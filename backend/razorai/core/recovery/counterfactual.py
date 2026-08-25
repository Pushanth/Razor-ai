from typing import List, Dict, Any, Optional
from razorai.data.models import Transaction, ActionType, CounterfactualOption, FailureReason
from razorai.core.recovery.diagnostics import FailureDiagnosticsEngine


class CounterfactualEngine:
    """
    Counterfactual Intervention Engine.
    Simulates: "What if we retry after 2 hours?", "What if we send a dynamic UPI link?",
    "What if we switch rails from Card to UPI?" and computes the Risk-Adjusted Expected Value.
    """

    def __init__(self, diagnostics: Optional[FailureDiagnosticsEngine] = None):
        self.diagnostics = diagnostics or FailureDiagnosticsEngine()

    def simulate_interventions(self, tx: Transaction) -> List[CounterfactualOption]:
        diag_res = self.diagnostics.diagnose_failure(tx)
        diag = diag_res["diagnostics"]

        if not diag["recoverable"]:
            return [
                CounterfactualOption(
                    action=ActionType.NO_ACTION,
                    description="Security block enforced. No recovery intervention allowed.",
                    expected_recovery_prob=0.0,
                    expected_recovered_amount=0.0,
                    cost=0.0,
                    friction_penalty=0.0,
                    risk_penalty=50000.0,
                    risk_adjusted_ev=-50000.0,
                    is_recommended=True
                )
            ]

        base_rate = diag["base_recovery_rate"]
        amount = tx.amount
        risk_score = tx.risk_score

        # 1. Option: SMART_RETRY_15M
        prob_15m = base_rate * (1.15 if tx.failure_reason == FailureReason.BANK_TIMEOUT else 0.85)
        prob_15m = min(0.95, max(0.10, prob_15m))
        cost_15m = 2.50 # API retry gateway fee
        friction_15m = 0.0 # zero user friction
        risk_pen_15m = (risk_score * amount * 0.25)
        ev_15m = (prob_15m * amount) - cost_15m - friction_15m - risk_pen_15m

        # 2. Option: SMART_RETRY_2H
        prob_2h = base_rate * (1.10 if tx.failure_reason == FailureReason.INSUFFICIENT_FUNDS else 0.90)
        prob_2h = min(0.95, max(0.10, prob_2h))
        cost_2h = 2.50
        friction_2h = 0.0
        risk_pen_2h = (risk_score * amount * 0.25)
        ev_2h = (prob_2h * amount) - cost_2h - friction_2h - risk_pen_2h

        # 3. Option: UPI_PAYMENT_LINK (WhatsApp / SMS Dynamic Link)
        prob_link = base_rate * (1.20 if tx.failure_reason in [FailureReason.AUTH_FAILED, FailureReason.INSUFFICIENT_FUNDS] else 0.95)
        prob_link = min(0.96, max(0.15, prob_link))
        cost_link = 8.00 # SMS/WhatsApp notification cost
        friction_link = min(amount * 0.005, 50.0) # mild user notification friction
        risk_pen_link = (risk_score * amount * 0.15) # lower risk as 2FA re-authenticated
        ev_link = (prob_link * amount) - cost_link - friction_link - risk_pen_link

        # 4. Option: SWITCH_RAIL_UPI (Auto-switch from failed Card/Netbanking to seamless UPI intent)
        prob_switch = base_rate * (1.25 if tx.payment_method != "UPI" else 0.80)
        prob_switch = min(0.97, max(0.15, prob_switch))
        cost_switch = 4.00
        friction_switch = min(amount * 0.002, 20.0)
        risk_pen_switch = (risk_score * amount * 0.20)
        ev_switch = (prob_switch * amount) - cost_switch - friction_switch - risk_pen_switch

        # 5. Option: PUSH_NOTIFICATION (App nudge)
        prob_push = base_rate * 0.70
        prob_push = min(0.85, max(0.10, prob_push))
        cost_push = 0.50
        friction_push = 5.00
        risk_pen_push = (risk_score * amount * 0.25)
        ev_push = (prob_push * amount) - cost_push - friction_push - risk_pen_push

        options = [
            CounterfactualOption(
                action=ActionType.SMART_RETRY_15M,
                description="Auto-retry over payment rail after 15 minutes as bank switch recovers.",
                expected_recovery_prob=round(prob_15m, 3),
                expected_recovered_amount=round(prob_15m * amount, 2),
                cost=round(cost_15m, 2),
                friction_penalty=round(friction_15m, 2),
                risk_penalty=round(risk_pen_15m, 2),
                risk_adjusted_ev=round(ev_15m, 2)
            ),
            CounterfactualOption(
                action=ActionType.SMART_RETRY_2H,
                description="Scheduled retry in 2 hours for salary/account liquidity refresh.",
                expected_recovery_prob=round(prob_2h, 3),
                expected_recovered_amount=round(prob_2h * amount, 2),
                cost=round(cost_2h, 2),
                friction_penalty=round(friction_2h, 2),
                risk_penalty=round(risk_pen_2h, 2),
                risk_adjusted_ev=round(ev_2h, 2)
            ),
            CounterfactualOption(
                action=ActionType.UPI_PAYMENT_LINK,
                description="Dispatch personalized 1-click dynamic UPI payment link via WhatsApp & SMS.",
                expected_recovery_prob=round(prob_link, 3),
                expected_recovered_amount=round(prob_link * amount, 2),
                cost=round(cost_link, 2),
                friction_penalty=round(friction_link, 2),
                risk_penalty=round(risk_pen_link, 2),
                risk_adjusted_ev=round(ev_link, 2)
            ),
            CounterfactualOption(
                action=ActionType.SWITCH_RAIL_UPI,
                description="Seamlessly switch payment rail to high-success UPI Intent fallback.",
                expected_recovery_prob=round(prob_switch, 3),
                expected_recovered_amount=round(prob_switch * amount, 2),
                cost=round(cost_switch, 2),
                friction_penalty=round(friction_switch, 2),
                risk_penalty=round(risk_pen_switch, 2),
                risk_adjusted_ev=round(ev_switch, 2)
            ),
            CounterfactualOption(
                action=ActionType.PUSH_NOTIFICATION,
                description="Send lightweight in-app nudge to complete pending checkout.",
                expected_recovery_prob=round(prob_push, 3),
                expected_recovered_amount=round(prob_push * amount, 2),
                cost=round(cost_push, 2),
                friction_penalty=round(friction_push, 2),
                risk_penalty=round(risk_pen_push, 2),
                risk_adjusted_ev=round(ev_push, 2)
            )
        ]

        # Sort by risk_adjusted_ev descending and mark top recommendation
        options.sort(key=lambda x: x.risk_adjusted_ev, reverse=True)
        if options:
            options[0].is_recommended = True

        return options
