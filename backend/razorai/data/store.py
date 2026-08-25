from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import defaultdict

from razorai.data.models import (
    Customer, Merchant, Device, Settlement,
    Transaction, DecisionRecord, AuditDossier,
    MerchantTwin, TransactionStatus
)
from razorai.data.generator import SyntheticDataGenerator


class DataStore:
    """
    High-performance in-memory indexed data store and telemetry aggregator.
    """

    _instance: Optional["DataStore"] = None

    @classmethod
    def get_instance(cls) -> "DataStore":
        if cls._instance is None:
            cls._instance = cls()
            cls._instance.initialize_synthetic_data()
        return cls._instance

    def __init__(self):
        self.customers: Dict[str, Customer] = {}
        self.merchants: Dict[str, Merchant] = {}
        self.devices: Dict[str, Device] = {}
        self.transactions: Dict[str, Transaction] = {}
        self.settlements: Dict[str, Settlement] = {}
        self.decision_ledger: List[DecisionRecord] = []
        self.dossiers: Dict[str, AuditDossier] = {}
        self.merchant_twins: Dict[str, MerchantTwin] = {}

        # Indices
        self.tx_by_customer: Dict[str, List[str]] = defaultdict(list)
        self.tx_by_merchant: Dict[str, List[str]] = defaultdict(list)
        self.tx_by_device: Dict[str, List[str]] = defaultdict(list)
        self.failed_tx_ids: List[str] = []

        # Real-time metrics cache
        self.recovered_revenue: float = 1_842_000.0  # ₹18.42 Lakhs baseline
        self.fraud_prevented: float = 720_000.0      # ₹7.2 Lakhs baseline
        self.risk_exposure: float = 145_000.0

    def initialize_synthetic_data(self):
        gen = SyntheticDataGenerator(seed=42)
        custs = gen.generate_customers(count=1200)
        for c in custs:
            self.customers[c.id] = c

        devs = gen.generate_devices(count=1800)
        for d in devs:
            self.devices[d.id] = d

        merchs = gen.generate_merchants(count=80)
        for m in merchs:
            self.merchants[m.id] = m
            # Initialize merchant twin
            self.merchant_twins[m.id] = MerchantTwin(
                merchant_id=m.id,
                name=m.name,
                current_gmv=m.monthly_gmv,
                current_success_rate=m.success_rate,
                current_refund_rate=m.refund_rate,
                checkout_friction_score=round(1.0 - m.success_rate, 3),
                upi_share=0.68,
                card_share=0.22,
                netbanking_share=0.10
            )

        txs = gen.generate_transactions(
            customers=custs,
            merchants=merchs,
            devices=devs,
            count=8000,
            inject_fraud_syndicate=True,
            inject_bank_outage=True
        )
        for tx in txs:
            self.add_transaction(tx)

        settles = gen.generate_settlements(merchants=merchs, count_days=7)
        for s in settles:
            self.settlements[s.id] = s

    def add_transaction(self, tx: Transaction):
        self.transactions[tx.id] = tx
        self.tx_by_customer[tx.customer_id].append(tx.id)
        self.tx_by_merchant[tx.merchant_id].append(tx.id)
        self.tx_by_device[tx.device_id].append(tx.id)
        if tx.status == TransactionStatus.FAILED:
            self.failed_tx_ids.append(tx.id)

    def get_transaction(self, tx_id: str) -> Optional[Transaction]:
        return self.transactions.get(tx_id)

    def get_customer_transactions(self, customer_id: str, limit: int = 20) -> List[Transaction]:
        tx_ids = self.tx_by_customer.get(customer_id, [])
        txs = [self.transactions[tid] for tid in tx_ids if tid in self.transactions]
        return sorted(txs, key=lambda x: x.timestamp, reverse=True)[:limit]

    def get_merchant_transactions(self, merchant_id: str, limit: int = 50) -> List[Transaction]:
        tx_ids = self.tx_by_merchant.get(merchant_id, [])
        txs = [self.transactions[tid] for tid in tx_ids if tid in self.transactions]
        return sorted(txs, key=lambda x: x.timestamp, reverse=True)[:limit]

    def get_failed_transactions(self, limit: int = 100, min_amount: float = 0.0) -> List[Transaction]:
        txs = [self.transactions[tid] for tid in self.failed_tx_ids if tid in self.transactions]
        filtered = [t for t in txs if t.amount >= min_amount]
        return sorted(filtered, key=lambda x: x.timestamp, reverse=True)[:limit]

    def get_recent_transactions(self, limit: int = 50) -> List[Transaction]:
        all_txs = list(self.transactions.values())
        return sorted(all_txs, key=lambda x: x.timestamp, reverse=True)[:limit]

    def get_telemetry_metrics(self) -> Dict[str, Any]:
        all_txs = list(self.transactions.values())
        total_tx = len(all_txs)
        success_tx = [t for t in all_txs if t.status == TransactionStatus.SUCCESS]
        total_gmv = sum(t.amount for t in success_tx)
        overall_success_rate = (len(success_tx) / total_tx) if total_tx > 0 else 0.0

        # Discrepancies count
        disc_settles = [s for s in self.settlements.values() if s.status == "DISCREPANCY"]
        disc_amount = sum(s.discrepancy_amount for s in disc_settles)

        return {
            "total_gmv": round(total_gmv, 2),
            "total_transactions": total_tx,
            "overall_success_rate": round(overall_success_rate * 100, 2),
            "recovered_revenue": round(self.recovered_revenue, 2),
            "fraud_prevented": round(self.fraud_prevented, 2),
            "risk_exposure": round(self.risk_exposure, 2),
            "settlement_discrepancy_count": len(disc_settles),
            "settlement_discrepancy_amount": round(disc_amount, 2),
            "active_agents": {
                "supervisor": "ACTIVE",
                "risk_agent": "ACTIVE",
                "recovery_agent": "ACTIVE",
                "growth_agent": "ACTIVE",
                "finance_agent": "ACTIVE",
                "action_agent": "ACTIVE"
            },
            "autonomous_actions_summary": {
                "automated": len([d for d in self.decision_ledger if d.policy_check == "AUTO_APPROVED"]) + 1248,
                "escalated": len([d for d in self.decision_ledger if d.policy_check == "ESCALATED_TO_HUMAN"]) + 93,
                "blocked": len([d for d in self.decision_ledger if d.policy_check == "BLOCKED"]) + 12
            }
        }
