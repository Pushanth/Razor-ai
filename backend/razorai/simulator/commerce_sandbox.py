import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional

from razorai.data.models import Transaction, PaymentMethod, TransactionStatus, FailureReason, RiskTier, PolicyDecision
from razorai.data.store import DataStore
from razorai.core.risk.risk_engine import AIRiskManager
from razorai.security.policy_engine import PolicyGuardrailEngine
from razorai.security.decision_ledger import AIDecisionLedger


class AgenticCommerceSimulator:
    """
    Agentic Commerce & Autonomous Checkout Simulator.
    Simulates AI Buyer Agent autonomous purchasing flow:
    Discover Product -> Evaluate -> Create Order -> Risk Check -> Delegated Consent -> Payment -> Ledger Verification.
    """

    SAMPLE_CATALOG = [
        {"id": "prod_01", "name": "AI Cloud Compute Cluster (30 Days)", "category": "SaaS & Cloud", "price": 18500.0, "merchant_id": "merch_0002"},
        {"id": "prod_02", "name": "Enterprise Security Firewall License", "category": "SaaS & Cloud", "price": 45000.0, "merchant_id": "merch_0002"},
        {"id": "prod_03", "name": "Fast Delivery Grocery Cart (Organic)", "category": "Quick Commerce & Food", "price": 2450.0, "merchant_id": "merch_0005"},
        {"id": "prod_04", "name": "Pro Gaming Ultra Pass (Annual)", "category": "Gaming & Entertainment", "price": 5999.0, "merchant_id": "merch_0004"},
        {"id": "prod_05", "name": "Executive Business Flight (BLR -> DEL)", "category": "Travel & Hospitality", "price": 12800.0, "merchant_id": "merch_0006"}
    ]

    def __init__(
        self,
        store: Optional[DataStore] = None,
        risk_manager: Optional[AIRiskManager] = None,
        policy_engine: Optional[PolicyGuardrailEngine] = None,
        ledger: Optional[AIDecisionLedger] = None
    ):
        self.store = store or DataStore.get_instance()
        self.risk_manager = risk_manager or AIRiskManager(self.store)
        self.policy_engine = policy_engine or PolicyGuardrailEngine()
        self.ledger = ledger or AIDecisionLedger(self.store)

    def run_autonomous_purchase(
        self,
        product_id: Optional[str] = None,
        user_delegated_limit: float = 25000.0,
        customer_id: str = "cust_000001"
    ) -> Dict[str, Any]:
        """
        Executes a complete 7-stage autonomous AI agent commerce transaction.
        """
        # 1. Product Discovery
        product = next((p for p in self.SAMPLE_CATALOG if p["id"] == product_id), self.SAMPLE_CATALOG[0])
        steps = []

        steps.append({
            "stage": "1. PRODUCT_DISCOVERY",
            "status": "COMPLETED",
            "detail": f"AI Commerce Agent identified requirement for '{product['name']}' at ₹{product['price']:,.2f}.",
            "timestamp": datetime.utcnow().isoformat()
        })

        # 2. Option Evaluation
        steps.append({
            "stage": "2. EVALUATE_OPTIONS",
            "status": "COMPLETED",
            "detail": f"Compared 4 merchant offerings. Selected merchant '{product['merchant_id']}' based on 98.4% fulfillment SLA and verified trust score.",
            "timestamp": datetime.utcnow().isoformat()
        })

        # 3. Create Order
        order_id = f"ord_agent_{uuid.uuid4().hex[:8]}"
        steps.append({
            "stage": "3. CREATE_ORDER",
            "status": "COMPLETED",
            "detail": f"Created Order {order_id} for ₹{product['price']:,.2f} on merchant checkout rail.",
            "timestamp": datetime.utcnow().isoformat()
        })

        # 4. Autonomous Risk Evaluation
        dummy_tx = Transaction(
            id=f"pay_agent_{uuid.uuid4().hex[:10]}",
            customer_id=customer_id,
            merchant_id=product["merchant_id"],
            amount=product["price"],
            currency="INR",
            payment_method=PaymentMethod.UPI,
            status=TransactionStatus.PENDING,
            device_id="dev_agent_trusted_01",
            ip_address="103.21.244.18",
            location="Bengaluru, KA",
            timestamp=datetime.utcnow()
        )
        risk_res = self.risk_manager.compute_fused_risk(dummy_tx)
        steps.append({
            "stage": "4. RISK_EVALUATION",
            "status": "COMPLETED",
            "detail": f"5-Layer Risk Score: {risk_res['final_risk_score']} ({risk_res['risk_tier']}). Recommendation: {risk_res['recommendation']}.",
            "risk_score": risk_res["final_risk_score"],
            "timestamp": datetime.utcnow().isoformat()
        })

        # 5. User Delegated Consent Check
        is_within_consent = (product["price"] <= user_delegated_limit)
        policy_res = self.policy_engine.evaluate_action(
            action="AUTO_PURCHASE",
            amount=product["price"],
            risk_score=risk_res["final_risk_score"],
            entity_id=customer_id
        )

        if not is_within_consent:
            steps.append({
                "stage": "5. USER_DELEGATED_CONSENT",
                "status": "ESCALATED",
                "detail": f"Price ₹{product['price']:,.2f} exceeds user autonomous delegated limit of ₹{user_delegated_limit:,.2f}. Requesting explicit user biometrics.",
                "timestamp": datetime.utcnow().isoformat()
            })
            return {
                "order_id": order_id,
                "product": product,
                "status": "REQUIRES_USER_CONFIRMATION",
                "stages": steps
            }

        steps.append({
            "stage": "5. USER_DELEGATED_CONSENT",
            "status": "APPROVED",
            "detail": f"Autonomous spend verified: ₹{product['price']:,.2f} is within delegated user mandate (Limit: ₹{user_delegated_limit:,.2f}).",
            "timestamp": datetime.utcnow().isoformat()
        })

        # 6. Payment Execution
        dummy_tx.status = TransactionStatus.SUCCESS
        self.store.add_transaction(dummy_tx)
        steps.append({
            "stage": "6. PAYMENT_EXECUTION",
            "status": "SUCCESS",
            "detail": f"Dispatched 1-Click Agentic UPI tokenized payment {dummy_tx.id}. Transaction authorized with 38ms latency.",
            "payment_id": dummy_tx.id,
            "timestamp": datetime.utcnow().isoformat()
        })

        # 7. Immutable Ledger Verification
        record = self.ledger.record_decision(
            entity_id=dummy_tx.id,
            entity_type="TRANSACTION",
            input_summary=f"Agentic Autonomous Purchase: {product['name']} (₹{product['price']:,.2f})",
            model_output={"risk_score": risk_res["final_risk_score"], "order_id": order_id},
            agent="CommerceAgent",
            tools_used=["evaluate_options", "calculate_risk", "execute_payment"],
            policy_check=PolicyDecision.AUTO_APPROVED,
            action_taken=f"Executed delegated purchase for {product['name']}",
            human_approval_required=False,
            revenue_impact=product["price"],
            outcome="PURCHASE_COMPLETED"
        )
        steps.append({
            "stage": "7. IMMUTABLE_LEDGER",
            "status": "RECORDED",
            "detail": f"Recorded cryptographically signed decision {record.decision_id} (Sig: {record.signature_hash[:16]}...).",
            "decision_id": record.decision_id,
            "timestamp": datetime.utcnow().isoformat()
        })

        return {
            "order_id": order_id,
            "payment_id": dummy_tx.id,
            "product": product,
            "status": "SUCCESS",
            "stages": steps,
            "decision_id": record.decision_id,
            "signature_hash": record.signature_hash
        }
