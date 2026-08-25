import math
import numpy as np
from typing import Dict, List, Any, Optional

from razorai.data.models import Transaction, Customer, Merchant, Device, RiskTier
from razorai.data.store import DataStore
from razorai.core.foundation.embedding import PaymentFoundationModel
from razorai.core.foundation.sequence_model import TemporalSequenceAnalyzer
from razorai.core.graph.knowledge_graph import PaymentKnowledgeGraph


class AIRiskManager:
    """
    Multi-layer AI Risk Manager 2.0 & Risk Fusion Engine.
    Evaluates Transaction, Customer, Merchant, Network/Graph, and Temporal Risk layers,
    fusing them into an explainable final risk score with SHAP-style attribution.
    """

    def __init__(
        self,
        store: Optional[DataStore] = None,
        foundation_model: Optional[PaymentFoundationModel] = None,
        graph_engine: Optional[PaymentKnowledgeGraph] = None,
        sequence_analyzer: Optional[TemporalSequenceAnalyzer] = None
    ):
        self.store = store or DataStore.get_instance()
        self.foundation_model = foundation_model or PaymentFoundationModel()
        self.graph_engine = graph_engine or PaymentKnowledgeGraph(self.store)
        self.sequence_analyzer = sequence_analyzer or TemporalSequenceAnalyzer()

        # Layer fusion weights (calibrated for fintech fraud detection)
        self.weights = {
            "transaction_risk": 0.20,
            "customer_risk": 0.20,
            "merchant_risk": 0.15,
            "graph_risk": 0.25,
            "temporal_risk": 0.20
        }

    def evaluate_layer1_transaction(self, tx: Transaction) -> Dict[str, Any]:
        """Layer 1: Transaction-level attributes and payload anomaly."""
        score = 0.05
        evidence = []

        if tx.amount > 50000.0:
            score += 0.35
            evidence.append(f"High-ticket transaction: ₹{tx.amount:,.2f}")
        elif tx.amount > 15000.0:
            score += 0.15

        if tx.location == "Unknown / Proxy Exit":
            score += 0.40
            evidence.append("Anonymized proxy / Tor exit node IP detected")

        if tx.payment_method == "CARD" and not tx.card_fingerprint:
            score += 0.20
            evidence.append("Missing card tokenization fingerprint")

        score = min(0.99, score)
        return {
            "score": round(score, 4),
            "evidence": evidence
        }

    def evaluate_layer2_customer(self, customer: Optional[Customer], tx: Transaction) -> Dict[str, Any]:
        """Layer 2: Customer historical behavior, failure rates, and device hops."""
        if not customer:
            return {"score": 0.30, "evidence": ["New unprofiled customer"]}

        score = 0.05
        evidence = []

        if customer.risk_tier == RiskTier.CRITICAL:
            score += 0.70
            evidence.append("Customer flagged with CRITICAL risk profile")
        elif customer.risk_tier == RiskTier.HIGH:
            score += 0.40
            evidence.append("Customer in HIGH risk tier")

        if customer.tx_count > 0:
            fail_rate = customer.failure_count / float(customer.tx_count)
            if fail_rate > 0.60 and customer.tx_count >= 3:
                score += 0.30
                evidence.append(f"High historical failure rate: {round(fail_rate*100, 1)}%")

        if len(customer.linked_devices) >= 3:
            score += 0.25
            evidence.append(f"Customer has hopped across {len(customer.linked_devices)} distinct devices")

        score = min(0.99, score)
        return {
            "score": round(score, 4),
            "evidence": evidence
        }

    def evaluate_layer3_merchant(self, merchant: Optional[Merchant]) -> Dict[str, Any]:
        """Layer 3: Merchant risk profile, dispute surge, and category baseline."""
        if not merchant:
            return {"score": 0.15, "evidence": []}

        score = 0.05
        evidence = []

        if merchant.dispute_rate > 0.005:
            score += 0.35
            evidence.append(f"Elevated dispute rate: {round(merchant.dispute_rate*100, 2)}% (MDR threshold exceeded)")

        if merchant.refund_rate > 0.04:
            score += 0.20
            evidence.append(f"High refund velocity: {round(merchant.refund_rate*100, 2)}%")

        if merchant.category in ["Gaming & Entertainment", "Financial Services"]:
            score += 0.10

        score = min(0.99, score)
        return {
            "score": round(score, 4),
            "evidence": evidence
        }

    def evaluate_layer4_graph(self, tx: Transaction) -> Dict[str, Any]:
        """Layer 4: Payment Knowledge Graph network risk & syndicate connectivity."""
        graph_analysis = self.graph_engine.analyze_entity_network(tx.customer_id, max_depth=2)
        score = graph_analysis["graph_risk_score"]
        evidence = []

        if graph_analysis["is_syndicate_member"]:
            score = max(score, 0.88)
            evidence.append(f"Connected to fraud syndicate cluster (device degree: {graph_analysis['shared_device_degree']})")
        elif graph_analysis["shared_device_degree"] > 2:
            evidence.append(f"Shared device with {graph_analysis['shared_device_degree']} other customer accounts")

        return {
            "score": round(score, 4),
            "evidence": evidence,
            "subgraph_summary": f"{graph_analysis['node_count']} nodes, {graph_analysis['edge_count']} edges"
        }

    def evaluate_layer5_temporal(self, tx: Transaction) -> Dict[str, Any]:
        """Layer 5: Temporal sequence dynamics and rapid velocity surges."""
        cust_history = self.store.get_customer_transactions(tx.customer_id, limit=10)
        seq_analysis = self.sequence_analyzer.analyze_sequence(cust_history)
        score = seq_analysis["sequence_risk_score"]
        evidence = []

        if seq_analysis["is_escalating_pattern"]:
            evidence.append("Escalating transaction amounts in short time window")
        if seq_analysis["is_failure_burst"]:
            evidence.append(f"Rapid failure burst cascade ({seq_analysis['burst_interval_sec']}s interval)")

        return {
            "score": round(score, 4),
            "evidence": evidence,
            "velocity_multiplier": seq_analysis["velocity_multiplier"]
        }

    def compute_fused_risk(self, tx: Transaction) -> Dict[str, Any]:
        """
        Executes full 5-layer risk evaluation, generates shared embedding,
        applies Bayesian Risk Fusion, and computes SHAP-style feature attributions.
        """
        customer = self.store.customers.get(tx.customer_id)
        merchant = self.store.merchants.get(tx.merchant_id)

        l1 = self.evaluate_layer1_transaction(tx)
        l2 = self.evaluate_layer2_customer(customer, tx)
        l3 = self.evaluate_layer3_merchant(merchant)
        l4 = self.evaluate_layer4_graph(tx)
        l5 = self.evaluate_layer5_temporal(tx)

        # Generate shared foundation embedding
        cust_history = self.store.get_customer_transactions(tx.customer_id, limit=5)
        embedding = self.foundation_model.generate_shared_embedding(
            tx=tx,
            customer_history=cust_history,
            merchant=merchant,
            device_degree=1,
            customer_cluster_risk=l4["score"],
            is_shared_device=("Shared device" in " ".join(l4["evidence"]))
        )
        tx.embedding = embedding.tolist()

        # Multi-task predictions from foundation representation
        foundation_preds = self.foundation_model.multi_task_predict(embedding)
        foundation_risk = foundation_preds["risk_score"]

        # Weighted Risk Fusion
        weighted_sum = (
            self.weights["transaction_risk"] * l1["score"] +
            self.weights["customer_risk"] * l2["score"] +
            self.weights["merchant_risk"] * l3["score"] +
            self.weights["graph_risk"] * l4["score"] +
            self.weights["temporal_risk"] * l5["score"]
        )

        # Cross-layer synergy bonus (if both graph risk and temporal risk are high)
        if l4["score"] > 0.70 and l5["score"] > 0.50:
            weighted_sum = min(0.99, weighted_sum + 0.15)

        # Blend with foundation model head (70% layer fusion + 30% foundation embedding head)
        final_risk = round(0.70 * weighted_sum + 0.30 * foundation_risk, 4)
        final_risk = min(0.99, max(0.01, final_risk))

        # Risk Tier Classification
        if final_risk >= 0.80:
            tier = RiskTier.CRITICAL
            recommendation = "BLOCK_TRANSACTION"
        elif final_risk >= 0.55:
            tier = RiskTier.HIGH
            recommendation = "HOLD_FOR_REVIEW"
        elif final_risk >= 0.25:
            tier = RiskTier.MEDIUM
            recommendation = "STEP_UP_2FA"
        else:
            tier = RiskTier.LOW
            recommendation = "APPROVE"

        # Update transaction risk
        tx.risk_score = final_risk
        tx.risk_tier = tier

        # Construct SHAP-style Explainable Feature Attributions
        attributions = [
            {
                "layer": "Layer 1: Transaction Risk",
                "score": l1["score"],
                "weight": self.weights["transaction_risk"],
                "contribution": round(l1["score"] * self.weights["transaction_risk"], 3),
                "evidence": l1["evidence"]
            },
            {
                "layer": "Layer 2: Customer Risk",
                "score": l2["score"],
                "weight": self.weights["customer_risk"],
                "contribution": round(l2["score"] * self.weights["customer_risk"], 3),
                "evidence": l2["evidence"]
            },
            {
                "layer": "Layer 3: Merchant Risk",
                "score": l3["score"],
                "weight": self.weights["merchant_risk"],
                "contribution": round(l3["score"] * self.weights["merchant_risk"], 3),
                "evidence": l3["evidence"]
            },
            {
                "layer": "Layer 4: Network/Graph Risk",
                "score": l4["score"],
                "weight": self.weights["graph_risk"],
                "contribution": round(l4["score"] * self.weights["graph_risk"], 3),
                "evidence": l4["evidence"]
            },
            {
                "layer": "Layer 5: Temporal Risk",
                "score": l5["score"],
                "weight": self.weights["temporal_risk"],
                "contribution": round(l5["score"] * self.weights["temporal_risk"], 3),
                "evidence": l5["evidence"]
            }
        ]

        all_evidence = l1["evidence"] + l2["evidence"] + l3["evidence"] + l4["evidence"] + l5["evidence"]

        return {
            "transaction_id": tx.id,
            "final_risk_score": final_risk,
            "risk_tier": tier.value,
            "recommendation": recommendation,
            "confidence": round(0.85 + (abs(final_risk - 0.5) * 0.28), 3),
            "foundation_prediction": foundation_preds,
            "layers": {
                "layer1_transaction": l1,
                "layer2_customer": l2,
                "layer3_merchant": l3,
                "layer4_graph": l4,
                "layer5_temporal": l5
            },
            "attributions": attributions,
            "evidence_summary": all_evidence or ["Standard transaction behavior within expected tolerances."]
        }
