from typing import Dict, Any, Optional
from razorai.data.models import PolicyDecision, ActionType, RiskTier


class PolicyGuardrailEngine:
    """
    Deterministic Financial Policy & Security Guardrails Engine.
    Enforces non-negotiable boundaries:
    - Auto-execute allowed only below monetary threshold and low risk
    - High-value actions escalated to Human-in-the-Loop review
    - High-risk or blacklisted actions strictly blocked
    """

    MAX_AUTO_RECOVERY_INR = 25_000.0
    MAX_AUTO_REFUND_INR = 5_000.0
    MAX_TRANSACTION_LIMIT_INR = 500_000.0
    MAX_PERMISSIBLE_RISK_SCORE = 0.65

    def __init__(self):
        self.blacklisted_devices = set(["dev_blacklisted_01", "dev_blacklisted_02"])
        self.blacklisted_ips = set(["185.220.101.5", "194.26.29.11"])

    def evaluate_action(
        self,
        action: str,
        amount: float,
        risk_score: float,
        entity_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        meta = metadata or {}
        ip = meta.get("ip_address", "")
        dev_id = meta.get("device_id", "")

        # 1. Hard Blacklist Check
        if dev_id in self.blacklisted_devices or ip in self.blacklisted_ips:
            return {
                "decision": PolicyDecision.BLOCKED,
                "rule_triggered": "SECURITY_BLACKLIST_VIOLATION",
                "human_approval_required": False,
                "reason": "Entity or IP address exists on global security embargo/blacklist."
            }

        # 2. Hard Regulatory & Absolute Ceiling Check
        if amount > self.MAX_TRANSACTION_LIMIT_INR:
            return {
                "decision": PolicyDecision.BLOCKED,
                "rule_triggered": "EXCEEDS_REGULATORY_CEILING_INR_5L",
                "human_approval_required": False,
                "reason": f"Requested amount ₹{amount:,.2f} exceeds absolute platform policy limit of ₹5,00,000."
            }

        # 3. Critical Risk Check
        if risk_score >= self.MAX_PERMISSIBLE_RISK_SCORE:
            return {
                "decision": PolicyDecision.BLOCKED,
                "rule_triggered": "CRITICAL_RISK_THRESHOLD_EXCEEDED",
                "human_approval_required": False,
                "reason": f"AI Risk Score ({risk_score}) exceeds safe autonomous threshold ({self.MAX_PERMISSIBLE_RISK_SCORE})."
            }

        # 4. Action-specific limits: Auto Refund
        if action == "AUTO_REFUND":
            if amount > self.MAX_AUTO_REFUND_INR:
                return {
                    "decision": PolicyDecision.ESCALATED_TO_HUMAN,
                    "rule_triggered": "REFUND_REQUIRES_DUAL_SIGN_OFF",
                    "human_approval_required": True,
                    "reason": f"Refund of ₹{amount:,.2f} exceeds autonomous limit of ₹{self.MAX_AUTO_REFUND_INR:,.2f}. Escalating to Finance Supervisor."
                }

        # 5. Action-specific limits: High-Value Recovery / Rail Switch
        if action in ["SMART_RETRY_15M", "SMART_RETRY_2H", "SWITCH_RAIL_UPI", "UPI_PAYMENT_LINK"]:
            if amount > self.MAX_AUTO_RECOVERY_INR:
                return {
                    "decision": PolicyDecision.ESCALATED_TO_HUMAN,
                    "rule_triggered": "HIGH_VALUE_RECOVERY_ESCALATION",
                    "human_approval_required": True,
                    "reason": f"High-ticket recovery of ₹{amount:,.2f} requires Human Operations approval."
                }

        # 6. Auto-approval
        return {
            "decision": PolicyDecision.AUTO_APPROVED,
            "rule_triggered": "WITHIN_SAFE_AUTONOMOUS_BOUNDS",
            "human_approval_required": False,
            "reason": "Action complies with all financial limits, risk tolerances, and security policies."
        }
