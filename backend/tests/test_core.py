import pytest
from razorai.data.store import DataStore
from razorai.core.foundation.embedding import PaymentFoundationModel
from razorai.core.foundation.sequence_model import TemporalSequenceAnalyzer
from razorai.core.graph.knowledge_graph import PaymentKnowledgeGraph
from razorai.core.risk.risk_engine import AIRiskManager
from razorai.core.recovery.counterfactual import CounterfactualEngine
from razorai.core.recovery.bandit import ContextualRecoveryBandit
from razorai.core.growth.digital_twin import MerchantGrowthEngine
from razorai.core.finance.reconciliation import AutonomousFinanceController


def test_data_store_and_generator():
    store = DataStore.get_instance()
    assert len(store.customers) > 0
    assert len(store.merchants) > 0
    assert len(store.devices) > 0
    assert len(store.transactions) > 0
    assert len(store.settlements) > 0


def test_foundation_model_embedding():
    store = DataStore.get_instance()
    tx = list(store.transactions.values())[0]
    model = PaymentFoundationModel()
    
    emb = model.generate_shared_embedding(
        tx=tx,
        customer_history=[],
        merchant=None
    )
    assert len(emb) == 64
    preds = model.multi_task_predict(emb)
    assert "risk_score" in preds
    assert "recovery_propensities" in preds
    assert "expected_ltv_uplift" in preds


def test_5_layer_risk_engine():
    store = DataStore.get_instance()
    tx = list(store.transactions.values())[0]
    risk_manager = AIRiskManager(store)
    
    result = risk_manager.compute_fused_risk(tx)
    assert "final_risk_score" in result
    assert 0.0 <= result["final_risk_score"] <= 1.0
    assert "risk_tier" in result
    assert "attributions" in result
    assert len(result["attributions"]) == 5


def test_knowledge_graph_and_syndicates():
    store = DataStore.get_instance()
    graph_engine = PaymentKnowledgeGraph(store)
    
    syndicates = graph_engine.detect_syndicates()
    assert isinstance(syndicates, list)
    
    cust_id = list(store.customers.keys())[0]
    network = graph_engine.analyze_entity_network(cust_id)
    assert "graph_risk_score" in network
    assert "nodes" in network
    assert "edges" in network


def test_counterfactual_and_bandit():
    store = DataStore.get_instance()
    tx = list(store.transactions.values())[0]
    cf_engine = CounterfactualEngine()
    bandit = ContextualRecoveryBandit()
    
    options = cf_engine.simulate_interventions(tx)
    assert len(options) > 0
    assert any(opt.is_recommended for opt in options)
    
    action, details = bandit.select_action(tx)
    assert action is not None
    assert "chosen_action" in details
    
    # Test online policy update
    bandit.update_policy(tx, action, observed_reward=850.0)
    assert bandit.total_decisions > 0


def test_merchant_digital_twin():
    store = DataStore.get_instance()
    merch_id = list(store.merchants.keys())[0]
    growth_engine = MerchantGrowthEngine(store)
    
    sim = growth_engine.simulate_what_if(
        merchant_id=merch_id,
        enable_smart_retry=True,
        add_emi_and_upi_intent=True,
        reduce_checkout_friction_pct=15.0
    )
    assert "baseline" in sim
    assert "projected" in sim
    assert sim["projected"]["total_uplift_inr"] > 0


def test_finance_reconciliation():
    store = DataStore.get_instance()
    controller = AutonomousFinanceController(store)
    
    recon = controller.reconcile_all_settlements()
    assert "total_settlement_batches" in recon
    
    settle_id = list(store.settlements.keys())[0]
    investigation = controller.investigate_settlement(settle_id)
    assert "waterfall" in investigation
    assert "case_id" in investigation
