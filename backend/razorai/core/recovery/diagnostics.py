from typing import Dict, Any
from razorai.data.models import Transaction, FailureReason


class FailureDiagnosticsEngine:
    """
    Diagnoses root causes of failed payments and maps failure patterns to intervention readiness.
    """

    def diagnose_failure(self, tx: Transaction) -> Dict[str, Any]:
        reason = tx.failure_reason

        diagnostics_map = {
            FailureReason.BANK_TIMEOUT: {
                "category": "INFRASTRUCTURE_TRANSIENT",
                "root_cause": "Issuer / NPCI bank switch latency spike (>15,000ms). Payment rail temporarily degraded.",
                "recoverable": True,
                "base_recovery_rate": 0.82,
                "recommended_rail": "UPI",
                "urgency": "HIGH"
            },
            FailureReason.INSUFFICIENT_FUNDS: {
                "category": "CUSTOMER_ACCOUNT",
                "root_cause": "Account balance below transaction authorization threshold.",
                "recoverable": True,
                "base_recovery_rate": 0.64,
                "recommended_rail": "UPI_PAYMENT_LINK",
                "urgency": "MEDIUM"
            },
            FailureReason.AUTH_FAILED: {
                "category": "CUSTOMER_AUTHENTICATION",
                "root_cause": "OTP verification timeout or 3D-Secure 2FA biometric mismatch.",
                "recoverable": True,
                "base_recovery_rate": 0.74,
                "recommended_rail": "UPI_PAYMENT_LINK",
                "urgency": "HIGH"
            },
            FailureReason.CARD_EXPIRED: {
                "category": "INSTRUMENT_STATIC",
                "root_cause": "Card expiry date reached or token invalid.",
                "recoverable": True,
                "base_recovery_rate": 0.58,
                "recommended_rail": "SWITCH_RAIL_UPI",
                "urgency": "LOW"
            },
            FailureReason.GATEWAY_ERROR: {
                "category": "ACQUIRER_TRANSIENT",
                "root_cause": "Acquiring bank payment gateway error 502/504.",
                "recoverable": True,
                "base_recovery_rate": 0.78,
                "recommended_rail": "SMART_RETRY_15M",
                "urgency": "HIGH"
            },
            FailureReason.LIMIT_EXCEEDED: {
                "category": "REGULATORY_LIMIT",
                "root_cause": "Per-transaction or daily UPI/Card velocity limit reached.",
                "recoverable": True,
                "base_recovery_rate": 0.52,
                "recommended_rail": "NETBANKING",
                "urgency": "LOW"
            },
            FailureReason.FRAUD_BLOCKED: {
                "category": "SECURITY_BLOCK",
                "root_cause": "AI Risk Engine intercepted high-probability fraud syndicate signature.",
                "recoverable": False,
                "base_recovery_rate": 0.0,
                "recommended_rail": "NONE",
                "urgency": "BLOCKED"
            }
        }

        diag = diagnostics_map.get(
            reason,
            {
                "category": "UNKNOWN",
                "root_cause": "Unspecified gateway failure.",
                "recoverable": True,
                "base_recovery_rate": 0.50,
                "recommended_rail": "UPI_PAYMENT_LINK",
                "urgency": "MEDIUM"
            }
        )

        return {
            "transaction_id": tx.id,
            "failure_reason": reason.value,
            "diagnostics": diag
        }
