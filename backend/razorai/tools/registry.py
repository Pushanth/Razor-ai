from typing import Dict, List, Any, Optional
from razorai.data.store import DataStore
from razorai.data.models import Transaction, ActionType, PolicyDecision
from razorai.core.risk.risk_engine import AIRiskManager
from razorai.core.recovery.counterfactual import CounterfactualEngine
from razorai.core.recovery.bandit import ContextualRecoveryBandit
from razorai.core.growth.digital_twin import MerchantGrowthEngine
from razorai.core.finance.reconciliation import AutonomousFinanceController
from razorai.core.graph.knowledge_graph import PaymentKnowledgeGraph
from razorai.security.policy_engine import PolicyGuardrailEngine
from razorai.security.decision_ledger import AIDecisionLedger


class AgentToolRegistry:
    """
    Standardized Tool Registry providing callable tools for Multi-Agent execution.
    """

    def __init__(
        self,
        store: Optional[DataStore] = None,
        risk_manager: Optional[AIRiskManager] = None,
        counterfactual_engine: Optional[CounterfactualEngine] = None,
        bandit_engine: Optional[ContextualRecoveryBandit] = None,
        growth_engine: Optional[MerchantGrowthEngine] = None,
        finance_controller: Optional[AutonomousFinanceController] = None,
        knowledge_graph: Optional[PaymentKnowledgeGraph] = None,
        policy_engine: Optional[PolicyGuardrailEngine] = None,
        decision_ledger: Optional[AIDecisionLedger] = None
    ):
        self.store = store or DataStore.get_instance()
        self.risk_manager = risk_manager or AIRiskManager(self.store)
        self.counterfactual_engine = counterfactual_engine or CounterfactualEngine()
        self.bandit_engine = bandit_engine or ContextualRecoveryBandit()
        self.growth_engine = growth_engine or MerchantGrowthEngine(self.store)
        self.finance_controller = finance_controller or AutonomousFinanceController(self.store)
        self.knowledge_graph = knowledge_graph or PaymentKnowledgeGraph(self.store)
        self.policy_engine = policy_engine or PolicyGuardrailEngine()
        self.decision_ledger = decision_ledger or AIDecisionLedger(self.store)

    # 1. Transaction & Data Tools
    def get_transaction(self, tx_id: str) -> Dict[str, Any]:
        tx = self.store.get_transaction(tx_id)
        if not tx:
            return {"error": f"Transaction {tx_id} not found."}
        return tx.model_dump(mode="json")

    def search_failed_transactions(self, limit: int = 50, min_amount: float = 0.0) -> List[Dict[str, Any]]:
        txs = self.store.get_failed_transactions(limit=limit, min_amount=min_amount)
        return [t.model_dump(mode="json") for t in txs]

    def get_customer_profile(self, customer_id: str) -> Dict[str, Any]:
        cust = self.store.customers.get(customer_id)
        if not cust:
            return {"error": f"Customer {customer_id} not found."}
        return cust.model_dump(mode="json")

    def get_merchant_profile(self, merchant_id: str) -> Dict[str, Any]:
        merch = self.store.merchants.get(merchant_id)
        if not merch:
            return {"error": f"Merchant {merchant_id} not found."}
        return merch.model_dump(mode="json")

    # 2. Risk & Forensics Tools
    def calculate_multi_layer_risk(self, tx_id: str) -> Dict[str, Any]:
        tx = self.store.get_transaction(tx_id)
        if not tx:
            return {"error": f"Transaction {tx_id} not found."}
        return self.risk_manager.compute_fused_risk(tx)

    def query_knowledge_graph(self, entity_id: str) -> Dict[str, Any]:
        return self.knowledge_graph.analyze_entity_network(entity_id)

    def detect_fraud_syndicates(self) -> List[Dict[str, Any]]:
        return self.knowledge_graph.detect_syndicates()

    # 3. Revenue Recovery Tools
    def predict_recovery_counterfactuals(self, tx_id: str) -> Dict[str, Any]:
        tx = self.store.get_transaction(tx_id)
        if not tx:
            return {"error": f"Transaction {tx_id} not found."}
        options = self.counterfactual_engine.simulate_interventions(tx)
        return {
            "transaction_id": tx_id,
            "options": [opt.model_dump(mode="json") for opt in options]
        }

    def bandit_select_action(self, tx_id: str) -> Dict[str, Any]:
        tx = self.store.get_transaction(tx_id)
        if not tx:
            return {"error": f"Transaction {tx_id} not found."}
        action, details = self.bandit_engine.select_action(tx)
        return {
            "transaction_id": tx_id,
            "selected_action": action.value,
            "details": details
        }

    # 4. Growth Tools
    def simulate_merchant_growth(
        self,
        merchant_id: str,
        enable_smart_retry: bool = True,
        add_emi_and_upi_intent: bool = True,
        reduce_checkout_friction_pct: float = 15.0
    ) -> Dict[str, Any]:
        return self.growth_engine.simulate_what_if(
            merchant_id=merchant_id,
            enable_smart_retry=enable_smart_retry,
            add_emi_and_upi_intent=add_emi_and_upi_intent,
            reduce_checkout_friction_pct=reduce_checkout_friction_pct
        )

    # 5. Finance Reconciliation Tools
    def reconcile_settlements_summary(self) -> Dict[str, Any]:
        return self.finance_controller.reconcile_all_settlements()

    def investigate_settlement_discrepancy(self, settlement_id: str) -> Dict[str, Any]:
        return self.finance_controller.investigate_settlement(settlement_id)

    # 6. Security, Policy & Execution Tools
    def evaluate_policy(self, action: str, amount: float, risk_score: float, entity_id: str) -> Dict[str, Any]:
        res = self.policy_engine.evaluate_action(action, amount, risk_score, entity_id)
        return {
            "decision": res["decision"].value,
            "rule_triggered": res["rule_triggered"],
            "human_approval_required": res["human_approval_required"],
            "reason": res["reason"]
        }

    def execute_recovery_action(self, tx_id: str, action_type: str) -> Dict[str, Any]:
        tx = self.store.get_transaction(tx_id)
        if not tx:
            return {"error": f"Transaction {tx_id} not found."}

        # Policy guardrail check
        policy_res = self.policy_engine.evaluate_action(
            action=action_type,
            amount=tx.amount,
            risk_score=tx.risk_score,
            entity_id=tx.id
        )

        decision_type = policy_res["decision"]

        if decision_type == PolicyDecision.BLOCKED:
            self.decision_ledger.record_decision(
                entity_id=tx.id,
                entity_type="TRANSACTION",
                input_summary=f"Recovery requested for {tx.id} (₹{tx.amount:,.2f})",
                model_output={"risk_score": tx.risk_score, "action": action_type},
                agent="ActionAgent",
                tools_used=["evaluate_policy", "execute_recovery_action"],
                policy_check=PolicyDecision.BLOCKED,
                policy_rule_triggered=policy_res["rule_triggered"],
                action_taken=f"BLOCKED: {policy_res['reason']}",
                human_approval_required=False,
                revenue_impact=0.0,
                outcome="POLICY_BLOCKED"
            )
            return {
                "status": "BLOCKED",
                "reason": policy_res["reason"],
                "rule": policy_res["rule_triggered"]
            }

        if decision_type == PolicyDecision.ESCALATED_TO_HUMAN:
            self.decision_ledger.record_decision(
                entity_id=tx.id,
                entity_type="TRANSACTION",
                input_summary=f"High-value recovery requested for {tx.id} (₹{tx.amount:,.2f})",
                model_output={"risk_score": tx.risk_score, "action": action_type},
                agent="ActionAgent",
                tools_used=["evaluate_policy", "request_human_approval"],
                policy_check=PolicyDecision.ESCALATED_TO_HUMAN,
                policy_rule_triggered=policy_res["rule_triggered"],
                action_taken=f"ESCALATED: {policy_res['reason']}",
                human_approval_required=True,
                revenue_impact=tx.amount,
                outcome="AWAITING_HUMAN_SIGN_OFF"
            )
            return {
                "status": "ESCALATED_TO_HUMAN",
                "reason": policy_res["reason"],
                "rule": policy_res["rule_triggered"]
            }

        # Auto-executed successfully
        self.store.recovered_revenue += tx.amount * 0.85 # simulated recovery success rate
        rec = self.decision_ledger.record_decision(
            entity_id=tx.id,
            entity_type="TRANSACTION",
            input_summary=f"Autonomous recovery executed for {tx.id} via {action_type} (₹{tx.amount:,.2f})",
            model_output={"risk_score": tx.risk_score, "action": action_type},
            agent="ActionAgent",
            tools_used=["evaluate_policy", "execute_recovery_action"],
            policy_check=PolicyDecision.AUTO_APPROVED,
            policy_rule_triggered=policy_res["rule_triggered"],
            action_taken=f"Executed {action_type} recovery dispatch",
            human_approval_required=False,
            revenue_impact=round(tx.amount * 0.85, 2),
            outcome="RECOVERY_DISPATCHED"
        )

        return {
            "status": "AUTO_EXECUTED",
            "action_taken": action_type,
            "decision_id": rec.decision_id,
            "revenue_recovered": round(tx.amount * 0.85, 2)
        }
