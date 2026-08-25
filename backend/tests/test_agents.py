import pytest
from razorai.data.store import DataStore
from razorai.tools.registry import AgentToolRegistry
from razorai.agents.memory import AgentMemory
from razorai.agents.supervisor import SupervisorAgent
from razorai.agents.orchestrator import MultiAgentOrchestrator


def test_agent_memory():
    mem = AgentMemory()
    mem.set_working_context("task", "recover_failed_txs")
    assert mem.get_working_context("task") == "recover_failed_txs"
    
    mem.record_episode(
        agent_name="RecoveryAgent",
        entity_id="pay_001",
        action_taken="SMART_RETRY_15M",
        reward=1500.0,
        outcome_status="SUCCESS",
        context_summary="Recovered bank timeout payment"
    )
    episodes = mem.retrieve_similar_episodes("pay_001")
    assert len(episodes) == 1
    assert episodes[0]["reward"] == 1500.0


def test_tool_registry():
    store = DataStore.get_instance()
    tools = AgentToolRegistry(store=store)
    
    failed_txs = tools.search_failed_transactions(limit=5)
    assert isinstance(failed_txs, list)
    
    if failed_txs:
        tid = failed_txs[0]["id"]
        tx_info = tools.get_transaction(tid)
        assert tx_info["id"] == tid
        
        cf_res = tools.predict_recovery_counterfactuals(tid)
        assert "options" in cf_res


def test_supervisor_and_orchestrator():
    orchestrator = MultiAgentOrchestrator.get_instance()
    prompt = "Investigate today's payment anomalies and recover all low-risk failed transactions where expected recovery value exceeds ₹10,000."
    
    result = orchestrator.run_command(prompt)
    assert result["status"] == "COMPLETED"
    assert "metrics" in result
    assert "agent_traces" in result
    assert len(result["agent_traces"]) > 0
    assert result["metrics"]["policy_violations"] == 0
