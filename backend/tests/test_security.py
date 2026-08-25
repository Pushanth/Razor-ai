import pytest
from razorai.data.store import DataStore
from razorai.security.policy_engine import PolicyGuardrailEngine
from razorai.security.decision_ledger import AIDecisionLedger
from razorai.security.red_team import RedTeamSecuritySuite
from razorai.data.models import PolicyDecision


def test_policy_guardrail_limits():
    policy = PolicyGuardrailEngine()
    
    # 1. Normal low value, low risk
    res1 = policy.evaluate_action(
        action="SMART_RETRY_15M",
        amount=4500.0,
        risk_score=0.12,
        entity_id="cust_001"
    )
    assert res1["decision"] == PolicyDecision.AUTO_APPROVED
    
    # 2. High amount refund -> Escalated to Human
    res2 = policy.evaluate_action(
        action="AUTO_REFUND",
        amount=25000.0,
        risk_score=0.15,
        entity_id="cust_001"
    )
    assert res2["decision"] == PolicyDecision.ESCALATED_TO_HUMAN
    assert res2["human_approval_required"] is True
    
    # 3. High risk -> Blocked
    res3 = policy.evaluate_action(
        action="SMART_RETRY_15M",
        amount=1000.0,
        risk_score=0.85,
        entity_id="cust_001"
    )
    assert res3["decision"] == PolicyDecision.BLOCKED
    
    # 4. Regulatory limit exceeded -> Blocked
    res4 = policy.evaluate_action(
        action="AUTO_REFUND",
        amount=10_000_000.0,
        risk_score=0.10,
        entity_id="cust_001"
    )
    assert res4["decision"] == PolicyDecision.BLOCKED


def test_decision_ledger_cryptographic_integrity():
    store = DataStore.get_instance()
    ledger = AIDecisionLedger(store)
    
    verification = ledger.verify_ledger_integrity()
    assert verification["status"] == "VALID"
    assert verification["is_compromised"] is False


def test_red_team_adversarial_defenses():
    suite = RedTeamSecuritySuite()
    results = suite.run_security_evaluation()
    
    assert results["defense_success_rate"] == 100.0
    assert results["safety_verdict"] == "HARDENED"
    assert results["attacks_successfully_defended"] == results["total_attacks_tested"]
