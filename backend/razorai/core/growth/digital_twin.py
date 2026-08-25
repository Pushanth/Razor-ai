from typing import Dict, Any, List, Optional
from razorai.data.models import Merchant, MerchantTwin
from razorai.data.store import DataStore


class MerchantGrowthEngine:
    """
    Merchant Digital Twin & Growth Simulator 2.0.
    Builds high-fidelity merchant digital twins and simulates what-if interventions:
    - Smart Retry Optimization
    - Dynamic Rail Addition (UPI Intent / No-cost EMI)
    - Checkout Friction Reduction
    - Agentic Conversion Optimization
    """

    def __init__(self, store: Optional[DataStore] = None):
        self.store = store or DataStore.get_instance()

    def get_or_create_twin(self, merchant_id: str) -> MerchantTwin:
        if merchant_id in self.store.merchant_twins:
            return self.store.merchant_twins[merchant_id]

        merchant = self.store.merchants.get(merchant_id)
        if not merchant:
            # Fallback mock twin
            return MerchantTwin(
                merchant_id=merchant_id,
                name="Default Merchant",
                current_gmv=2_500_000.0,
                current_success_rate=0.91,
                current_refund_rate=0.025,
                checkout_friction_score=0.09,
                upi_share=0.65,
                card_share=0.25,
                netbanking_share=0.10
            )

        twin = MerchantTwin(
            merchant_id=merchant.id,
            name=merchant.name,
            current_gmv=merchant.monthly_gmv,
            current_success_rate=merchant.success_rate,
            current_refund_rate=merchant.refund_rate,
            checkout_friction_score=round(1.0 - merchant.success_rate, 3),
            upi_share=0.68,
            card_share=0.22,
            netbanking_share=0.10
        )
        self.store.merchant_twins[merchant.id] = twin
        return twin

    def simulate_what_if(
        self,
        merchant_id: str,
        enable_smart_retry: bool = True,
        add_emi_and_upi_intent: bool = True,
        reduce_checkout_friction_pct: float = 15.0
    ) -> Dict[str, Any]:
        """
        Runs comprehensive counterfactual simulation on the Merchant Digital Twin.
        """
        twin = self.get_or_create_twin(merchant_id)
        base_gmv = twin.current_gmv
        base_success = twin.current_success_rate

        # 1. Smart Retry Impact
        # Failed volume = GMV * (1 - success_rate)
        failed_volume = base_gmv * (1.0 - base_success)
        retry_recovery_pct = 0.58 if enable_smart_retry else 0.0
        retry_gmv_gain = failed_volume * retry_recovery_pct

        # 2. Dynamic Rail Expansion (EMI + 1-Click UPI) Impact
        rail_uplift_pct = 0.042 if add_emi_and_upi_intent else 0.0
        rail_gmv_gain = base_gmv * rail_uplift_pct

        # 3. Checkout Friction Reduction Impact
        friction_factor = (reduce_checkout_friction_pct / 100.0) * 0.35
        friction_gmv_gain = base_gmv * friction_factor

        # Projected totals
        projected_gmv = round(base_gmv + retry_gmv_gain + rail_gmv_gain + friction_gmv_gain, 2)
        total_uplift_inr = round(projected_gmv - base_gmv, 2)
        total_uplift_pct = round((total_uplift_inr / base_gmv) * 100, 2) if base_gmv > 0 else 0.0
        projected_success_rate = round(min(0.985, base_success + (retry_recovery_pct * (1.0 - base_success))), 4)

        simulation_results = {
            "merchant_id": merchant_id,
            "merchant_name": twin.name,
            "baseline": {
                "monthly_gmv": round(base_gmv, 2),
                "success_rate": round(base_success * 100, 2),
                "monthly_failed_gmv": round(failed_volume, 2)
            },
            "projected": {
                "monthly_gmv": projected_gmv,
                "projected_success_rate": round(projected_success_rate * 100, 2),
                "total_uplift_inr": total_uplift_inr,
                "total_uplift_percentage": total_uplift_pct
            },
            "breakdown": [
                {
                    "lever": "AI Smart Retry Engine",
                    "description": "Recovers transient bank timeouts & fund refreshes autonomously",
                    "gmv_gain_inr": round(retry_gmv_gain, 2),
                    "percentage_contribution": round((retry_gmv_gain / max(total_uplift_inr, 1.0)) * 100, 1),
                    "active": enable_smart_retry
                },
                {
                    "lever": "1-Click UPI & EMI Rail Expansion",
                    "description": "Unlocks high-ticket affordability & instant auth",
                    "gmv_gain_inr": round(rail_gmv_gain, 2),
                    "percentage_contribution": round((rail_gmv_gain / max(total_uplift_inr, 1.0)) * 100, 1),
                    "active": add_emi_and_upi_intent
                },
                {
                    "lever": f"Checkout Friction Reduction ({reduce_checkout_friction_pct}%)",
                    "description": "Pre-fills addresses and accelerates payment handoff",
                    "gmv_gain_inr": round(friction_gmv_gain, 2),
                    "percentage_contribution": round((friction_gmv_gain / max(total_uplift_inr, 1.0)) * 100, 1),
                    "active": reduce_checkout_friction_pct > 0
                }
            ],
            "actionable_recommendations": [
                f"Activate AI Smart Retry on UPI rail to instantly capture +₹{round(retry_gmv_gain/100000, 2)}L monthly.",
                f"Enable Affordability EMI widget on checkouts over ₹3,000 for +{round(rail_uplift_pct*100, 1)}% GMV expansion.",
                f"Deploy 1-click address prefill to reduce drop-off by {reduce_checkout_friction_pct}%."
            ]
        }
        twin.simulations["latest"] = simulation_results
        return simulation_results
