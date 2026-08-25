import math
import numpy as np
from typing import Dict, List, Any, Optional

from razorai.data.models import Transaction, Customer, Merchant, PaymentMethod


class PaymentFoundationModel:
    """
    Unified Payment Foundation Model (Vulcan Research Prototype).
    Learns a shared multi-modal payment intelligence representation
    that simultaneously encodes risk, revenue recovery, merchant dynamics, and financial attributes.
    """

    EMBEDDING_DIM = 64

    def __init__(self, seed: int = 42):
        self.seed = seed
        np.random.seed(seed)
        
        # Projection weight matrices for multimodal fusion
        self.W_tx = np.random.randn(12, self.EMBEDDING_DIM) * 0.1
        self.W_temporal = np.random.randn(8, self.EMBEDDING_DIM) * 0.1
        self.W_merchant = np.random.randn(6, self.EMBEDDING_DIM) * 0.1
        self.W_graph = np.random.randn(4, self.EMBEDDING_DIM) * 0.1
        
        # Multi-task classification / regression heads
        self.head_risk = np.random.randn(self.EMBEDDING_DIM, 1) * 0.1
        self.head_recovery = np.random.randn(self.EMBEDDING_DIM, 4) * 0.1 # 4 action recovery probabilities
        self.head_growth = np.random.randn(self.EMBEDDING_DIM, 1) * 0.1
        self.head_discrepancy = np.random.randn(self.EMBEDDING_DIM, 1) * 0.1

    def encode_transaction_features(self, tx: Transaction) -> np.ndarray:
        """Extracts normalized transaction feature vector (12-dim)."""
        log_amount = math.log1p(max(0.0, tx.amount)) / 10.0 # normalized ~0-1.2
        hour = tx.timestamp.hour
        hour_sin = math.sin(2 * math.pi * hour / 24.0)
        hour_cos = math.cos(2 * math.pi * hour / 24.0)

        # Payment method one-hot (5 dims)
        pm_vec = [0.0] * 5
        pm_map = {
            PaymentMethod.UPI: 0,
            PaymentMethod.CARD: 1,
            PaymentMethod.NETBANKING: 2,
            PaymentMethod.WALLET: 3,
            PaymentMethod.EMI: 4
        }
        pm_idx = pm_map.get(tx.payment_method, 0)
        pm_vec[pm_idx] = 1.0

        latency_norm = min(tx.latency_ms / 500.0, 1.0)
        is_high_ticket = 1.0 if tx.amount > 50000 else 0.0
        is_night_time = 1.0 if (hour >= 23 or hour <= 5) else 0.0
        has_card = 1.0 if tx.card_fingerprint else 0.0

        vec = [log_amount, hour_sin, hour_cos] + pm_vec + [latency_norm, is_high_ticket, is_night_time, has_card]
        return np.array(vec, dtype=np.float32)

    def encode_temporal_context(self, customer_history: List[Transaction]) -> np.ndarray:
        """Encodes sequence velocity, acceleration, and failure bursts (8-dim)."""
        if not customer_history:
            return np.zeros(8, dtype=np.float32)

        tx_count = len(customer_history)
        recent_txs = customer_history[-5:] # last 5 transactions
        amounts = [t.amount for t in recent_txs]
        
        avg_amount = float(np.mean(amounts)) / 10000.0
        amount_std = float(np.std(amounts)) / 10000.0 if len(amounts) > 1 else 0.0
        amount_velocity = (amounts[-1] - amounts[0]) / 10000.0 if len(amounts) > 1 else 0.0

        # Time deltas between consecutive transactions
        if len(recent_txs) > 1:
            deltas = [(recent_txs[i].timestamp - recent_txs[i-1].timestamp).total_seconds() for i in range(1, len(recent_txs))]
            min_delta_sec = min(deltas)
            burst_indicator = 1.0 if min_delta_sec < 180 else 0.0 # txs within 3 minutes
        else:
            burst_indicator = 0.0

        fail_count = sum(1 for t in recent_txs if t.status == "FAILED")
        fail_ratio = fail_count / float(len(recent_txs))
        
        return np.array([
            min(tx_count / 50.0, 1.0),
            avg_amount,
            amount_std,
            amount_velocity,
            burst_indicator,
            fail_ratio,
            1.0 if fail_count >= 2 else 0.0,
            1.0 if (len(amounts) >= 3 and amounts[-1] > 3 * np.mean(amounts[:-1])) else 0.0
        ], dtype=np.float32)

    def encode_merchant_context(self, merchant: Optional[Merchant]) -> np.ndarray:
        """Encodes merchant digital twin priors (6-dim)."""
        if not merchant:
            return np.array([0.5, 0.9, 0.02, 0.001, 0.0, 0.0], dtype=np.float32)

        gmv_scale = min(merchant.monthly_gmv / 10_000_000.0, 1.0)
        return np.array([
            gmv_scale,
            merchant.success_rate,
            merchant.refund_rate,
            merchant.dispute_rate,
            1.0 if merchant.risk_profile == "HIGH" else 0.0,
            1.0 if merchant.category in ["Gaming & Entertainment", "Financial Services"] else 0.0
        ], dtype=np.float32)

    def encode_graph_context(self, device_degree: int, customer_cluster_risk: float, is_shared_device: bool) -> np.ndarray:
        """Encodes Knowledge Graph topology & syndicate clustering (4-dim)."""
        return np.array([
            min(device_degree / 10.0, 1.0),
            customer_cluster_risk,
            1.0 if is_shared_device else 0.0,
            1.0 if (device_degree >= 5 and customer_cluster_risk > 0.6) else 0.0
        ], dtype=np.float32)

    def generate_shared_embedding(
        self,
        tx: Transaction,
        customer_history: List[Transaction],
        merchant: Optional[Merchant],
        device_degree: int = 1,
        customer_cluster_risk: float = 0.0,
        is_shared_device: bool = False
    ) -> np.ndarray:
        """
        Generates the 64-dimensional unified Payment Event Embedding (z_t)
        via non-linear multi-source projection.
        """
        v_tx = self.encode_transaction_features(tx)
        v_temp = self.encode_temporal_context(customer_history)
        v_merch = self.encode_merchant_context(merchant)
        v_graph = self.encode_graph_context(device_degree, customer_cluster_risk, is_shared_device)

        # Multimodal fusion
        h = (
            np.dot(v_tx, self.W_tx) +
            np.dot(v_temp, self.W_temporal) +
            np.dot(v_merch, self.W_merchant) +
            np.dot(v_graph, self.W_graph)
        )
        # Non-linear activation (GELU approximation)
        z_t = 0.5 * h * (1.0 + np.tanh(np.sqrt(2.0 / np.pi) * (h + 0.044715 * np.power(h, 3))))
        # L2 normalization for stable representations
        norm = np.linalg.norm(z_t)
        if norm > 1e-6:
            z_t = z_t / norm
        return z_t

    def multi_task_predict(self, embedding: np.ndarray) -> Dict[str, Any]:
        """
        Passes the shared payment embedding through downstream multi-task heads.
        """
        # Risk Head
        risk_logit = float(np.dot(embedding, self.head_risk)[0])
        risk_prob = 1.0 / (1.0 + math.exp(-max(min(risk_logit * 3.0, 10.0), -10.0)))

        # Recovery Head (Probabilities for [Retry_15m, Retry_2h, UPI_Link, Switch_Rail])
        recovery_logits = np.dot(embedding, self.head_recovery)
        exp_logits = np.exp(recovery_logits - np.max(recovery_logits))
        recovery_probs = (exp_logits / np.sum(exp_logits)).tolist()

        # Growth / LTV Uplift Head
        growth_val = float(np.dot(embedding, self.head_growth)[0])
        expected_ltv_uplift = round(max(0.0, (growth_val + 0.5) * 1000.0), 2)

        # Finance Discrepancy Head
        disc_logit = float(np.dot(embedding, self.head_discrepancy)[0])
        discrepancy_risk = 1.0 / (1.0 + math.exp(-disc_logit))

        return {
            "risk_score": round(risk_prob, 4),
            "recovery_propensities": {
                "SMART_RETRY_15M": round(recovery_probs[0], 4),
                "SMART_RETRY_2H": round(recovery_probs[1], 4),
                "UPI_PAYMENT_LINK": round(recovery_probs[2], 4),
                "SWITCH_RAIL_UPI": round(recovery_probs[3], 4)
            },
            "expected_ltv_uplift": expected_ltv_uplift,
            "discrepancy_risk": round(discrepancy_risk, 4)
        }
