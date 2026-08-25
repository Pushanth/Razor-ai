from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class PaymentMethod(str, Enum):
    UPI = "UPI"
    CARD = "CARD"
    NETBANKING = "NETBANKING"
    WALLET = "WALLET"
    EMI = "EMI"


class TransactionStatus(str, Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    PENDING = "PENDING"
    REFUNDED = "REFUNDED"
    DISPUTED = "DISPUTED"


class FailureReason(str, Enum):
    NONE = "NONE"
    BANK_TIMEOUT = "BANK_TIMEOUT"
    INSUFFICIENT_FUNDS = "INSUFFICIENT_FUNDS"
    AUTH_FAILED = "AUTH_FAILED"
    CARD_EXPIRED = "CARD_EXPIRED"
    GATEWAY_ERROR = "GATEWAY_ERROR"
    LIMIT_EXCEEDED = "LIMIT_EXCEEDED"
    FRAUD_BLOCKED = "FRAUD_BLOCKED"


class RiskTier(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ActionType(str, Enum):
    SMART_RETRY_15M = "SMART_RETRY_15M"
    SMART_RETRY_2H = "SMART_RETRY_2H"
    UPI_PAYMENT_LINK = "UPI_PAYMENT_LINK"
    SWITCH_RAIL_UPI = "SWITCH_RAIL_UPI"
    PUSH_NOTIFICATION = "PUSH_NOTIFICATION"
    HOLD_FOR_REVIEW = "HOLD_FOR_REVIEW"
    BLOCK_TRANSACTION = "BLOCK_TRANSACTION"
    AUTO_REFUND = "AUTO_REFUND"
    NO_ACTION = "NO_ACTION"


class PolicyDecision(str, Enum):
    AUTO_APPROVED = "AUTO_APPROVED"
    ESCALATED_TO_HUMAN = "ESCALATED_TO_HUMAN"
    BLOCKED = "BLOCKED"


class Transaction(BaseModel):
    id: str
    customer_id: str
    merchant_id: str
    amount: float
    currency: str = "INR"
    payment_method: PaymentMethod
    status: TransactionStatus
    failure_reason: FailureReason = FailureReason.NONE
    device_id: str
    card_fingerprint: Optional[str] = None
    ip_address: str = "127.0.0.1"
    location: str = "Mumbai, IN"
    timestamp: datetime
    risk_score: float = 0.0
    risk_tier: RiskTier = RiskTier.LOW
    latency_ms: float = 45.0
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Customer(BaseModel):
    id: str
    name: str
    email: str
    phone: str
    created_at: datetime
    risk_tier: RiskTier = RiskTier.LOW
    total_gmv: float = 0.0
    tx_count: int = 0
    failure_count: int = 0
    linked_devices: List[str] = Field(default_factory=list)
    linked_cards: List[str] = Field(default_factory=list)


class Merchant(BaseModel):
    id: str
    name: str
    category: str
    monthly_gmv: float
    success_rate: float
    refund_rate: float
    dispute_rate: float
    risk_profile: RiskTier = RiskTier.LOW
    preferred_recovery_rail: PaymentMethod = PaymentMethod.UPI
    webhook_url: str = "https://api.merchant.com/webhook"


class Device(BaseModel):
    id: str
    device_type: str = "mobile"
    os: str = "Android"
    ip_addresses: List[str] = Field(default_factory=list)
    associated_customers: List[str] = Field(default_factory=list)
    fraud_flag: bool = False


class Settlement(BaseModel):
    id: str
    merchant_id: str
    date: str
    gross_volume: float
    refund_deduction: float
    fee_deduction: float
    chargeback_deduction: float
    reserve_holdback: float
    expected_payout: float
    actual_payout: float
    discrepancy_amount: float
    status: str = "SETTLED"  # SETTLED, DISCREPANCY, UNDER_INVESTIGATION
    dossier_id: Optional[str] = None


class CounterfactualOption(BaseModel):
    action: ActionType
    description: str
    expected_recovery_prob: float
    expected_recovered_amount: float
    cost: float
    friction_penalty: float
    risk_penalty: float
    risk_adjusted_ev: float
    is_recommended: bool = False


class DecisionRecord(BaseModel):
    decision_id: str
    timestamp: datetime
    entity_id: str
    entity_type: str  # TRANSACTION, SETTLEMENT, MERCHANT
    input_summary: str
    model_version: str = "Vulcan-Prototype-v2.4"
    model_output: Dict[str, Any] = Field(default_factory=dict)
    agent: str
    tools_used: List[str] = Field(default_factory=list)
    policy_check: PolicyDecision
    policy_rule_triggered: Optional[str] = None
    action_taken: str
    human_approval_required: bool = False
    human_approved: Optional[bool] = None
    revenue_impact: float = 0.0
    outcome: str = "PENDING"
    signature_hash: str = ""


class AuditDossier(BaseModel):
    case_id: str
    created_at: datetime
    entity_id: str
    discrepancy_type: str
    gross_gmv: float
    refunds: float
    fees: float
    chargebacks: float
    unexplained_variance: float
    evidence_trail: List[str] = Field(default_factory=list)
    recommended_action: str
    status: str = "OPEN"  # OPEN, RESOLVED, ESCALATED


class MerchantTwin(BaseModel):
    merchant_id: str
    name: str
    current_gmv: float
    current_success_rate: float
    current_refund_rate: float
    checkout_friction_score: float
    upi_share: float
    card_share: float
    netbanking_share: float
    simulations: Dict[str, Any] = Field(default_factory=dict)


class AgentTraceStep(BaseModel):
    step_index: int
    agent_name: str
    thought: str
    tool_name: Optional[str] = None
    tool_input: Optional[Dict[str, Any]] = None
    tool_output: Optional[Dict[str, Any]] = None
    status: str = "COMPLETED"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
