from datetime import datetime
from typing import Dict, List, Any, Optional

from razorai.data.models import AgentTraceStep
from razorai.tools.registry import AgentToolRegistry
from razorai.agents.memory import AgentMemory


class BaseSpecialistAgent:
    def __init__(self, name: str, tools: AgentToolRegistry, memory: AgentMemory):
        self.name = name
        self.tools = tools
        self.memory = memory

    def log_step(
        self,
        traces: List[AgentTraceStep],
        thought: str,
        tool_name: Optional[str] = None,
        tool_input: Optional[Dict[str, Any]] = None,
        tool_output: Optional[Dict[str, Any]] = None
    ):
        step = AgentTraceStep(
            step_index=len(traces) + 1,
            agent_name=self.name,
            thought=thought,
            tool_name=tool_name,
            tool_input=tool_input,
            tool_output=tool_output,
            status="COMPLETED",
            timestamp=datetime.utcnow()
        )
        traces.append(step)


class RiskAgent(BaseSpecialistAgent):
    def __init__(self, tools: AgentToolRegistry, memory: AgentMemory):
        super().__init__("RiskAgent", tools, memory)

    def investigate_risk(self, target_tx_ids: List[str], traces: List[AgentTraceStep]) -> Dict[str, Any]:
        self.log_step(
            traces,
            f"Initiating 5-layer forensic risk scan on {len(target_tx_ids)} transactions across Graph, Temporal, and Payload layers."
        )

        # 1. Detect Syndicates
        syndicates = self.tools.detect_fraud_syndicates()
        self.log_step(
            traces,
            f"Knowledge Graph community scan completed: Identified {len(syndicates)} suspicious device-sharing syndicate clusters.",
            tool_name="detect_fraud_syndicates",
            tool_input={},
            tool_output={"syndicates_found": len(syndicates)}
        )

        # 2. Score sample transactions
        scored_txs = []
        low_risk_tx_ids = []
        high_risk_tx_ids = []

        for tid in target_tx_ids[:15]:
            risk_res = self.tools.calculate_multi_layer_risk(tid)
            if "error" not in risk_res:
                scored_txs.append(risk_res)
                if risk_res["final_risk_score"] < 0.35:
                    low_risk_tx_ids.append(tid)
                else:
                    high_risk_tx_ids.append(tid)

        self.log_step(
            traces,
            f"Risk segmentation complete: {len(low_risk_tx_ids)} safe recoverable transactions, {len(high_risk_tx_ids)} high-risk/syndicate transactions isolated.",
            tool_name="calculate_multi_layer_risk",
            tool_input={"analyzed_count": len(scored_txs)},
            tool_output={"low_risk_count": len(low_risk_tx_ids), "high_risk_count": len(high_risk_tx_ids)}
        )

        return {
            "syndicates_detected": syndicates,
            "low_risk_tx_ids": low_risk_tx_ids,
            "high_risk_tx_ids": high_risk_tx_ids,
            "sample_risk_evaluations": scored_txs[:5]
        }


class RecoveryAgent(BaseSpecialistAgent):
    def __init__(self, tools: AgentToolRegistry, memory: AgentMemory):
        super().__init__("RecoveryAgent", tools, memory)

    def optimize_recovery(self, tx_ids: List[str], traces: List[AgentTraceStep]) -> Dict[str, Any]:
        self.log_step(
            traces,
            f"Analyzing {len(tx_ids)} failed transactions for counterfactual recovery potential & LinUCB action selection."
        )

        recovery_plans = []
        total_expected_recovery = 0.0

        for tid in tx_ids:
            # Counterfactual simulation
            cf_res = self.tools.predict_recovery_counterfactuals(tid)
            bandit_res = self.tools.bandit_select_action(tid)

            if "error" not in cf_res and "error" not in bandit_res:
                top_opt = cf_res["options"][0] if cf_res["options"] else None
                rec_amount = top_opt.get("expected_recovered_amount", 0.0) if top_opt else 0.0
                total_expected_recovery += rec_amount

                plan = {
                    "transaction_id": tid,
                    "recommended_action": bandit_res["selected_action"],
                    "expected_recovery_amount": rec_amount,
                    "risk_adjusted_ev": top_opt.get("risk_adjusted_ev", 0.0) if top_opt else 0.0,
                    "top_counterfactual": top_opt
                }
                recovery_plans.append(plan)

        self.log_step(
            traces,
            f"Counterfactual simulation finished: Total estimated recoverable revenue ₹{total_expected_recovery:,.2f} across {len(recovery_plans)} interventions.",
            tool_name="predict_recovery_counterfactuals",
            tool_input={"target_count": len(tx_ids)},
            tool_output={"total_expected_recoverable_inr": round(total_expected_recovery, 2), "plans_generated": len(recovery_plans)}
        )

        return {
            "total_expected_recovery_inr": round(total_expected_recovery, 2),
            "plans": recovery_plans
        }


class GrowthAgent(BaseSpecialistAgent):
    def __init__(self, tools: AgentToolRegistry, memory: AgentMemory):
        super().__init__("GrowthAgent", tools, memory)

    def analyze_merchant_growth(self, merchant_id: str, traces: List[AgentTraceStep]) -> Dict[str, Any]:
        self.log_step(
            traces,
            f"Querying Merchant Digital Twin for {merchant_id} to simulate growth levers & checkout optimization."
        )
        sim_res = self.tools.simulate_merchant_growth(merchant_id)
        self.log_step(
            traces,
            f"Digital Twin simulation complete: Projected GMV uplift of +₹{sim_res['projected']['total_uplift_inr']:,.2f} (+{sim_res['projected']['total_uplift_percentage']}%)",
            tool_name="simulate_merchant_growth",
            tool_input={"merchant_id": merchant_id},
            tool_output=sim_res["projected"]
        )
        return sim_res


class FinanceAgent(BaseSpecialistAgent):
    def __init__(self, tools: AgentToolRegistry, memory: AgentMemory):
        super().__init__("FinanceAgent", tools, memory)

    def reconcile_financials(self, traces: List[AgentTraceStep]) -> Dict[str, Any]:
        self.log_step(
            traces,
            "Scanning settlement payout ledger across all acquirer bank batches for fee/reserve discrepancies."
        )
        recon_summary = self.tools.reconcile_settlements_summary()
        self.log_step(
            traces,
            f"Settlement reconciliation scan complete: {recon_summary['discrepancy_batches_count']} discrepancy batches flagged with ₹{recon_summary['total_unreconciled_inr']:,.2f} total variance.",
            tool_name="reconcile_settlements_summary",
            tool_input={},
            tool_output=recon_summary
        )

        # Investigate primary discrepancy if any
        primary_investigation = None
        if recon_summary["discrepancies"]:
            sample_set_id = recon_summary["discrepancies"][0]["settlement_id"]
            primary_investigation = self.tools.investigate_settlement_discrepancy(sample_set_id)
            self.log_step(
                traces,
                f"Generated forensic Dossier {primary_investigation.get('case_id')} for settlement {sample_set_id}: Isolated ₹{primary_investigation.get('unexplained_variance'):,.2f} bank underpayment.",
                tool_name="investigate_settlement_discrepancy",
                tool_input={"settlement_id": sample_set_id},
                tool_output={"case_id": primary_investigation.get("case_id"), "variance": primary_investigation.get("unexplained_variance")}
            )

        return {
            "summary": recon_summary,
            "primary_investigation": primary_investigation
        }


class ActionAgent(BaseSpecialistAgent):
    def __init__(self, tools: AgentToolRegistry, memory: AgentMemory):
        super().__init__("ActionAgent", tools, memory)

    def execute_actions(self, plans: List[Dict[str, Any]], traces: List[AgentTraceStep]) -> Dict[str, Any]:
        self.log_step(
            traces,
            f"Passing {len(plans)} proposed recovery actions through Deterministic Policy Engine & Security Guardrails."
        )

        auto_executed = 0
        escalated = 0
        blocked = 0
        total_recovered_amount = 0.0

        for p in plans:
            tx_id = p["transaction_id"]
            act_type = p["recommended_action"]
            exec_res = self.tools.execute_recovery_action(tx_id, act_type)

            if exec_res.get("status") == "AUTO_EXECUTED":
                auto_executed += 1
                total_recovered_amount += exec_res.get("revenue_recovered", 0.0)
            elif exec_res.get("status") == "ESCALATED_TO_HUMAN":
                escalated += 1
            else:
                blocked += 1

        self.log_step(
            traces,
            f"Execution results: {auto_executed} safe actions AUTO-EXECUTED, {escalated} ESCALATED to Human Review, {blocked} BLOCKED by policy.",
            tool_name="execute_recovery_action",
            tool_input={"total_actions": len(plans)},
            tool_output={
                "auto_executed": auto_executed,
                "escalated_to_human": escalated,
                "blocked": blocked,
                "revenue_recovered_inr": round(total_recovered_amount, 2)
            }
        )

        return {
            "auto_executed": auto_executed,
            "escalated_to_human": escalated,
            "blocked": blocked,
            "total_recovered_amount_inr": round(total_recovered_amount, 2)
        }
