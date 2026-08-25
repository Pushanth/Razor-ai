import sys
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import uvicorn
from razorai.api.app import create_app

app = create_app()

if __name__ == "__main__":
    print("================================================================================")
    print(">>> Starting RAZORAI: Autonomous Financial Intelligence & Agentic Commerce Engine")
    print(">>> Payment Foundation Model (Vulcan Research Prototype) Initialized")
    print(">>> 5-Layer Risk Intelligence & Payment Knowledge Graph Loaded")
    print(">>> Counterfactual Recovery & Contextual Multi-Armed Bandit Active")
    print(">>> Multi-Agent Operating System (Supervisor + 5 Specialists) Ready")
    print(">>> Cryptographic AI Decision Ledger Online")
    print(">>> FastAPI Gateway listening on http://localhost:8000")
    print("================================================================================")
    uvicorn.run(app, host="127.0.0.1", port=8000)
