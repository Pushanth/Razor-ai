import os
import asyncio
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from razorai.data.store import DataStore
from razorai.agents.orchestrator import MultiAgentOrchestrator
from razorai.core.risk.risk_engine import AIRiskManager
from razorai.core.graph.knowledge_graph import PaymentKnowledgeGraph
from razorai.core.recovery.counterfactual import CounterfactualEngine
from razorai.core.recovery.bandit import ContextualRecoveryBandit
from razorai.core.growth.digital_twin import MerchantGrowthEngine
from razorai.core.finance.reconciliation import AutonomousFinanceController
from razorai.security.policy_engine import PolicyGuardrailEngine
from razorai.security.decision_ledger import AIDecisionLedger
from razorai.security.red_team import RedTeamSecuritySuite
from razorai.simulator.commerce_sandbox import AgenticCommerceSimulator
from razorai.streaming.streamer import TransactionStreamer
from razorai.streaming.event_bus import EventBus
from razorai.mlops.drift_detector import ModelDriftDetector
from razorai.mlops.experiments import ResearchExperimentHarness


def create_app() -> FastAPI:
    app = FastAPI(
        title="RAZORAI: Autonomous Financial Intelligence & Agentic Commerce Platform",
        description="Unified Payment Intelligence, Multi-Agent Orchestration, 5-Layer Risk, Counterfactual Recovery, and Immutable Decision Ledger API.",
        version="2.0.0"
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Initialize Core Singletons
    store = DataStore.get_instance()
    orchestrator = MultiAgentOrchestrator.get_instance()
    risk_manager = AIRiskManager(store)
    graph_engine = PaymentKnowledgeGraph(store)
    counterfactual_engine = CounterfactualEngine()
    bandit_engine = ContextualRecoveryBandit()
    growth_engine = MerchantGrowthEngine(store)
    finance_controller = AutonomousFinanceController(store)
    policy_engine = PolicyGuardrailEngine()
    decision_ledger = AIDecisionLedger(store)
    red_team = RedTeamSecuritySuite(policy_engine)
    commerce_simulator = AgenticCommerceSimulator(store, risk_manager, policy_engine, decision_ledger)
    event_bus = EventBus.get_instance()
    streamer = TransactionStreamer(store, risk_manager, event_bus)
    drift_detector = ModelDriftDetector()
    experiment_harness = ResearchExperimentHarness()

    # Active WebSockets
    active_websockets: List[WebSocket] = []

    # Models for Request Payloads
    class CommandRequest(BaseModel):
        prompt: str

    class RecoveryActionRequest(BaseModel):
        transaction_id: str
        action_type: str

    class GrowthSimulationRequest(BaseModel):
        merchant_id: str
        enable_smart_retry: bool = True
        add_emi_and_upi_intent: bool = True
        reduce_checkout_friction_pct: float = 15.0

    class CommercePurchaseRequest(BaseModel):
        product_id: Optional[str] = "prod_01"
        user_delegated_limit: float = 25000.0

    # 1. Telemetry & Metrics
    @app.get("/api/telemetry/metrics")
    def get_metrics():
        return store.get_telemetry_metrics()

    @app.get("/api/telemetry/transactions")
    def get_transactions(limit: int = 50):
        txs = store.get_recent_transactions(limit=limit)
        return [t.model_dump(mode="json") for t in txs]

    @app.post("/api/telemetry/stream/benchmark")
    def run_benchmark(count: int = 500):
        return streamer.run_throughput_benchmark(count=count)

    # 2. Natural Language Financial Command Center
    @app.post("/api/command/execute")
    def execute_command(req: CommandRequest):
        return orchestrator.run_command(req.prompt)

    # 3. 5-Layer Risk Intelligence
    @app.get("/api/risk/evaluate/{tx_id}")
    def evaluate_risk(tx_id: str):
        tx = store.get_transaction(tx_id)
        if not tx:
            raise HTTPException(status_code=404, detail="Transaction not found")
        return risk_manager.compute_fused_risk(tx)

    # 4. Payment Knowledge Graph
    @app.get("/api/graph/network/{entity_id}")
    def get_network(entity_id: str):
        return graph_engine.analyze_entity_network(entity_id)

    @app.get("/api/graph/syndicates")
    def get_syndicates():
        return graph_engine.detect_syndicates()

    # 5. Revenue Recovery & Contextual Bandit
    @app.get("/api/recovery/options/{tx_id}")
    def get_recovery_options(tx_id: str):
        tx = store.get_transaction(tx_id)
        if not tx:
            raise HTTPException(status_code=404, detail="Transaction not found")
        options = counterfactual_engine.simulate_interventions(tx)
        action, bandit_details = bandit_engine.select_action(tx)
        return {
            "transaction_id": tx_id,
            "options": [opt.model_dump(mode="json") for opt in options],
            "bandit_recommendation": {
                "action": action.value,
                "details": bandit_details
            }
        }

    @app.get("/api/recovery/bandit/stats")
    def get_bandit_stats():
        return bandit_engine.get_stats()

    @app.post("/api/recovery/execute")
    def execute_recovery(req: RecoveryActionRequest):
        return orchestrator.tools.execute_recovery_action(req.transaction_id, req.action_type)

    # 6. Merchant Digital Twin & Growth Simulator
    @app.get("/api/growth/twin/{merchant_id}")
    def get_merchant_twin(merchant_id: str):
        return growth_engine.get_or_create_twin(merchant_id).model_dump(mode="json")

    @app.post("/api/growth/simulate")
    def simulate_growth(req: GrowthSimulationRequest):
        return growth_engine.simulate_what_if(
            merchant_id=req.merchant_id,
            enable_smart_retry=req.enable_smart_retry,
            add_emi_and_upi_intent=req.add_emi_and_upi_intent,
            reduce_checkout_friction_pct=req.reduce_checkout_friction_pct
        )

    # 7. Autonomous Finance Controller
    @app.get("/api/finance/reconcile")
    def reconcile_finance():
        return finance_controller.reconcile_all_settlements()

    @app.get("/api/finance/investigate/{settlement_id}")
    def investigate_settlement(settlement_id: str):
        return finance_controller.investigate_settlement(settlement_id)

    # 8. Security Guardrails & Decision Ledger
    @app.get("/api/security/ledger")
    def get_decision_ledger(limit: int = 50):
        records = decision_ledger.get_ledger(limit=limit)
        return [r.model_dump(mode="json") for r in records]

    @app.get("/api/security/ledger/verify")
    def verify_ledger():
        return decision_ledger.verify_ledger_integrity()

    @app.post("/api/security/red-team")
    def run_red_team_attack():
        return red_team.run_security_evaluation()

    # 9. Agentic Commerce Sandbox
    @app.get("/api/commerce/catalog")
    def get_catalog():
        return commerce_simulator.SAMPLE_CATALOG

    @app.post("/api/commerce/purchase")
    def execute_agentic_purchase(req: CommercePurchaseRequest):
        return commerce_simulator.run_autonomous_purchase(
            product_id=req.product_id,
            user_delegated_limit=req.user_delegated_limit
        )

    # 10. MLOps & Research Experiments
    @app.get("/api/mlops/drift")
    def get_drift_report():
        txs = list(store.transactions.values())[-1000:]
        amounts = [t.amount for t in txs]
        risks = [t.risk_score for t in txs]
        return drift_detector.evaluate_drift(amounts, risks)

    @app.get("/api/mlops/experiments")
    def get_experiments():
        return experiment_harness.run_all_experiments()

    # 11. WebSocket Live Stream
    @app.websocket("/ws/stream")
    async def websocket_endpoint(websocket: WebSocket):
        await websocket.accept()
        active_websockets.append(websocket)
        try:
            while True:
                # Stream a live transaction and updated metrics every 2.5 seconds
                live_tx = streamer.generate_single_live_transaction()
                payload = {
                    "type": "STREAM_UPDATE",
                    "timestamp": datetime.utcnow().isoformat(),
                    "live_transaction": live_tx.model_dump(mode="json"),
                    "telemetry": store.get_telemetry_metrics()
                }
                await websocket.send_text(json.dumps(payload))
                await asyncio.sleep(2.5)
        except WebSocketDisconnect:
            if websocket in active_websockets:
                active_websockets.remove(websocket)
        except Exception:
            if websocket in active_websockets:
                active_websockets.remove(websocket)

    # Mount Static Files
    static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "static")
    if os.path.exists(static_dir):
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

    return app
