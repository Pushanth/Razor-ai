/**
 * RAZORAI — Executive AI Dashboard Client Engine
 */

let ws = null;
let currentFailedTxs = [];
let currentGraphData = null;

// Initialize on page load
window.addEventListener("DOMContentLoaded", () => {
  initWebSocket();
  loadInitialData();
});

// ==================== TAB NAVIGATION ====================
function switchTab(tabId) {
  document.querySelectorAll(".tab-content").forEach(el => el.classList.add("hidden"));
  document.querySelectorAll(".tab-btn").forEach(el => el.classList.remove("active"));

  const targetTab = document.getElementById(`tab-${tabId}`);
  const targetBtn = document.getElementById(`tab-btn-${tabId}`);

  if (targetTab) targetTab.classList.remove("hidden");
  if (targetBtn) targetBtn.classList.add("active");

  // Trigger tab-specific refresh
  if (tabId === "graph") loadGraphData();
  if (tabId === "recovery") loadRecoveryData();
  if (tabId === "growth") runMerchantSimulation();
  if (tabId === "finance") loadFinanceData();
  if (tabId === "security") loadSecurityData();
  if (tabId === "mlops") { loadDriftReport(); loadExperimentsData(); }
  if (tabId === "agents") loadAgentsData();

  lucide.createIcons();
}

function setPrompt(text) {
  const input = document.getElementById("command-input");
  if (input) {
    input.value = text;
    input.focus();
  }
}

// ==================== WEBSOCKET LIVE STREAM ====================
function initWebSocket() {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const wsUrl = `${protocol}//${window.location.host}/ws/stream`;

  try {
    ws = new WebSocket(wsUrl);
    const statusBadge = document.getElementById("stream-status");

    ws.onopen = () => {
      if (statusBadge) statusBadge.innerText = "STREAM: LIVE";
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "STREAM_UPDATE" && data.telemetry) {
          updateTelemetryHUD(data.telemetry);
        }
      } catch (err) {
        console.error("WS parse error:", err);
      }
    };

    ws.onclose = () => {
      if (statusBadge) statusBadge.innerText = "STREAM: RECONNECTING...";
      setTimeout(initWebSocket, 3000);
    };

    ws.onerror = () => {
      if (statusBadge) statusBadge.innerText = "STREAM: OFFLINE";
    };
  } catch (e) {
    console.warn("WebSocket initialization skipped:", e);
  }
}

function updateTelemetryHUD(t) {
  if (!t) return;
  if (document.getElementById("kpi-gmv")) document.getElementById("kpi-gmv").innerText = `₹${(t.total_gmv/100000).toFixed(2)}L`;
  if (document.getElementById("kpi-success-rate")) document.getElementById("kpi-success-rate").innerText = `${t.overall_success_rate}%`;
  if (document.getElementById("kpi-recovered")) document.getElementById("kpi-recovered").innerText = `₹${(t.recovered_revenue/100000).toFixed(2)}L`;
  if (document.getElementById("kpi-fraud-prevented")) document.getElementById("kpi-fraud-prevented").innerText = `₹${(t.fraud_prevented/100000).toFixed(2)}L`;
  if (document.getElementById("kpi-risk-exposure")) document.getElementById("kpi-risk-exposure").innerText = `₹${(t.risk_exposure/1000).toFixed(0)}k`;
  if (document.getElementById("kpi-discrepancies")) document.getElementById("kpi-discrepancies").innerText = `${t.settlement_discrepancy_count} Batches (₹${(t.settlement_discrepancy_amount/100000).toFixed(2)}L)`;
  if (document.getElementById("kpi-actions")) {
    const act = t.autonomous_actions_summary || {};
    document.getElementById("kpi-actions").innerText = `${act.automated || 1248} Auto / ${act.escalated || 93} Esc`;
  }
}

async function loadInitialData() {
  try {
    const res = await fetch("/api/telemetry/metrics");
    const data = await res.json();
    updateTelemetryHUD(data);
  } catch (err) {
    console.error("Failed to load initial metrics:", err);
  }
}

// ==================== TAB 1: COMMAND CENTER ====================
async function handleCommandSubmit(e) {
  e.preventDefault();
  const input = document.getElementById("command-input");
  const prompt = input.value.trim();
  if (!prompt) return;

  const badge = document.getElementById("agent-exec-badge");
  const container = document.getElementById("agent-trace-container");
  const reportBox = document.getElementById("executive-report-box");
  const submitBtn = document.getElementById("command-submit-btn");

  if (badge) {
    badge.innerText = "PLANNING & EXECUTING...";
    badge.className = "text-[10px] font-mono px-2 py-0.5 rounded bg-brand-500/20 text-brand-300 animate-pulse border border-brand-500/30";
  }
  if (submitBtn) submitBtn.disabled = true;

  container.innerHTML = `
    <div class="p-6 text-center text-slate-400 text-xs flex flex-col items-center justify-center space-y-2">
      <div class="animate-spin rounded-full h-7 w-7 border-b-2 border-brand-500"></div>
      <span>Supervisor is decomposing workflow and orchestrating Specialist Agents...</span>
    </div>
  `;

  try {
    const res = await fetch("/api/command/execute", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt })
    });
    const data = await res.json();

    if (badge) {
      badge.innerText = "WORKFLOW COMPLETE";
      badge.className = "text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30";
    }

    // Render Traces Stepper
    renderAgentTraces(data.agent_traces || []);

    // Render Executive Report
    if (reportBox) {
      reportBox.innerHTML = `
        <div class="prose prose-invert max-w-none text-xs space-y-2">
          ${formatMarkdown(data.executive_summary || "")}
        </div>
      `;
    }

    // Update Quick Metric Cards
    if (document.getElementById("exec-recovered-val")) {
      document.getElementById("exec-recovered-val").innerText = `₹${((data.metrics?.recovered_inr || 0)/100000).toFixed(2)}L`;
    }
    if (document.getElementById("exec-risk-val")) {
      document.getElementById("exec-risk-val").innerText = `${data.metrics?.high_risk_isolated || 0} Blocked`;
    }

    // Refresh Telemetry
    loadInitialData();

  } catch (err) {
    console.error("Command execution error:", err);
    container.innerHTML = `<div class="p-4 bg-rose-500/10 text-rose-400 rounded text-xs">Error executing command: ${err.message}</div>`;
    if (badge) {
      badge.innerText = "EXECUTION ERROR";
      badge.className = "text-[10px] font-mono px-2 py-0.5 rounded bg-rose-500/20 text-rose-300";
    }
  } finally {
    if (submitBtn) submitBtn.disabled = false;
    lucide.createIcons();
  }
}

function renderAgentTraces(traces) {
  const container = document.getElementById("agent-trace-container");
  if (!container) return;

  if (!traces || traces.length === 0) {
    container.innerHTML = `<p class="text-xs text-slate-500">No traces recorded.</p>`;
    return;
  }

  const agentColorMap = {
    "Supervisor": { bg: "bg-brand-500/10", border: "border-brand-500/30", text: "text-brand-400", icon: "terminal" },
    "RiskAgent": { bg: "bg-rose-500/10", border: "border-rose-500/30", text: "text-rose-400", icon: "shield-alert" },
    "RecoveryAgent": { bg: "bg-emerald-500/10", border: "border-emerald-500/30", text: "text-emerald-400", icon: "refresh-cw" },
    "GrowthAgent": { bg: "bg-amber-500/10", border: "border-amber-500/30", text: "text-amber-400", icon: "trending-up" },
    "FinanceAgent": { bg: "bg-purple-500/10", border: "border-purple-500/30", text: "text-purple-400", icon: "landmark" },
    "ActionAgent": { bg: "bg-cyan-500/10", border: "border-cyan-500/30", text: "text-cyan-400", icon: "zap" }
  };

  let html = `<div class="space-y-3">`;
  traces.forEach((t) => {
    const c = agentColorMap[t.agent_name] || { bg: "bg-slate-800", border: "border-slate-700", text: "text-slate-300", icon: "bot" };
    html += `
      <div class="p-3.5 rounded-lg ${c.bg} border ${c.border} text-xs space-y-2 transition">
        <div class="flex items-center justify-between">
          <div class="flex items-center space-x-2">
            <span class="font-bold ${c.text} flex items-center space-x-1 font-mono">
              <i data-lucide="${c.icon}" class="w-3.5 h-3.5"></i>
              <span>${t.agent_name}</span>
            </span>
            <span class="text-[10px] text-slate-500 font-mono">Step ${t.step_index}</span>
          </div>
          <span class="text-[10px] text-slate-400 font-mono">${new Date(t.timestamp).toLocaleTimeString()}</span>
        </div>
        <p class="text-slate-200 text-xs leading-relaxed">${t.thought}</p>
        ${t.tool_name ? `
          <div class="bg-slate-950/80 p-2 rounded border border-slate-800 text-[11px] font-mono space-y-1">
            <div class="text-slate-400 flex items-center space-x-1">
              <i data-lucide="wrench" class="w-3 h-3 text-brand-400"></i>
              <span>Tool Call: <span class="text-brand-300 font-semibold">${t.tool_name}()</span></span>
            </div>
            ${t.tool_output ? `<div class="text-emerald-400/90 text-[10px] truncate">Result: ${JSON.stringify(t.tool_output)}</div>` : ''}
          </div>
        ` : ''}
      </div>
    `;
  });
  html += `</div>`;
  container.innerHTML = html;
  lucide.createIcons();
}

function formatMarkdown(text) {
  if (!text) return "";
  return text
    .replace(/\*\*(.*?)\*\*/g, '<strong class="text-white font-semibold">$1</strong>')
    .replace(/^- (.*$)/gim, '<div class="flex items-start space-x-2 my-1"><span class="text-brand-400 mt-1">•</span><span>$1</span></div>')
    .replace(/\n\n/g, '<br/>');
}

// ==================== TAB 2: MULTI-AGENT OPERATIONS ROOM ====================
function loadAgentsData() {
  const container = document.getElementById("agent-cards-grid");
  if (!container) return;

  const agents = [
    {
      name: "Supervisor Agent",
      role: "Workflow Planner & Synthesizer",
      status: "ACTIVE",
      icon: "terminal",
      color: "brand",
      desc: "Decomposes high-level natural language directives into optimized multi-step execution graphs and enforces policy compliance.",
      tools: ["parse_intent", "search_failed_transactions", "synthesize_report"]
    },
    {
      name: "Risk Agent",
      role: "5-Layer Fraud & Graph Forensics",
      status: "ACTIVE",
      icon: "shield-alert",
      color: "rose",
      desc: "Investigates payload, customer velocity, merchant anomalies, and Payment Knowledge Graph syndicate rings.",
      tools: ["calculate_multi_layer_risk", "query_knowledge_graph", "detect_fraud_syndicates"]
    },
    {
      name: "Recovery Agent",
      role: "Counterfactuals & Contextual Bandit",
      status: "ACTIVE",
      icon: "refresh-cw",
      color: "emerald",
      desc: "Diagnoses payment failures and uses LinUCB Multi-Armed Bandit to dispatch risk-adjusted optimal recovery actions.",
      tools: ["predict_recovery_counterfactuals", "bandit_select_action", "update_bandit_policy"]
    },
    {
      name: "Growth Agent",
      role: "Merchant Digital Twin Simulator",
      status: "ACTIVE",
      icon: "trending-up",
      color: "amber",
      desc: "Models merchant payment funnels and runs counterfactual what-if scenarios on friction reduction and payment rail mix.",
      tools: ["get_merchant_twin", "simulate_merchant_growth"]
    },
    {
      name: "Finance Agent",
      role: "Autonomous Settlement Investigator",
      status: "ACTIVE",
      icon: "landmark",
      color: "purple",
      desc: "Reconciles settlement batches against acquirer payouts, isolating refunds, MDR fees, chargebacks, and unexplained variances.",
      tools: ["reconcile_settlements_summary", "investigate_settlement_discrepancy"]
    },
    {
      name: "Action Agent",
      role: "Policy Guardrails & Execution",
      status: "ACTIVE",
      icon: "zap",
      color: "cyan",
      desc: "Evaluates proposed actions against deterministic financial limits and executes approved actions or escalates to human review.",
      tools: ["evaluate_policy", "execute_recovery_action", "request_human_approval"]
    }
  ];

  let html = "";
  agents.forEach(a => {
    html += `
      <div class="bg-slate-900/60 border border-slate-800 hover:border-slate-700 rounded-xl p-5 space-y-4 hover-lift">
        <div class="flex items-center justify-between">
          <div class="flex items-center space-x-2.5">
            <div class="p-2 rounded-lg bg-${a.color}-500/10 border border-${a.color}-500/20 text-${a.color}-400">
              <i data-lucide="${a.icon}" class="w-4 h-4"></i>
            </div>
            <div>
              <h4 class="text-sm font-semibold text-white">${a.name}</h4>
              <span class="text-[11px] text-slate-400">${a.role}</span>
            </div>
          </div>
          <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-semibold">${a.status}</span>
        </div>
        <p class="text-xs text-slate-300 leading-relaxed">${a.desc}</p>
        <div class="pt-3 border-t border-slate-800/80 space-y-1.5">
          <span class="text-[10px] uppercase font-mono text-slate-400 tracking-wider">Available Tools:</span>
          <div class="flex flex-wrap gap-1">
            ${a.tools.map(t => `<span class="px-2 py-0.5 bg-slate-950 text-slate-400 rounded text-[10px] font-mono border border-slate-800">${t}()</span>`).join("")}
          </div>
        </div>
      </div>
    `;
  });

  container.innerHTML = html;
  lucide.createIcons();
}

// ==================== TAB 3: KNOWLEDGE GRAPH ====================
async function loadGraphData() {
  try {
    const res = await fetch("/api/graph/syndicates");
    const syndicates = await res.json();
    renderSyndicatesList(syndicates);

    // Draw visual graph on canvas
    drawKnowledgeGraphCanvas();
  } catch (err) {
    console.error("Failed to load graph data:", err);
  }
}

function renderSyndicatesList(syndicates) {
  const container = document.getElementById("syndicates-list");
  if (!container) return;

  if (!syndicates || syndicates.length === 0) {
    container.innerHTML = `<p class="text-xs text-slate-500">No syndicate clusters detected.</p>`;
    return;
  }

  let html = "";
  syndicates.forEach(s => {
    html += `
      <div class="p-3.5 bg-slate-950/80 border border-rose-500/30 rounded-lg space-y-2 text-xs">
        <div class="flex items-center justify-between">
          <span class="font-mono font-bold text-rose-400 flex items-center space-x-1">
            <i data-lucide="alert-triangle" class="w-3.5 h-3.5"></i>
            <span>${s.device_id}</span>
          </span>
          <span class="text-[10px] px-1.5 py-0.5 rounded bg-rose-500/20 text-rose-300 font-mono font-bold">${s.risk_tier}</span>
        </div>
        <div class="text-[11px] text-slate-300">
          <div>OS: <span class="font-mono text-slate-400">${s.os}</span></div>
          <div>Connected Customers: <span class="font-mono text-amber-300 font-bold">${s.connected_customer_count} accounts</span></div>
          <div>Confidence: <span class="font-mono text-emerald-400">${(s.confidence*100).toFixed(1)}%</span></div>
        </div>
        <div class="text-[10px] text-slate-500 font-mono">Customer IDs: ${s.customer_ids.slice(0, 4).join(", ")}...</div>
      </div>
    `;
  });
  container.innerHTML = html;
  lucide.createIcons();
}

function drawKnowledgeGraphCanvas() {
  const canvas = document.getElementById("kg-canvas");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const rect = canvas.getBoundingClientRect();
  canvas.width = rect.width;
  canvas.height = rect.height;

  ctx.clearRect(0, 0, canvas.width, canvas.height);

  const cx = canvas.width / 2;
  const cy = canvas.height / 2;

  // Draw central syndicate device node
  const nodes = [
    { x: cx, y: cy, r: 18, label: "dev_syndicate_01", color: "#f43f5e", type: "DEVICE (CRITICAL)" },
    { x: cx - 180, y: cy - 100, r: 12, label: "cust_000001", color: "#3b82f6", type: "CUSTOMER" },
    { x: cx - 140, y: cy + 120, r: 12, label: "cust_000002", color: "#3b82f6", type: "CUSTOMER" },
    { x: cx + 160, y: cy - 110, r: 12, label: "cust_000003", color: "#3b82f6", type: "CUSTOMER" },
    { x: cx + 190, y: cy + 90, r: 12, label: "cust_000004", color: "#3b82f6", type: "CUSTOMER" },
    { x: cx, y: cy - 180, r: 14, label: "card_stolen_01", color: "#f59e0b", type: "CARD" },
    { x: cx - 220, y: cy + 20, r: 16, label: "Apex Cloud", color: "#10b981", type: "MERCHANT" },
    { x: cx + 230, y: cy + 20, r: 16, label: "QuickKart", color: "#10b981", type: "MERCHANT" }
  ];

  // Draw Edges
  ctx.lineWidth = 1.5;
  nodes.slice(1, 5).forEach(c => {
    ctx.strokeStyle = "rgba(244, 63, 94, 0.4)";
    ctx.beginPath();
    ctx.moveTo(nodes[0].x, nodes[0].y);
    ctx.lineTo(c.x, c.y);
    ctx.stroke();

    // Edge to merchant
    ctx.strokeStyle = "rgba(51, 149, 255, 0.2)";
    ctx.beginPath();
    ctx.moveTo(c.x, c.y);
    ctx.lineTo(nodes[6].x, nodes[6].y);
    ctx.stroke();
  });

  // Edge from card to syndicate
  ctx.strokeStyle = "rgba(245, 158, 11, 0.5)";
  ctx.beginPath();
  ctx.moveTo(nodes[0].x, nodes[0].y);
  ctx.lineTo(nodes[5].x, nodes[5].y);
  ctx.stroke();

  // Draw Nodes
  nodes.forEach(n => {
    ctx.beginPath();
    ctx.arc(n.x, n.y, n.r, 0, 2 * Math.PI);
    ctx.fillStyle = n.color;
    ctx.fill();
    ctx.lineWidth = 2;
    ctx.strokeStyle = "#ffffff";
    ctx.stroke();

    // Label
    ctx.fillStyle = "#cbd5e1";
    ctx.font = "10px JetBrains Mono";
    ctx.textAlign = "center";
    ctx.fillText(n.label, n.x, n.y + n.r + 14);
  });
}

// ==================== TAB 4: RECOVERY & BANDIT ====================
async function loadRecoveryData() {
  try {
    const res = await fetch("/api/telemetry/transactions?limit=100");
    const txs = await res.json();
    currentFailedTxs = txs.filter(t => t.status === "FAILED");
    renderFailedTxTable(currentFailedTxs);
  } catch (err) {
    console.error("Failed to load recovery txs:", err);
  }
}

function renderFailedTxTable(txs) {
  const tbody = document.getElementById("failed-tx-table-body");
  if (!tbody) return;

  if (!txs || txs.length === 0) {
    tbody.innerHTML = `<tr><td colspan="6" class="p-4 text-center text-slate-500">No failed transactions.</td></tr>`;
    return;
  }

  let html = "";
  txs.slice(0, 15).forEach((t) => {
    html += `
      <tr class="hover:bg-slate-800/50 cursor-pointer transition" onclick="selectFailedTxForRecovery('${t.id}')">
        <td class="p-2.5 text-brand-300 font-bold">${t.id}</td>
        <td class="p-2.5 text-white font-semibold">₹${t.amount.toLocaleString()}</td>
        <td class="p-2.5 text-slate-300">${t.payment_method}</td>
        <td class="p-2.5 text-rose-400 font-sans text-[11px]">${t.failure_reason}</td>
        <td class="p-2.5 text-amber-400">${t.risk_score}</td>
        <td class="p-2.5">
          <button class="px-2 py-0.5 bg-brand-500/20 hover:bg-brand-500/30 text-brand-300 border border-brand-500/30 rounded text-[10px]">
            Simulate
          </button>
        </td>
      </tr>
    `;
  });
  tbody.innerHTML = html;
}

async function selectFailedTxForRecovery(txId) {
  const container = document.getElementById("counterfactual-details-box");
  if (!container) return;

  container.innerHTML = `<div class="p-8 text-center text-slate-400 text-xs">Simulating counterfactual intervention options...</div>`;

  try {
    const res = await fetch(`/api/recovery/options/${txId}`);
    const data = await res.json();
    renderCounterfactualOptions(data);
  } catch (err) {
    container.innerHTML = `<div class="p-4 bg-rose-500/10 text-rose-400 rounded text-xs">Error: ${err.message}</div>`;
  }
}

function renderCounterfactualOptions(data) {
  const container = document.getElementById("counterfactual-details-box");
  if (!container) return;

  const bandit = data.bandit_recommendation || {};
  let html = `
    <div class="space-y-4">
      <div class="p-3 bg-brand-950/40 border border-brand-500/30 rounded-lg space-y-1">
        <div class="flex items-center justify-between text-xs">
          <span class="font-bold text-white font-mono">Target: ${data.transaction_id}</span>
          <span class="text-emerald-400 font-mono text-[10px] font-bold">BANDIT CHOICE: ${bandit.action || 'SMART_RETRY_15M'}</span>
        </div>
        <p class="text-[11px] text-slate-400">Contextual LinUCB evaluates expected recovery minus friction and risk exposure.</p>
      </div>

      <div class="space-y-2 max-h-[300px] overflow-y-auto pr-1">
  `;

  (data.options || []).forEach(opt => {
    const isTop = opt.is_recommended;
    html += `
      <div class="p-3 rounded-lg border ${isTop ? 'bg-emerald-950/20 border-emerald-500/40' : 'bg-slate-950 border-slate-800'} space-y-1 text-xs">
        <div class="flex items-center justify-between">
          <span class="font-mono font-bold ${isTop ? 'text-emerald-300' : 'text-slate-300'}">${opt.action}</span>
          <span class="font-mono text-[11px] ${isTop ? 'text-emerald-400 font-bold' : 'text-slate-400'}">Risk-Adjusted EV: ₹${opt.risk_adjusted_ev.toFixed(2)}</span>
        </div>
        <p class="text-[11px] text-slate-400">${opt.description}</p>
        <div class="flex items-center space-x-3 text-[10px] text-slate-500 font-mono pt-1">
          <span>Prob: ${(opt.expected_recovery_prob*100).toFixed(0)}%</span>
          <span>Cost: ₹${opt.cost}</span>
          <span>Friction: ₹${opt.friction_penalty}</span>
        </div>
      </div>
    `;
  });

  html += `
      </div>

      <button onclick="dispatchRecoveryAction('${data.transaction_id}', '${bandit.action || 'SMART_RETRY_15M'}')" class="w-full py-2.5 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white rounded-lg text-xs font-semibold shadow-lg shadow-emerald-500/20 transition flex items-center justify-center space-x-1.5">
        <i data-lucide="check" class="w-3.5 h-3.5"></i>
        <span>Execute Recommended Action (${bandit.action || 'SMART_RETRY_15M'})</span>
      </button>
    </div>
  `;

  container.innerHTML = html;
  lucide.createIcons();
}

async function dispatchRecoveryAction(txId, actionType) {
  try {
    const res = await fetch("/api/recovery/execute", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ transaction_id: txId, action_type: actionType })
    });
    const result = await res.json();
    alert(`Action Status: ${result.status}\nDecision ID: ${result.decision_id || 'N/A'}\nRevenue Recovered: ₹${result.revenue_recovered || 0}`);
    loadRecoveryData();
    loadInitialData();
  } catch (err) {
    alert("Error executing recovery: " + err.message);
  }
}

// ==================== TAB 5: MERCHANT DIGITAL TWIN ====================
async function runMerchantSimulation() {
  const select = document.getElementById("merchant-twin-select");
  const merchId = select ? select.value : "merch_0001";
  const smartRetry = document.getElementById("sim-smart-retry")?.checked ?? true;
  const emiRails = document.getElementById("sim-emi-rails")?.checked ?? true;
  const friction = parseFloat(document.getElementById("sim-friction-slider")?.value || 15);

  const container = document.getElementById("twin-simulation-results");
  if (!container) return;

  try {
    const res = await fetch("/api/growth/simulate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        merchant_id: merchId,
        enable_smart_retry: smartRetry,
        add_emi_and_upi_intent: emiRails,
        reduce_checkout_friction_pct: friction
      })
    });
    const sim = await res.json();
    renderSimulationResults(sim);
  } catch (err) {
    container.innerHTML = `<div class="p-4 bg-rose-500/10 text-rose-400 rounded text-xs">Simulation Error: ${err.message}</div>`;
  }
}

function renderSimulationResults(sim) {
  const container = document.getElementById("twin-simulation-results");
  if (!container) return;

  let html = `
    <div class="space-y-4">
      <div class="grid grid-cols-2 gap-3 text-xs font-mono">
        <div class="p-3 bg-slate-900 rounded border border-slate-800">
          <span class="text-[10px] text-slate-400 block">Baseline Monthly GMV:</span>
          <span class="text-base font-bold text-white">₹${(sim.baseline.monthly_gmv/100000).toFixed(2)} Lakhs</span>
          <span class="text-[10px] text-slate-400 block mt-1">Success Rate: ${sim.baseline.success_rate}%</span>
        </div>
        <div class="p-3 bg-emerald-950/40 rounded border border-emerald-500/30">
          <span class="text-[10px] text-emerald-400 block">Projected Monthly GMV:</span>
          <span class="text-base font-bold text-emerald-300">₹${(sim.projected.monthly_gmv/100000).toFixed(2)} Lakhs</span>
          <span class="text-[10px] text-emerald-400 block mt-1">Total Uplift: +₹${(sim.projected.total_uplift_inr/100000).toFixed(2)}L (+${sim.projected.total_uplift_percentage}%)</span>
        </div>
      </div>

      <div class="space-y-2 pt-2 border-t border-slate-800">
        <span class="text-[10px] uppercase font-mono text-slate-400 tracking-wider">Growth Levers Contribution:</span>
        ${sim.breakdown.map(b => `
          <div class="flex items-center justify-between p-2 rounded bg-slate-900 text-xs">
            <div>
              <span class="font-medium text-white block">${b.lever}</span>
              <span class="text-[10px] text-slate-400">${b.description}</span>
            </div>
            <div class="text-right font-mono">
              <span class="text-emerald-400 font-bold">+₹${(b.gmv_gain_inr/100000).toFixed(2)}L</span>
              <span class="text-[10px] text-slate-400 block">${b.percentage_contribution}%</span>
            </div>
          </div>
        `).join("")}
      </div>

      <div class="p-3 bg-slate-900/60 rounded border border-slate-800 text-xs space-y-1.5">
        <span class="text-brand-300 font-semibold flex items-center space-x-1">
          <i data-lucide="lightbulb" class="w-3.5 h-3.5"></i>
          <span>Autonomous AI Recommendations:</span>
        </span>
        <ul class="text-[11px] text-slate-300 list-disc list-inside space-y-1">
          ${sim.actionable_recommendations.map(r => `<li>${r}</li>`).join("")}
        </ul>
      </div>
    </div>
  `;
  container.innerHTML = html;
  lucide.createIcons();
}

// ==================== TAB 6: FINANCE RECONCILER ====================
async function loadFinanceData() {
  try {
    const res = await fetch("/api/finance/reconcile");
    const recon = await res.json();
    renderSettlementsList(recon.discrepancies || []);
  } catch (err) {
    console.error("Failed to load finance data:", err);
  }
}

function renderSettlementsList(batches) {
  const container = document.getElementById("settlements-list-container");
  if (!container) return;

  if (!batches || batches.length === 0) {
    container.innerHTML = `<p class="text-xs text-slate-500">All settlement payout batches balanced.</p>`;
    return;
  }

  let html = "";
  batches.forEach(b => {
    html += `
      <div onclick="inspectSettlement('${b.settlement_id}')" class="p-3 bg-slate-950 hover:bg-slate-900 border border-slate-800 hover:border-slate-700 rounded-lg cursor-pointer transition text-xs space-y-1 font-mono">
        <div class="flex items-center justify-between">
          <span class="font-bold text-brand-300">${b.settlement_id}</span>
          <span class="text-[10px] px-1.5 py-0.5 rounded bg-rose-500/20 text-rose-300 font-bold">₹${b.variance.toLocaleString()} Variance</span>
        </div>
        <div class="text-[11px] text-slate-400">Merchant: ${b.merchant_id} | Date: ${b.date}</div>
        <div class="text-[10px] text-slate-500">Expected: ₹${b.expected_payout.toLocaleString()} vs Actual: ₹${b.actual_payout.toLocaleString()}</div>
      </div>
    `;
  });
  container.innerHTML = html;
}

async function inspectSettlement(settleId) {
  const container = document.getElementById("finance-waterfall-container");
  if (!container) return;

  container.innerHTML = `<div class="p-8 text-center text-slate-400 text-xs">Generating forensic settlement deconstruction waterfall...</div>`;

  try {
    const res = await fetch(`/api/finance/investigate/${settleId}`);
    const inv = await res.json();
    renderFinanceWaterfall(inv);
  } catch (err) {
    container.innerHTML = `<div class="p-4 bg-rose-500/10 text-rose-400 rounded text-xs">Error: ${err.message}</div>`;
  }
}

function renderFinanceWaterfall(inv) {
  const container = document.getElementById("finance-waterfall-container");
  if (!container) return;

  let html = `
    <div class="space-y-4 text-xs font-mono">
      <div class="p-3 bg-rose-950/20 border border-rose-500/30 rounded-lg space-y-1">
        <div class="flex items-center justify-between">
          <span class="font-bold text-white">Case ID: ${inv.case_id}</span>
          <span class="text-rose-400 font-bold">Unexplained Variance: ₹${inv.unexplained_variance.toLocaleString()}</span>
        </div>
        <p class="text-[11px] text-slate-400 font-sans">Merchant: ${inv.merchant_name} | Settlement ID: ${inv.settlement_id}</p>
      </div>

      <div class="space-y-1.5">
        <span class="text-[10px] uppercase text-slate-400 tracking-wider">Settlement Waterfall Breakdown:</span>
        <div class="space-y-1">
          ${inv.waterfall.map(w => {
            const color = w.type === 'positive' ? 'text-emerald-400' : w.type === 'negative' ? 'text-rose-400' : w.type === 'variance' ? 'text-amber-400 font-bold bg-amber-500/10 p-1 rounded' : 'text-white font-bold';
            return `
              <div class="flex items-center justify-between p-2 bg-slate-950 rounded border border-slate-800/80">
                <span class="text-slate-300">${w.step}</span>
                <span class="${color}">${w.formatted}</span>
              </div>
            `;
          }).join("")}
        </div>
      </div>

      <div class="p-3 bg-slate-950 rounded border border-slate-800 text-[11px] space-y-1 font-sans">
        <span class="font-bold text-slate-300">Recommended Action:</span>
        <p class="text-slate-400">${inv.recommended_action}</p>
      </div>
    </div>
  `;
  container.innerHTML = html;
}

// ==================== TAB 7: DECISION LEDGER & RED TEAM ====================
async function loadSecurityData() {
  try {
    const res = await fetch("/api/security/ledger?limit=30");
    const records = await res.json();
    renderLedgerTable(records);
  } catch (err) {
    console.error("Failed to load ledger:", err);
  }
}

function renderLedgerTable(records) {
  const tbody = document.getElementById("ledger-table-body");
  if (!tbody) return;

  if (!records || records.length === 0) {
    tbody.innerHTML = `<tr><td colspan="6" class="p-4 text-center text-slate-500">No records found.</td></tr>`;
    return;
  }

  let html = "";
  records.forEach(r => {
    const policyClass = r.policy_check === 'AUTO_APPROVED' ? 'text-emerald-400' : r.policy_check === 'ESCALATED_TO_HUMAN' ? 'text-amber-400' : 'text-rose-400';
    html += `
      <tr class="hover:bg-slate-800/50 transition">
        <td class="p-2 text-brand-300 font-bold">${r.decision_id}</td>
        <td class="p-2 text-slate-300">${r.agent}</td>
        <td class="p-2 text-slate-200 text-[10px] font-sans truncate max-w-[140px]">${r.action_taken}</td>
        <td class="p-2 font-bold ${policyClass}">${r.policy_check}</td>
        <td class="p-2 text-emerald-300">₹${r.revenue_impact.toLocaleString()}</td>
        <td class="p-2 text-slate-500 font-mono text-[9px]">${r.signature_hash.substring(0, 16)}...</td>
      </tr>
    `;
  });
  tbody.innerHTML = html;
}

async function verifyLedgerIntegrity() {
  try {
    const res = await fetch("/api/security/ledger/verify");
    const data = await res.json();
    alert(`Ledger Integrity Status: ${data.status}\nRecords Verified: ${data.record_count}\nCompromised: ${data.is_compromised}\nLatest Hash: ${data.latest_signature?.substring(0, 24)}...`);
  } catch (err) {
    alert("Verification Error: " + err.message);
  }
}

async function runRedTeamEvaluation() {
  const container = document.getElementById("red-team-results-container");
  if (!container) return;

  container.innerHTML = `<div class="p-6 text-center text-slate-400 text-xs">Launching adversarial prompt injections and limit bypass payloads against Policy Engine...</div>`;

  try {
    const res = await fetch("/api/security/red-team", { method: "POST" });
    const data = await res.json();

    let html = `
      <div class="p-3 bg-emerald-950/30 border border-emerald-500/30 rounded-lg text-xs flex items-center justify-between font-mono">
        <span>DEFENSE PASS RATE: <strong class="text-emerald-400">${data.defense_success_rate}%</strong></span>
        <span class="px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300">${data.safety_verdict}</span>
      </div>
      <div class="space-y-2 pt-2">
    `;

    (data.test_runs || []).forEach(t => {
      html += `
        <div class="p-3 bg-slate-950 rounded border border-slate-800 text-xs space-y-1">
          <div class="flex items-center justify-between">
            <span class="font-bold text-white font-mono">${t.attack_id}: ${t.attack_name}</span>
            <span class="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 font-mono font-bold">${t.status}</span>
          </div>
          <p class="text-[11px] text-slate-400 italic">"${t.adversarial_prompt}"</p>
          <div class="text-[10px] text-emerald-400 font-mono">Defense: ${t.defense_reason}</div>
        </div>
      `;
    });

    html += `</div>`;
    container.innerHTML = html;
  } catch (err) {
    container.innerHTML = `<div class="p-4 bg-rose-500/10 text-rose-400 rounded text-xs">Error: ${err.message}</div>`;
  }
}

// ==================== TAB 8: AGENTIC COMMERCE ====================
async function executeAgenticPurchase() {
  const prodSelect = document.getElementById("commerce-product-select");
  const limitInput = document.getElementById("commerce-user-limit");
  const container = document.getElementById("commerce-stepper-list");

  if (!container) return;

  const productId = prodSelect ? prodSelect.value : "prod_01";
  const userLimit = parseFloat(limitInput ? limitInput.value : 25000);

  container.innerHTML = `<div class="p-6 text-center text-slate-400 text-xs">AI Buyer Agent executing autonomous 7-stage checkout flow...</div>`;

  try {
    const res = await fetch("/api/commerce/purchase", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ product_id: productId, user_delegated_limit: userLimit })
    });
    const data = await res.json();
    renderCommerceStepper(data);
    loadInitialData();
  } catch (err) {
    container.innerHTML = `<div class="p-4 bg-rose-500/10 text-rose-400 rounded text-xs">Error: ${err.message}</div>`;
  }
}

function renderCommerceStepper(data) {
  const container = document.getElementById("commerce-stepper-list");
  if (!container) return;

  let html = `
    <div class="space-y-3">
      <div class="p-3 bg-brand-950/30 border border-brand-500/30 rounded-lg flex items-center justify-between text-xs">
        <span class="font-bold text-white font-mono">Order ID: ${data.order_id}</span>
        <span class="text-emerald-400 font-mono font-bold">STATUS: ${data.status}</span>
      </div>
      <div class="space-y-2.5">
  `;

  (data.stages || []).forEach((s) => {
    const isSuccess = s.status === 'SUCCESS' || s.status === 'COMPLETED' || s.status === 'APPROVED' || s.status === 'RECORDED';
    const badgeColor = isSuccess ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' : 'bg-amber-500/10 text-amber-400 border-amber-500/20';

    html += `
      <div class="p-3 rounded bg-slate-950 border border-slate-800 text-xs space-y-1">
        <div class="flex items-center justify-between">
          <span class="font-bold text-slate-200 font-mono">${s.stage}</span>
          <span class="text-[10px] px-1.5 py-0.5 rounded border ${badgeColor} font-mono">${s.status}</span>
        </div>
        <p class="text-[11px] text-slate-400">${s.detail}</p>
      </div>
    `;
  });

  html += `</div></div>`;
  container.innerHTML = html;
}

// ==================== TAB 9: RESEARCH & MLOPS ====================
async function loadDriftReport() {
  const container = document.getElementById("drift-report-container");
  if (!container) return;

  try {
    const res = await fetch("/api/mlops/drift");
    const d = await res.json();

    container.innerHTML = `
      <div class="p-3.5 bg-slate-950 rounded-lg border border-slate-800 space-y-1.5 font-mono">
        <span class="text-[10px] text-slate-400 block uppercase">Transaction Amount Drift (PSI)</span>
        <div class="text-base font-bold ${d.amount_feature_drift.drift_detected ? 'text-rose-400' : 'text-emerald-400'}">${d.amount_feature_drift.psi_score} (${d.amount_feature_drift.status})</div>
        <div class="text-[10px] text-slate-500">KS p-value: ${d.amount_feature_drift.p_value}</div>
      </div>

      <div class="p-3.5 bg-slate-950 rounded-lg border border-slate-800 space-y-1.5 font-mono">
        <span class="text-[10px] text-slate-400 block uppercase">Risk Score Prediction Drift (PSI)</span>
        <div class="text-base font-bold ${d.risk_prediction_drift.drift_detected ? 'text-rose-400' : 'text-emerald-400'}">${d.risk_prediction_drift.psi_score} (${d.risk_prediction_drift.status})</div>
        <div class="text-[10px] text-slate-500">KS p-value: ${d.risk_prediction_drift.p_value}</div>
      </div>

      <div class="p-3.5 bg-slate-950 rounded-lg border border-slate-800 space-y-1.5 font-mono">
        <span class="text-[10px] text-slate-400 block uppercase">Automated Pipeline Action</span>
        <div class="text-xs font-bold text-white">${d.overall_model_health}</div>
        <div class="text-[10px] text-slate-400 font-sans">${d.automated_action}</div>
      </div>
    `;
  } catch (err) {
    console.error("Failed to load drift:", err);
  }
}

async function loadExperimentsData() {
  const container = document.getElementById("experiments-list-container");
  if (!container) return;

  try {
    const res = await fetch("/api/mlops/experiments");
    const experiments = await res.json();

    let html = "";
    experiments.forEach(exp => {
      html += `
        <div class="p-4 bg-slate-950 rounded-lg border border-slate-800 space-y-3 text-xs">
          <div class="flex items-center justify-between">
            <h4 class="font-bold text-white text-sm flex items-center space-x-2">
              <span class="px-2 py-0.5 rounded bg-brand-500/20 text-brand-300 font-mono text-xs">${exp.experiment_id}</span>
              <span>${exp.title}</span>
            </h4>
          </div>
          <p class="text-[11px] text-slate-400 italic">Hypothesis: ${exp.hypothesis}</p>

          <div class="overflow-x-auto">
            <table class="w-full text-left font-mono text-[11px]">
              <thead class="text-slate-500 border-b border-slate-800 text-[10px]">
                <tr>
                  <th class="p-1.5">Metric</th>
                  <th class="p-1.5">Baseline</th>
                  <th class="p-1.5">Proposed (RAZORAI)</th>
                  <th class="p-1.5 text-emerald-400">Uplift</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-900">
                ${exp.metrics.map(m => {
                  const keys = Object.keys(m);
                  const baseKey = keys.find(k => k.includes("baseline")) || keys[1];
                  const propKey = keys.find(k => k.includes("proposed")) || keys[2];
                  return `
                    <tr>
                      <td class="p-1.5 text-slate-300">${m.metric}</td>
                      <td class="p-1.5 text-slate-400">${m[baseKey]}</td>
                      <td class="p-1.5 text-brand-300 font-bold">${m[propKey]}</td>
                      <td class="p-1.5 text-emerald-400 font-bold">${m.uplift || ''}</td>
                    </tr>
                  `;
                }).join("")}
              </tbody>
            </table>
          </div>

          <div class="text-[11px] text-slate-400 bg-slate-900/60 p-2.5 rounded border border-slate-800 font-sans">
            <strong class="text-white">Conclusion:</strong> ${exp.conclusion}
          </div>
        </div>
      `;
    });

    container.innerHTML = html;
  } catch (err) {
    console.error("Failed to load experiments:", err);
  }
}

async function runStreamingBenchmark() {
  alert("Running 1,000 Tx/s streaming inference benchmark...");
  try {
    const res = await fetch("/api/telemetry/stream/benchmark?count=500", { method: "POST" });
    const data = await res.json();
    alert(`Benchmark Complete!\n\nThroughput: ${data.throughput_tps} TPS\nAvg Latency: ${data.avg_latency_ms} ms\nP95 Latency: ${data.p95_latency_ms} ms\nMeets <100ms SLA: ${data.meets_100ms_sla ? 'YES (Passed)' : 'NO'}`);
    loadInitialData();
  } catch (err) {
    alert("Benchmark error: " + err.message);
  }
}
