import hashlib
import json
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional

from razorai.data.models import DecisionRecord, PolicyDecision
from razorai.data.store import DataStore


class AIDecisionLedger:
    """
    Cryptographically Chained Immutable AI Decision Ledger.
    Every autonomous agent action, risk verdict, tool execution, and policy evaluation
    is recorded with tamper-evident SHA-256 hash chaining.
    """

    def __init__(self, store: Optional[DataStore] = None):
        self.store = store or DataStore.get_instance()
        self.genesis_hash = "0" * 64
        self._seed_baseline_ledger_if_empty()

    def _seed_baseline_ledger_if_empty(self):
        if not self.store.decision_ledger:
            # Seed initial records
            self.record_decision(
                entity_id="pay_init_001",
                entity_type="TRANSACTION",
                input_summary="Payment failed due to HDFC bank switch timeout (₹12,450.00)",
                model_output={"risk_score": 0.08, "recommended_action": "SMART_RETRY_15M"},
                agent="RecoveryAgent",
                tools_used=["predict_recovery_counterfactuals", "bandit_select_action"],
                policy_check=PolicyDecision.AUTO_APPROVED,
                policy_rule_triggered="WITHIN_SAFE_AUTONOMOUS_BOUNDS",
                action_taken="Scheduled Smart Retry for 15 minutes",
                human_approval_required=False,
                revenue_impact=12450.0,
                outcome="SUCCESS_RECOVERED"
            )
            self.record_decision(
                entity_id="pay_init_002",
                entity_type="TRANSACTION",
                input_summary="Suspected card fraud syndicate attempt (₹85,000.00)",
                model_output={"risk_score": 0.94, "recommended_action": "BLOCK_TRANSACTION"},
                agent="RiskAgent",
                tools_used=["calculate_multi_layer_risk", "query_knowledge_graph"],
                policy_check=PolicyDecision.AUTO_APPROVED,
                policy_rule_triggered="CRITICAL_RISK_THRESHOLD_EXCEEDED",
                action_taken="Blocked transaction and flagged device dev_syndicate_01",
                human_approval_required=False,
                revenue_impact=-85000.0,
                outcome="FRAUD_PREVENTED"
            )
            self.record_decision(
                entity_id="set_merch_001_20260824",
                entity_type="SETTLEMENT",
                input_summary="Settlement payout discrepancy detected: ₹20,000 unexplained variance",
                model_output={"unexplained_variance": 20000.0, "recommended_action": "CREATE_DISPUTE_CASE"},
                agent="FinanceAgent",
                tools_used=["reconcile_settlement", "generate_audit_dossier"],
                policy_check=PolicyDecision.AUTO_APPROVED,
                policy_rule_triggered="WITHIN_SAFE_AUTONOMOUS_BOUNDS",
                action_taken="Generated Audit Dossier CASE-FIN-SETTLE-01",
                human_approval_required=False,
                revenue_impact=20000.0,
                outcome="INVESTIGATION_OPEN"
            )

    def get_last_hash(self) -> str:
        if not self.store.decision_ledger:
            return self.genesis_hash
        return self.store.decision_ledger[-1].signature_hash

    def record_decision(
        self,
        entity_id: str,
        entity_type: str,
        input_summary: str,
        model_output: Dict[str, Any],
        agent: str,
        tools_used: List[str],
        policy_check: PolicyDecision,
        action_taken: str,
        policy_rule_triggered: Optional[str] = None,
        human_approval_required: bool = False,
        human_approved: Optional[bool] = None,
        revenue_impact: float = 0.0,
        outcome: str = "COMPLETED"
    ) -> DecisionRecord:
        decision_id = f"DEC-{uuid.uuid4().hex[:10].upper()}"
        ts = datetime.utcnow()
        prev_hash = self.get_last_hash()

        # Build payload for cryptographic signature
        payload = {
            "decision_id": decision_id,
            "prev_hash": prev_hash,
            "timestamp": ts.isoformat(),
            "entity_id": entity_id,
            "agent": agent,
            "tools": tools_used,
            "policy": policy_check.value,
            "action": action_taken,
            "revenue_impact": revenue_impact
        }
        sig_hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()

        record = DecisionRecord(
            decision_id=decision_id,
            timestamp=ts,
            entity_id=entity_id,
            entity_type=entity_type,
            input_summary=input_summary,
            model_version="Vulcan-Prototype-v2.4",
            model_output=model_output,
            agent=agent,
            tools_used=tools_used,
            policy_check=policy_check,
            policy_rule_triggered=policy_rule_triggered,
            action_taken=action_taken,
            human_approval_required=human_approval_required,
            human_approved=human_approved,
            revenue_impact=revenue_impact,
            outcome=outcome,
            signature_hash=sig_hash
        )

        self.store.decision_ledger.append(record)
        return record

    def get_ledger(self, limit: int = 50) -> List[DecisionRecord]:
        return list(reversed(self.store.decision_ledger))[:limit]

    def verify_ledger_integrity(self) -> Dict[str, Any]:
        """Validates tamper-evident hash chain integrity."""
        ledger = self.store.decision_ledger
        if not ledger:
            return {"status": "VALID", "record_count": 0, "is_compromised": False}

        prev_hash = self.genesis_hash
        for i, rec in enumerate(ledger):
            payload = {
                "decision_id": rec.decision_id,
                "prev_hash": prev_hash,
                "timestamp": rec.timestamp.isoformat(),
                "entity_id": rec.entity_id,
                "agent": rec.agent,
                "tools": rec.tools_used,
                "policy": rec.policy_check.value,
                "action": rec.action_taken,
                "revenue_impact": rec.revenue_impact
            }
            computed_hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
            if computed_hash != rec.signature_hash:
                return {
                    "status": "CORRUPTED",
                    "corrupted_at_index": i,
                    "record_id": rec.decision_id,
                    "is_compromised": True
                }
            prev_hash = rec.signature_hash

        return {
            "status": "VALID",
            "record_count": len(ledger),
            "is_compromised": False,
            "latest_signature": prev_hash
        }
