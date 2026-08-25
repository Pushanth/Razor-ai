import numpy as np
from typing import Dict, List, Any, Tuple
from razorai.data.models import Transaction, ActionType, FailureReason


class ContextualRecoveryBandit:
    """
    Contextual Multi-Armed Bandit (LinUCB) for optimal payment recovery policy learning.
    Learns to maximize Risk-Adjusted Revenue:
      Reward = Recovered Revenue - Customer Friction - Gateway Fee - Risk Exposure
    """

    ACTIONS = [
        ActionType.SMART_RETRY_15M,
        ActionType.SMART_RETRY_2H,
        ActionType.UPI_PAYMENT_LINK,
        ActionType.SWITCH_RAIL_UPI,
        ActionType.PUSH_NOTIFICATION
    ]
    CONTEXT_DIM = 6

    def __init__(self, alpha: float = 0.35):
        self.alpha = alpha
        self.num_actions = len(self.ACTIONS)
        
        # LinUCB parameters: A_a (d x d matrix), b_a (d-dim vector)
        self.A = [np.identity(self.CONTEXT_DIM, dtype=np.float32) for _ in range(self.num_actions)]
        self.b = [np.zeros((self.CONTEXT_DIM, 1), dtype=np.float32) for _ in range(self.num_actions)]
        
        # Telemetry & tracking
        self.action_counts = {a.value: 0 for a in self.ACTIONS}
        self.cumulative_rewards = {a.value: 0.0 for a in self.ACTIONS}
        self.total_decisions = 0
        self.total_reward = 0.0

        # Pre-seed with realistic fintech baseline experience (warm start)
        self._warm_start_prior_experience()

    def _warm_start_prior_experience(self):
        """Warm-starts the LinUCB matrices with 500 synthetic historical recoveries."""
        for _ in range(500):
            # Synthetic context: [log_amount, is_timeout, is_auth_fail, is_card, risk_score, 1.0]
            log_amt = float(np.random.uniform(0.3, 1.0))
            is_timeout = float(np.random.choice([0.0, 1.0]))
            is_auth = float(np.random.choice([0.0, 1.0]) if is_timeout == 0.0 else 0.0)
            is_card = float(np.random.choice([0.0, 1.0]))
            risk = float(np.random.uniform(0.05, 0.40))
            ctx = np.array([[log_amt], [is_timeout], [is_auth], [is_card], [risk], [1.0]], dtype=np.float32)

            # Assign realistic rewards for actions
            if is_timeout:
                best_act_idx = 0 # Retry 15m
                rew = float(np.random.uniform(0.75, 0.92))
            elif is_auth:
                best_act_idx = 2 # UPI Link
                rew = float(np.random.uniform(0.70, 0.88))
            elif is_card:
                best_act_idx = 3 # Switch to UPI
                rew = float(np.random.uniform(0.65, 0.85))
            else:
                best_act_idx = 1 # Retry 2h
                rew = float(np.random.uniform(0.55, 0.75))

            self.A[best_act_idx] += np.dot(ctx, ctx.T)
            self.b[best_act_idx] += rew * ctx
            self.action_counts[self.ACTIONS[best_act_idx].value] += 1
            self.cumulative_rewards[self.ACTIONS[best_act_idx].value] += rew * 1000.0
            self.total_decisions += 1
            self.total_reward += rew * 1000.0

    def extract_context(self, tx: Transaction) -> np.ndarray:
        """Extracts normalized 6-dim context vector for bandit decision."""
        log_amount = min(np.log1p(max(0.0, tx.amount)) / 10.0, 1.5)
        is_timeout = 1.0 if tx.failure_reason == FailureReason.BANK_TIMEOUT else 0.0
        is_auth_fail = 1.0 if tx.failure_reason in [FailureReason.AUTH_FAILED, FailureReason.INSUFFICIENT_FUNDS] else 0.0
        is_card = 1.0 if tx.payment_method == "CARD" else 0.0
        risk_score = float(tx.risk_score)
        bias = 1.0

        return np.array([[log_amount], [is_timeout], [is_auth_fail], [is_card], [risk_score], [bias]], dtype=np.float32)

    def select_action(self, tx: Transaction) -> Tuple[ActionType, Dict[str, Any]]:
        """
        LinUCB action selection:
          theta_a = A_a^{-1} * b_a
          p_a = theta_a^T * x + alpha * sqrt(x^T * A_a^{-1} * x)
        """
        x = self.extract_context(tx)
        p_scores = []
        theta_list = []
        ucb_bonuses = []

        for a_idx in range(self.num_actions):
            A_inv = np.linalg.inv(self.A[a_idx])
            theta_a = np.dot(A_inv, self.b[a_idx])
            expected_payoff = float(np.dot(theta_a.T, x)[0, 0])
            ucb_bonus = float(self.alpha * np.sqrt(np.dot(np.dot(x.T, A_inv), x)[0, 0]))
            total_score = expected_payoff + ucb_bonus
            
            p_scores.append(total_score)
            theta_list.append(expected_payoff)
            ucb_bonuses.append(ucb_bonus)

        best_idx = int(np.argmax(p_scores))
        chosen_action = self.ACTIONS[best_idx]

        details = {
            "chosen_action": chosen_action.value,
            "action_scores": {
                self.ACTIONS[i].value: {
                    "expected_payoff": round(theta_list[i], 4),
                    "ucb_bonus": round(ucb_bonuses[i], 4),
                    "total_ucb_score": round(p_scores[i], 4)
                }
                for i in range(self.num_actions)
            },
            "exploration_bonus": round(ucb_bonuses[best_idx], 4),
            "exploitation_score": round(theta_list[best_idx], 4)
        }
        return chosen_action, details

    def update_policy(self, tx: Transaction, action: ActionType, observed_reward: float):
        """Updates the LinUCB online policy based on observed outcome."""
        try:
            a_idx = self.ACTIONS.index(action)
        except ValueError:
            return

        x = self.extract_context(tx)
        self.A[a_idx] += np.dot(x, x.T)
        self.b[a_idx] += observed_reward * x

        self.action_counts[action.value] += 1
        self.cumulative_rewards[action.value] += observed_reward
        self.total_decisions += 1
        self.total_reward += observed_reward

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_decisions": self.total_decisions,
            "total_reward": round(self.total_reward, 2),
            "action_distribution": self.action_counts,
            "action_cumulative_rewards": {k: round(v, 2) for k, v in self.cumulative_rewards.items()},
            "exploration_alpha": self.alpha
        }
