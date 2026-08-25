from datetime import datetime
from typing import List, Dict, Any
import numpy as np

from razorai.data.models import Transaction


class TemporalSequenceAnalyzer:
    """
    Analyzes temporal sequences of transactions for velocity surges,
    rapid failure cascades, and sudden amount escalations.
    """

    def __init__(self):
        pass

    def analyze_sequence(self, transactions: List[Transaction]) -> Dict[str, Any]:
        """
        Analyzes a chronological sequence of customer transactions.
        Example pattern:
          10:01 -> ₹500
          10:03 -> ₹800
          10:04 -> ₹15,000
          10:05 -> failed
          10:07 -> ₹20,000
        """
        if not transactions:
            return {
                "sequence_risk_score": 0.05,
                "velocity_multiplier": 1.0,
                "is_escalating_pattern": False,
                "is_failure_burst": False,
                "burst_interval_sec": None,
                "summary": "No historical sequence data."
            }

        sorted_txs = sorted(transactions, key=lambda x: x.timestamp)
        amounts = [t.amount for t in sorted_txs]
        statuses = [t.status for t in sorted_txs]

        # Calculate time intervals between transactions
        intervals = []
        if len(sorted_txs) > 1:
            for i in range(1, len(sorted_txs)):
                delta = (sorted_txs[i].timestamp - sorted_txs[i-1].timestamp).total_seconds()
                intervals.append(delta)

        # Check for rapid succession burst (< 300 seconds between successive transactions)
        min_interval = min(intervals) if intervals else 999999.0
        is_failure_burst = (len(statuses) >= 3 and statuses.count("FAILED") >= 2 and min_interval < 300)

        # Check for exponential amount escalation (e.g. 500 -> 800 -> 15000)
        is_escalating_pattern = False
        if len(amounts) >= 3:
            recent_avg = np.mean(amounts[-2:])
            prior_avg = np.mean(amounts[:-2]) if len(amounts) > 2 else amounts[0]
            if prior_avg > 0 and (recent_avg / prior_avg) > 4.0:
                is_escalating_pattern = True

        # Calculate sequence risk score
        risk = 0.05
        if is_escalating_pattern:
            risk += 0.45
        if is_failure_burst:
            risk += 0.35
        if min_interval < 60: # 60 seconds interval
            risk += 0.20

        risk = min(0.99, risk)
        velocity_mult = round(3600.0 / max(min_interval, 1.0), 2) if min_interval < 3600 else 1.0

        return {
            "sequence_risk_score": round(risk, 4),
            "velocity_multiplier": velocity_mult,
            "is_escalating_pattern": is_escalating_pattern,
            "is_failure_burst": is_failure_burst,
            "burst_interval_sec": round(min_interval, 1) if intervals else None,
            "summary": (
                f"Escalating ticket size detected ({len(amounts)} txs)" if is_escalating_pattern
                else f"Failure cascade observed ({statuses.count('FAILED')} failures in {round(min_interval)}s)" if is_failure_burst
                else "Normal temporal sequence behavior."
            )
        }
