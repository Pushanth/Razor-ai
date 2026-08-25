from datetime import datetime
from typing import Dict, List, Any, Optional


class AgentMemory:
    """
    3-Tier Agent Memory System:
    1. Working Memory: Active task context, entity scratchpad, and planning steps.
    2. Long-Term Memory: Merchant preferences, rail reliability priors, and risk profiles.
    3. Episodic Memory: Historical actions, counterfactual outcomes, bandit rewards, and human feedback.
    """

    def __init__(self):
        # 1. Working Memory (Ephemeral / Session)
        self.working_context: Dict[str, Any] = {}
        self.plan_steps: List[Dict[str, Any]] = []

        # 2. Long-Term Memory (Persistent Entity Knowledge)
        self.long_term_memory: Dict[str, Any] = {
            "merchant_preferences": {
                "merch_0001": {"preferred_rail": "UPI", "max_auto_retry_hours": 4, "risk_tolerance": "MODERATE"},
                "merch_0002": {"preferred_rail": "CARD", "max_auto_retry_hours": 1, "risk_tolerance": "STRICT"}
            },
            "bank_downtime_patterns": {
                "HDFC": {"peak_maintenance_window": "01:00-03:00 IST", "avg_recovery_latency_min": 25},
                "SBI": {"peak_maintenance_window": "02:00-04:00 IST", "avg_recovery_latency_min": 40}
            }
        }

        # 3. Episodic Memory (Historical Decision Records & Rewards)
        self.episodic_history: List[Dict[str, Any]] = []

    def set_working_context(self, key: str, value: Any):
        self.working_context[key] = value

    def get_working_context(self, key: str, default: Any = None) -> Any:
        return self.working_context.get(key, default)

    def record_episode(
        self,
        agent_name: str,
        entity_id: str,
        action_taken: str,
        reward: float,
        outcome_status: str,
        context_summary: str
    ):
        episode = {
            "timestamp": datetime.utcnow().isoformat(),
            "agent": agent_name,
            "entity_id": entity_id,
            "action": action_taken,
            "reward": round(reward, 2),
            "status": outcome_status,
            "context": context_summary
        }
        self.episodic_history.append(episode)

    def retrieve_similar_episodes(self, entity_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Retrieves past episodic memory for the specified entity."""
        matches = [e for e in self.episodic_history if e.get("entity_id") == entity_id]
        return list(reversed(matches))[:limit]

    def get_merchant_profile(self, merchant_id: str) -> Dict[str, Any]:
        return self.long_term_memory["merchant_preferences"].get(
            merchant_id,
            {"preferred_rail": "UPI", "max_auto_retry_hours": 2, "risk_tolerance": "STANDARD"}
        )

    def clear_working_memory(self):
        self.working_context.clear()
        self.plan_steps.clear()
