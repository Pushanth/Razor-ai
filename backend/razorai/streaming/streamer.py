import time
import random
import uuid
from datetime import datetime
from typing import Dict, Any, Optional

from razorai.data.models import (
    Transaction, PaymentMethod, TransactionStatus, FailureReason, RiskTier
)
from razorai.data.store import DataStore
from razorai.core.risk.risk_engine import AIRiskManager
from razorai.streaming.event_bus import EventBus


class TransactionStreamer:
    """
    Live streaming transaction generator and high-throughput benchmark simulator.
    Capable of streaming live transactions to WebSockets and benchmarking >1,000 tx/sec with <100ms latency.
    """

    def __init__(
        self,
        store: Optional[DataStore] = None,
        risk_manager: Optional[AIRiskManager] = None,
        event_bus: Optional[EventBus] = None
    ):
        self.store = store or DataStore.get_instance()
        self.risk_manager = risk_manager or AIRiskManager(self.store)
        self.event_bus = event_bus or EventBus.get_instance()
        self.is_streaming = False

    def generate_single_live_transaction(self) -> Transaction:
        """Generates and processes a single live streaming transaction."""
        t0 = time.perf_counter()
        
        customers = list(self.store.customers.values())
        merchants = list(self.store.merchants.values())
        devices = list(self.store.devices.values())

        customer = random.choice(customers) if customers else None
        merchant = random.choice(merchants) if merchants else None
        device = random.choice(devices) if devices else None

        cust_id = customer.id if customer else "cust_live_001"
        merch_id = merchant.id if merchant else "merch_0001"
        dev_id = device.id if device else "dev_live_001"

        methods = [PaymentMethod.UPI, PaymentMethod.CARD, PaymentMethod.NETBANKING, PaymentMethod.WALLET]
        method = random.choices(methods, weights=[0.65, 0.20, 0.10, 0.05])[0]

        amount = round(random.expovariate(1.0 / 1500) + 100, 2)
        amount = min(amount, 120_000.0)

        # 90% success, 10% failure
        is_success = random.random() < 0.90
        if is_success:
            status = TransactionStatus.SUCCESS
            failure_reason = FailureReason.NONE
        else:
            status = TransactionStatus.FAILED
            failure_reason = random.choice([
                FailureReason.BANK_TIMEOUT,
                FailureReason.INSUFFICIENT_FUNDS,
                FailureReason.AUTH_FAILED,
                FailureReason.GATEWAY_ERROR
            ])

        tx = Transaction(
            id=f"pay_live_{uuid.uuid4().hex[:10]}",
            customer_id=cust_id,
            merchant_id=merch_id,
            amount=amount,
            currency="INR",
            payment_method=method,
            status=status,
            failure_reason=failure_reason,
            device_id=dev_id,
            card_fingerprint=f"card_{uuid.uuid4().hex[:8]}" if method == PaymentMethod.CARD else None,
            ip_address=f"103.21.{random.randint(10, 250)}.{random.randint(1, 254)}",
            location=random.choice(["Mumbai, MH", "Bengaluru, KA", "Delhi, DL", "Pune, MH"]),
            timestamp=datetime.utcnow()
        )

        # Fast risk inference
        risk_res = self.risk_manager.compute_fused_risk(tx)
        latency = (time.perf_counter() - t0) * 1000.0 # ms
        tx.latency_ms = round(latency, 2)

        self.store.add_transaction(tx)

        # Publish to event bus
        if tx.status == TransactionStatus.SUCCESS:
            self.event_bus.publish("PaymentSucceeded", {"transaction_id": tx.id, "amount": tx.amount})
        else:
            self.event_bus.publish("TransactionFailed", {
                "transaction_id": tx.id,
                "amount": tx.amount,
                "reason": tx.failure_reason.value,
                "risk_score": tx.risk_score
            })

        if tx.risk_score >= 0.70:
            self.event_bus.publish("RiskDetected", {
                "transaction_id": tx.id,
                "risk_score": tx.risk_score,
                "tier": tx.risk_tier.value
            })

        return tx

    def run_throughput_benchmark(self, count: int = 1000) -> Dict[str, Any]:
        """
        Runs high-throughput streaming benchmark simulating 1,000+ tx/sec
        with ultra-low latency (<100ms risk scoring).
        """
        t_start = time.perf_counter()
        latencies = []
        success_count = 0
        fraud_intercepted = 0

        for _ in range(count):
            t0 = time.perf_counter()
            tx = self.generate_single_live_transaction()
            lat = (time.perf_counter() - t0) * 1000.0
            latencies.append(lat)
            if tx.status == TransactionStatus.SUCCESS:
                success_count += 1
            if tx.risk_score >= 0.75:
                fraud_intercepted += 1

        total_elapsed = time.perf_counter() - t_start
        throughput_tps = round(count / total_elapsed, 1)

        return {
            "total_transactions_processed": count,
            "total_time_seconds": round(total_elapsed, 3),
            "throughput_tps": throughput_tps,
            "avg_latency_ms": round(float(sum(latencies)/len(latencies)), 2),
            "p50_latency_ms": round(float(sorted(latencies)[int(count * 0.50)]), 2),
            "p95_latency_ms": round(float(sorted(latencies)[int(count * 0.95)]), 2),
            "p99_latency_ms": round(float(sorted(latencies)[int(count * 0.99)]), 2),
            "success_rate_percentage": round((success_count / count) * 100, 2),
            "fraud_intercepted_count": fraud_intercepted,
            "meets_100ms_sla": bool(sum(latencies)/len(latencies) < 100.0)
        }
