import numpy as np
from scipy import stats
from typing import Dict, List, Any


class ModelDriftDetector:
    """
    MLOps Statistical Drift Detector.
    Calculates Population Stability Index (PSI) and Kolmogorov-Smirnov (KS) tests
    to monitor feature drift, prediction distribution shifts, and trigger automated retraining alerts.
    """

    def __init__(self):
        # Baseline reference distribution (from training set)
        np.random.seed(42)
        self.baseline_amounts = np.random.exponential(scale=1800, size=2000)
        self.baseline_risk_scores = np.random.beta(a=1.5, b=8.0, size=2000)
        self.baseline_failure_rate = 0.085

    def calculate_psi(self, baseline: np.ndarray, current: np.ndarray, num_buckets: int = 10) -> float:
        """Calculates Population Stability Index between baseline and current distributions."""
        if len(current) == 0 or len(baseline) == 0:
            return 0.0

        percentiles = np.linspace(0, 100, num_buckets + 1)
        breakpoints = np.percentile(baseline, percentiles)
        breakpoints[0] = -np.inf
        breakpoints[-1] = np.inf

        base_counts, _ = np.histogram(baseline, bins=breakpoints)
        curr_counts, _ = np.histogram(current, bins=breakpoints)

        base_pct = np.maximum(base_counts / float(len(baseline)), 1e-4)
        curr_pct = np.maximum(curr_counts / float(len(current)), 1e-4)

        psi = np.sum((curr_pct - base_pct) * np.log(curr_pct / base_pct))
        return float(psi)

    def evaluate_drift(self, current_amounts: List[float], current_risk_scores: List[float]) -> Dict[str, Any]:
        curr_amt = np.array(current_amounts, dtype=np.float32) if current_amounts else self.baseline_amounts
        curr_risk = np.array(current_risk_scores, dtype=np.float32) if current_risk_scores else self.baseline_risk_scores

        amount_psi = self.calculate_psi(self.baseline_amounts, curr_amt)
        risk_psi = self.calculate_psi(self.baseline_risk_scores, curr_risk)

        # KS Test for distribution shift
        ks_amt_stat, ks_amt_pval = stats.ks_2samp(self.baseline_amounts, curr_amt)
        ks_risk_stat, ks_risk_pval = stats.ks_2samp(self.baseline_risk_scores, curr_risk)

        # Drift severity interpretation
        # PSI < 0.1: No change; 0.1 <= PSI <= 0.2: Moderate shift; PSI > 0.2: Significant drift
        is_amount_drifting = amount_psi > 0.15
        is_risk_drifting = risk_psi > 0.15
        retraining_recommended = is_amount_drifting or is_risk_drifting

        return {
            "amount_feature_drift": {
                "psi_score": round(amount_psi, 4),
                "ks_statistic": round(float(ks_amt_stat), 4),
                "p_value": round(float(ks_amt_pval), 4),
                "drift_detected": is_amount_drifting,
                "status": "SIGNIFICANT_DRIFT" if amount_psi > 0.2 else "MODERATE_DRIFT" if amount_psi > 0.1 else "STABLE"
            },
            "risk_prediction_drift": {
                "psi_score": round(risk_psi, 4),
                "ks_statistic": round(float(ks_risk_stat), 4),
                "p_value": round(float(ks_risk_pval), 4),
                "drift_detected": is_risk_drifting,
                "status": "SIGNIFICANT_DRIFT" if risk_psi > 0.2 else "MODERATE_DRIFT" if risk_psi > 0.1 else "STABLE"
            },
            "overall_model_health": "RETRAINING_TRIGGERED" if retraining_recommended else "OPTIMAL",
            "automated_action": (
                "Trigger candidate model retraining pipeline on fresh 7-day data window."
                if retraining_recommended
                else "Model distributions healthy. Continuous monitoring active."
            )
        }
