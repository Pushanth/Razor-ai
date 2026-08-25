from typing import Dict, Any, Optional
from razorai.data.store import DataStore
from razorai.tools.registry import AgentToolRegistry
from razorai.agents.memory import AgentMemory
from razorai.agents.supervisor import SupervisorAgent


class MultiAgentOrchestrator:
    """
    Multi-Agent Orchestration Engine.
    Coordinates the LangGraph-style agent graph lifecycle, memory updates, and execution dispatch.
    """

    _instance: Optional["MultiAgentOrchestrator"] = None

    @classmethod
    def get_instance(cls) -> "MultiAgentOrchestrator":
        if cls._instance is None:
            store = DataStore.get_instance()
            tools = AgentToolRegistry(store=store)
            memory = AgentMemory()
            supervisor = SupervisorAgent(tools=tools, memory=memory)
            cls._instance = cls(store=store, tools=tools, memory=memory, supervisor=supervisor)
        return cls._instance

    def __init__(
        self,
        store: DataStore,
        tools: AgentToolRegistry,
        memory: AgentMemory,
        supervisor: SupervisorAgent
    ):
        self.store = store
        self.tools = tools
        self.memory = memory
        self.supervisor = supervisor

    def run_command(self, query: str) -> Dict[str, Any]:
        """Runs an end-to-end natural language operational task through the multi-agent system."""
        self.memory.set_working_context("current_query", query)
        result = self.supervisor.execute_workflow(query)
        self.memory.record_episode(
            agent_name="Supervisor",
            entity_id="WORKFLOW_RUN",
            action_taken=f"Executed query: {query}",
            reward=result["metrics"]["recovered_inr"],
            outcome_status=result["status"],
            context_summary=result["executive_summary"]
        )
        return result
