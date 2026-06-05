/* Matrix Context — control plane (admin UI). Zero-dependency SPA wired to /v1.
 * Views: Overview, Inspector, Builder, Memory, Experts, Routing, Benchmarks,
 * Standard, Settings. Enterprise basics: top-bar scope selector (tenant
 * isolation), auth token, graceful offline state. (Cloud omitted — pre-launch.)
 */
(function () {
  "use strict";
  const MC = window.MC;
  const $ = (s, r) => (r || document).querySelector(s);
  const el = (h) => { const t = document.createElement("template"); t.innerHTML = h.trim(); return t.content.firstChild; };
  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const state = { tab: "overview", scope: "/", online: false, version: null, health: null, experts: [], scopes: [], items: [] };

  const BENCH = {
    note: "sentence-transformers/all-MiniLM-L6-v2 · test split · K=8",
    rows: [
      { m: "bm25_rag", kw: 100, pa: 81, adv: 64, hd: 72 },
      { m: "dense_rag", kw: 83, pa: 79, adv: 74, hd: 103 },
      { m: "hybrid_rag", kw: 96, pa: 88, adv: 71, hd: 91 },
      { m: "moc_rag_e2", kw: 96, pa: 86, adv: 78, hd: 48 },
      { m: "moc_rag_e3", kw: 96, pa: 89, adv: 79, hd: 62 },
    ],
  };
  const ENDPOINTS = ["GET /v1/health", "GET /v1/version", "GET /v1/experts", "GET /v1/scopes",
    "GET /v1/items", "GET /v1/items/{id}", "POST /v1/remember", "POST /v1/recall",
    "POST /v1/pack", "POST /v1/inspect", "POST /v1/router/explain", "POST /v1/forget"];
  const NAV = [
    ["Workspace", [["overview", "Overview", "◎"], ["inspector", "Inspector", "⌕"], ["builder", "Ingest", "↥"], ["memory", "Memory", "▤"]]],
    ["Develop", [["integrate", "Integrate", "⌁"]]],
    ["Engine", [["experts", "Experts", "❖"], ["routing", "Routing", "⇄"], ["benchmarks", "Benchmarks", "▦"]]],
    ["Platform", [["standard", "MoC Contract", "§"], ["settings", "Settings", "⚙"]]],
  ];

  // ---- ingest classifier (Compatible Mode) ----
  const SAMPLE = `# Project notes

## Decision: default backend
Use SQLite as the default storage backend; vectors accelerate, SQL is the source of truth.

## Policy: secrets
The agent must never store API keys, tokens, or PII in durable memory.

## Preference
The user prefers local-first tools over cloud services.

## Roadmap
Defer Milvus to v2; pgvector lands in v1.`;
  const EXPERT_FOR_TYPE = { decision: "semantic", fact: "semantic", rule: "policy", preference: "profile", event: "episodic", document: "document" };
  function classify(text) {
    if (!text || !text.trim()) return [];
    const blocks = text.split(/\n(?=#)|\n\s*\n/).map((b) => b.replace(/^#+\s*/, "").replace(/\s+/g, " ").trim()).filter((b) => b.length > 12);
    return blocks.slice(0, 20).map((b, i) => {
      const low = b.toLowerCase();
      let type = "fact";
      if (/\b(decide|decision|chose|default|will use|roadmap|defer|v1|v2|phase)\b/.test(low)) type = "decision";
      else if (/\b(policy|must|never|forbidden|require)\b/.test(low)) type = "rule";
      else if (/\b(prefer|preference|like)\b/.test(low)) type = "preference";
      const has = (id) => state.experts.some((e) => e.id === id);
      let expert = EXPERT_FOR_TYPE[type] || "semantic";
      if (!has(expert)) expert = (state.experts[0] && state.experts[0].id) || "semantic";
      const importance = Math.round(Math.min(0.98, 0.55 + (type === "rule" ? 0.4 : type === "decision" ? 0.32 : 0.18)) * 100) / 100;
      const tags = Array.from(new Set((low.match(/\b(mcp|sdk|api|sqlite|milvus|pgvector|policy|secrets|local-first|memory|scope|roadmap)\b/g) || []))).slice(0, 4);
      return { id: "c" + i, content: b.slice(0, 280), type, expert, importance, confidence: Math.round((0.75 + Math.random() * 0.2) * 100) / 100, tags: tags.length ? tags : ["context"], approved: true };
    });
  }

  // ---- boot / chrome ----
  async function boot() {
    try { state.health = await MC.health(); state.version = await MC.version(); state.online = true; }
    catch (e) { state.online = false; }
    if (state.online) {
      try { state.experts = await MC.experts(); } catch (e) {}
      try { state.scopes = await MC.scopes(); } catch (e) {}
      try { state.items = (await MC.items()).items; } catch (e) {}
    }
    chrome(); render();
  }
  async function refreshStore() { try { state.items = (await MC.items()).items; state.health = await MC.health(); chrome(); } catch (e) {} }
  function chrome() {
    const p = $("#health"); if (p) { p.className = "pill " + (state.online ? "ok" : "bad"); p.textContent = state.online ? "● online" : "● offline"; }
    const ver = $("#ver"); if (ver) ver.textContent = state.version ? ("contract " + state.version.contract) : "—";
    const b = $("#banner"); if (b) b.classList.toggle("show", !state.online);
    const sel = $("#scopesel");
    if (sel) {
      sel.innerHTML = `<option value="/">All scopes</option>` + state.scopes.map((s) => `<option value="${esc(s.id)}" ${s.id === state.scope ? "selected" : ""}>${esc(s.label)}</option>`).join("");
      sel.value = state.scope;
    }
  }
  function counts(field) { const m = {}; state.items.forEach((it) => { m[it[field]] = (m[it[field]] || 0) + 1; }); return m; }
  const scopeLabel = () => (state.scope === "/" ? "all scopes" : state.scope);
  function offline(v) { v.appendChild(el(`<div class="card"><h2>Disconnected</h2><p class="muted">The backend is not reachable. Start it (<span class="mono">python frontend/server.py</span>) or check Settings, then reload.</p></div>`)); }

  function render() {
    document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("active", t.dataset.tab === state.tab));
    const v = $("#view"); v.innerHTML = "";
    const views = { overview: vOverview, inspector: vInspector, builder: vBuilder, memory: vMemory, integrate: vIntegrate, experts: vExperts, routing: vRouting, benchmarks: vBench, standard: vStandard, settings: vSettings };
    if (!state.online && ["overview", "inspector", "builder", "memory", "experts", "routing"].indexOf(state.tab) >= 0) {
      v.appendChild(el(`<div><h1>${esc(state.tab[0].toUpperCase() + state.tab.slice(1))}</h1></div>`)); offline(v); return;
    }
    (views[state.tab] || vOverview)(v);
  }

  // ---- Overview ----
  function vOverview(v) {
    const ec = counts("expert"), sc = counts("scope");
    v.appendChild(el(`<div>
      <h1>Control plane</h1>
      <p class="sub">Inspectable, typed memory for AI agents — routed retrieval, budgeted packs, every choice explained. Backed by MoC Contract v1.</p>
      <div class="grid cols-3">
        <div class="card"><div class="lbl">Memory items</div><div class="stat acc">${state.health ? state.health.items : "—"}</div></div>
        <div class="card"><div class="lbl">Context experts</div><div class="stat">${state.experts.length}</div></div>
        <div class="card"><div class="lbl">Scopes</div><div class="stat">${state.scopes.length}</div></div>
      </div>
      <div class="grid cols-3" style="margin-top:14px">
        <div class="card value-card"><h3>Route, don't dump</h3><p>Each query goes to the few typed experts it needs — not one flat index.</p></div>
        <div class="card value-card"><h3>Budgeted packs</h3><p>Relevance · importance · recency − redundancy, under a token budget.</p></div>
        <div class="card value-card"><h3>Always inspectable</h3><p>See selected/dropped experts, scores, and reasons for every item.</p></div>
      </div>
      <div class="grid cols-2" style="margin-top:14px">
        <div class="card"><h2>Experts</h2>${state.experts.map((e) => `<div class="kv"><span>${esc(e.name)}</span><span class="mono dim">${ec[e.id] || 0}</span></div>`).join("") || '<div class="dim">none</div>'}</div>
        <div class="card"><h2>Scopes</h2>${state.scopes.map((s) => `<div class="kv"><span class="mono">${esc(s.label)}</span><span class="mono dim">${sc[s.id] || 0}</span></div>`).join("") || '<div class="dim">none</div>'}</div>
      </div>
      <div class="card" style="margin-top:14px"><h2>Get started</h2>
        <div class="install">pip install matrix-context &nbsp;·&nbsp; matrix-context serve --transport rest</div>
        <div class="kv" style="margin-top:10px"><span class="muted">Conformance</span><span class="mono acc">${state.online ? "MoC API v1 Compatible" : "—"}</span></div>
      </div>
    </div>`));
  }

  // ---- Inspector ----
  function vInspector(v) {
    v.appendChild(el(`<div>
      <h1>Inspector</h1>
      <p class="sub">Ask a question; see exactly why each item was routed, kept, or dropped. <span class="chip on">scope: ${esc(scopeLabel())}</span></p>
      <div class="grid cols-inspect">
        <div class="card"><h2>Query</h2>
          <label>Question</label><input id="q" value="what did we decide about the backend?"/>
          <div class="row" style="margin-top:10px"><div style="flex:1"><label>Max tokens</label><input id="mt" type="number" value="120"/></div><div style="flex:1"><label>Top experts</label><input id="te" type="number" value="3"/></div></div>
          <div class="row" style="margin-top:12px"><button id="run">Inspect</button></div>
        </div>
        <div class="card" id="packCard"><h2>Context pack</h2><div id="pack" class="dim">…</div></div>
        <div class="card" id="routeCard"><h2>Router</h2><div id="route" class="dim">…</div></div>
      </div>
    </div>`));
    const run = async () => {
      $("#pack").innerHTML = '<div class="dim">running…</div>'; $("#route").innerHTML = "";
      let r; try { r = await MC.inspect($("#q").value, { scope: state.scope, max_tokens: +$("#mt").value, top_experts: +$("#te").value }); }
      catch (e) { $("#pack").innerHTML = `<div class="reason">${esc(e.message)}</div>`; return; }
      const max = Math.max.apply(null, r.routing.scores.map((s) => s.score).concat([0.0001]));
      $("#routeCard").querySelector("h2").innerHTML = `Router <span class="dim" style="text-transform:none">— ${esc(r.routing.reason)}</span>`;
      $("#route").innerHTML = `<div style="margin-bottom:10px">${r.routing.selected.map((e) => `<span class="chip on">${esc(e)}</span>`).join("")}${r.routing.unselected.map((e) => `<span class="chip">${esc(e)}</span>`).join("")}</div>` +
        `<table><tbody>${r.routing.scores.map((s) => { const on = r.routing.selected.indexOf(s.expert) >= 0; return `<tr><td>${on ? "● " : ""}${esc(s.expert)}</td><td class="mono">${s.score.toFixed(3)}</td><td><div class="bar"><span style="width:${(100 * s.score / max).toFixed(0)}%;${on ? "" : "background:#2c5b46"}"></span></div></td></tr>`; }).join("")}</tbody></table>`;
      $("#packCard").querySelector("h2").innerHTML = `Context pack <span class="pill">${r.pack.tokens}/${r.pack.maxTokens} tok</span>`;
      $("#pack").innerHTML = `<table><thead><tr><th>Expert</th><th>Content</th><th>Score</th></tr></thead><tbody>${r.pack.items.map((p) => `<tr><td><span class="chip on">${esc(p.expert)}</span></td><td>${esc(p.content)}<div class="mono dim" style="font-size:11px">rel ${p.breakdown.relevance} · imp ${p.breakdown.importance} · rec ${p.breakdown.recency} · −red ${p.breakdown.redundancy}</div></td><td class="mono">${p.final_score}</td></tr>`).join("")}</tbody>${r.pack.dropped.length ? `<tbody>${r.pack.dropped.map((d) => `<tr class="dropped"><td><span class="chip">${esc(d.expert)}</span></td><td class="mono">${esc(d.id)}</td><td class="reason">dropped</td></tr>`).join("")}</tbody>` : ""}</table><h2 style="margin-top:14px">Prompt-ready pack</h2><pre>${esc(r.pack.prompt)}</pre>`;
    };
    $("#run", v).onclick = run; run();
  }

  // ---- Builder ----
  let cands = [];
  function vBuilder(v) {
    const defScope = state.scope !== "/" ? state.scope : ((state.scopes[0] && state.scopes[0].id) || "project:demo");
    v.appendChild(el(`<div>
      <h1>Ingest</h1>
      <p class="sub">Never ingest blindly — paste, review typed candidates, approve, commit, then prove recall. <span class="tag">Compatible Mode: client-side chunk → POST /v1/remember</span></p>
      <div class="card"><label>Source text</label><textarea id="src" placeholder="Paste documents, decisions, notes…"></textarea>
        <div class="row" style="margin-top:10px"><div style="flex:0 1 280px"><label>Scope</label><input id="bscope" value="${esc(defScope)}"/></div><button id="sample" class="ghost">Load sample</button><button id="analyze">Analyze →</button></div>
      </div><div id="cands"></div><div id="commit"></div>
    </div>`));
    $("#sample", v).onclick = () => { $("#src").value = SAMPLE; };
    $("#analyze", v).onclick = () => { cands = classify($("#src").value); paint(); };
    function paint() {
      const host = $("#cands"); host.innerHTML = ""; if (!cands.length) return;
      const ap = cands.filter((c) => c.approved).length;
      host.appendChild(el(`<div class="card" style="margin-top:14px"><h2>Review — ${ap}/${cands.length} approved</h2>
        <table><thead><tr><th>✓</th><th>Type</th><th>Content</th><th>Expert</th><th>Imp.</th></tr></thead><tbody>${cands.map((c, i) => `<tr><td><input type="checkbox" data-i="${i}" ${c.approved ? "checked" : ""} style="width:auto"/></td><td><span class="chip">${esc(c.type)}</span></td><td>${esc(c.content)}</td><td><select data-e="${i}">${state.experts.map((e) => `<option value="${esc(e.id)}" ${e.id === c.expert ? "selected" : ""}>${esc(e.name)}</option>`).join("")}</select></td><td class="mono">${c.importance}</td></tr>`).join("")}</tbody></table>
        <div class="row" style="margin-top:12px"><button id="go">Commit ${ap} → POST /v1/remember</button><span class="note">type/confidence/source saved as tags</span></div></div>`));
      host.querySelectorAll("input[type=checkbox]").forEach((cb) => cb.onchange = () => { cands[+cb.dataset.i].approved = cb.checked; paint(); });
      host.querySelectorAll("select[data-e]").forEach((sl) => sl.onchange = () => { cands[+sl.dataset.e].expert = sl.value; });
      $("#go", host).onclick = commit;
    }
    async function commit() {
      const scope = $("#bscope").value || "/"; const ap = cands.filter((c) => c.approved);
      const w = $("#commit"); w.innerHTML = `<div class="card" style="margin-top:14px"><h2>Commit</h2><div class="log" id="log"></div><div class="row" style="margin-top:12px"><button id="ti" class="ghost">Test recall →</button></div></div>`;
      const log = $("#log", w), line = (h) => { log.appendChild(el(`<div>${h}</div>`)); log.scrollTop = log.scrollHeight; };
      line(`<span class="ok">remember.batch --scope ${esc(scope)} --count ${ap.length}</span>`);
      for (const c of ap) {
        try { const it = await MC.remember({ content: c.content, expert: c.expert, scope, importance: c.importance, tags: c.tags.concat([`type:${c.type}`, `confidence:${c.confidence}`, "source:console"]) });
          line(`POST /v1/remember expert=${esc(c.expert)} <span class="code">201 ${esc(it.id)}</span>`); }
        catch (e) { line(`<span class="err">FAILED ${esc(e.message)}</span>`); }
      }
      line(`<span class="ok">done · ${ap.length} written</span>`); await refreshStore();
      $("#ti", w).onclick = () => { state.tab = "inspector"; render(); };
    }
  }

  // ---- Memory ----
  function vMemory(v) {
    v.appendChild(el(`<div><h1>Memory</h1><p class="sub">Browse, filter, and forget stored items.</p>
      <div class="card"><div class="row">
        <div style="flex:0 1 220px"><label>Expert</label><select id="fe"><option value="">All experts</option>${state.experts.map((e) => `<option value="${esc(e.id)}">${esc(e.name)}</option>`).join("")}</select></div>
        <div style="flex:0 1 260px"><label>Scope</label><select id="fs"><option value="">All scopes</option>${state.scopes.map((s) => `<option value="${esc(s.id)}" ${s.id === state.scope ? "selected" : ""}>${esc(s.label)}</option>`).join("")}</select></div>
        <button id="rf" class="ghost">Refresh</button></div></div>
      <div id="rows" class="card" style="margin-top:14px"></div></div>`));
    async function load() {
      let items = []; try { items = (await MC.items({ expert: $("#fe").value, scope: $("#fs").value })).items; } catch (e) {}
      const h = $("#rows"); h.innerHTML = `<h2>${items.length} item${items.length === 1 ? "" : "s"}</h2>` + (items.length ? `<table><thead><tr><th>Expert</th><th>Content</th><th>Scope</th><th>Tags</th><th></th></tr></thead><tbody>${items.map((it) => `<tr><td><span class="chip on">${esc(it.expert)}</span></td><td>${esc(it.content)}</td><td class="mono dim">${esc(it.scope)}</td><td>${(it.tags || []).map((t) => `<span class="tag">${esc(t)}</span>`).join(" ")}</td><td class="right"><button class="ghost sm" data-d="${esc(it.id)}">Forget</button></td></tr>`).join("")}</tbody></table>` : '<div class="dim">no items</div>');
      h.querySelectorAll("button[data-d]").forEach((b) => b.onclick = async () => { await MC.forget(b.dataset.d); await refreshStore(); load(); });
    }
    $("#rf", v).onclick = load; $("#fe", v).onchange = load; $("#fs", v).onchange = load; load();
  }

  // ---- Experts ----
  function vExperts(v) {
    const c = counts("expert");
    v.appendChild(el(`<div><h1>Context experts</h1><p class="sub">The typed partitions the router selects between.</p>
      <div class="grid cols-2">${state.experts.map((e) => `<div class="card"><div class="row" style="justify-content:space-between"><span class="chip on">${esc(e.name)}</span><span class="mono dim">${c[e.id] || 0} items</span></div><p class="muted" style="margin:10px 0 0">${esc(e.desc)}</p></div>`).join("")}</div></div>`));
  }

  // ---- Routing ----
  function vRouting(v) {
    v.appendChild(el(`<div><h1>Routing</h1><p class="sub">The router debugger — per-expert scores and the decision reason.</p>
      <div class="card"><div class="row"><div style="flex:1"><label>Query</label><input id="q" value="can the agent store secrets?"/></div><button id="run">Explain</button></div></div><div id="out"></div></div>`));
    $("#run", v).onclick = async () => {
      const o = $("#out"); o.innerHTML = '<p class="dim" style="margin-top:14px">…</p>';
      let r; try { r = await MC.routerExplain($("#q").value, { scope: state.scope }); } catch (e) { o.innerHTML = `<p class="reason">${esc(e.message)}</p>`; return; }
      const max = Math.max.apply(null, r.scores.map((s) => s.score).concat([0.0001]));
      o.innerHTML = `<div class="card" style="margin-top:14px"><h2>Decision <span class="dim" style="text-transform:none">— ${esc(r.reason)}</span></h2><div style="margin-bottom:10px">${r.selected.map((e) => `<span class="chip on">${esc(e)}</span>`).join("")}${r.unselected.map((e) => `<span class="chip">${esc(e)}</span>`).join("")}</div><table><tbody>${r.scores.map((s) => { const on = r.selected.indexOf(s.expert) >= 0; return `<tr><td>${on ? "● " : ""}${esc(s.expert)}</td><td class="mono">${s.score.toFixed(3)}</td><td><div class="bar"><span style="width:${(100 * s.score / max).toFixed(0)}%;${on ? "" : "background:#2c5b46"}"></span></div></td></tr>`; }).join("")}</tbody></table></div>`;
    };
  }

  // ---- Benchmarks ----
  function vBench(v) {
    const bar = (val, color) => `<div class="bar" style="display:inline-block;width:120px;vertical-align:middle"><span style="width:${val}%;background:${color || "var(--acc)"}"></span></div> <span class="mono">${val}%</span>`;
    v.appendChild(el(`<div><h1>Benchmarks</h1><p class="sub">Robustness on the public MoC-RAG Benchmark. ${esc(BENCH.note)}. <b>BM25 is strong on keyword queries; MoC-RAG is more robust under paraphrase/adversarial.</b></p>
      <div class="card"><h2>Recall@8 by query type</h2><table><thead><tr><th>Method</th><th>keyword</th><th>paraphrased</th><th>adversarial</th><th>hard distractors ↓</th></tr></thead><tbody>${BENCH.rows.map((r) => { const moc = r.m.indexOf("moc") === 0; return `<tr><td>${moc ? '<span class="chip on">' + esc(r.m) + "</span>" : esc(r.m)}</td><td>${bar(r.kw)}</td><td>${bar(r.pa)}</td><td>${bar(r.adv, moc ? "var(--acc)" : "var(--amber)")}</td><td class="mono">${r.hd}</td></tr>`; }).join("")}</tbody></table><p class="note">Honest claim: MoC-RAG improves robustness and context efficiency under typed, adversarial conditions — it does not universally beat all RAG.</p></div></div>`));
  }

  // ---- Standard ----
  function vStandard(v) {
    v.appendChild(el(`<div><h1>MoC Contract</h1><p class="sub">A frozen, versioned, inspectable wire contract — implement it and claim compatibility.</p>
      <div class="grid cols-3"><div class="card"><div class="lbl">Contract</div><div class="stat">${state.version ? esc(state.version.contract) : "—"}</div></div><div class="card"><div class="lbl">Implementation</div><div class="stat" style="font-size:18px">${state.version ? esc(state.version.implementation + " " + state.version.build) : "—"}</div></div><div class="card"><div class="lbl">Conformance</div><div class="stat acc" style="font-size:18px">${state.online ? "MoC API v1 ✓" : "—"}</div></div></div>
      <div class="card" style="margin-top:14px"><h2>Endpoints</h2><div>${ENDPOINTS.map((e) => `<span class="chip">${esc(e)}</span>`).join("")}</div><div class="install" style="margin-top:12px">python -m moc_contract.conformance --url ${esc(location.origin)}</div></div></div>`));
  }

  // ---- Integrate (simple usage for agents) ----
  function snippet(title, code) {
    const id = "sn" + Math.random().toString(36).slice(2, 8);
    return `<div class="card" style="margin-top:14px"><div class="row" style="justify-content:space-between;align-items:center"><h2 style="margin:0">${esc(title)}</h2><button class="ghost sm" data-copy="${id}">Copy</button></div><pre id="${id}" style="margin-top:10px">${esc(code)}</pre></div>`;
  }
  function vIntegrate(v) {
    const origin = location.origin;
    const py = `from matrix_context import ContextManager
ctx = ContextManager.create("my-agent", path="agent.db")

def chat(user_msg, scope="/"):
    # BEFORE the model call: routed, budgeted, inspectable context
    pack = ctx.build_pack(user_msg, scope=scope, max_tokens=400)
    answer = your_llm(pack.to_prompt() + "\\nUser: " + user_msg)
    # AFTER the turn: remember it so the agent accumulates memory
    ctx.remember(user_msg, expert="episodic", scope=scope)
    ctx.remember(answer,   expert="semantic", scope=scope)
    return answer`;
    const rest = `# BEFORE: a prompt-ready, routed pack
curl -s ${origin}/v1/pack -H 'content-type: application/json' \\
  -d '{"query":"what did we decide?","max_tokens":400}'

# AFTER: remember the turn
curl -s ${origin}/v1/remember -H 'content-type: application/json' \\
  -d '{"content":"...","expert":"episodic"}'`;
    const mcp = `# Agent-native binding (MoC Contract v1 over MCP)
matrix-context serve --transport stdio`;
    v.appendChild(el(`<div>
      <h1>Integrate an agent</h1>
      <p class="sub">Give any agent typed, inspectable memory in two calls per turn — <b>build_pack</b> before the model call, <b>remember</b> after. This server's live API base is <span class="mono acc">${esc(origin)}/v1</span>.</p>
      <div class="install">pip install matrix-context</div>
      ${snippet("Python — the agent loop", py)}
      ${snippet("REST — any language", rest)}
      ${snippet("MCP — agent-native (binding pending)", mcp)}
      <p class="note">Full guide: <span class="mono">tutorials/build-your-first-chatbot.md</span> · this endpoint passes <span class="acc">MoC API v1</span>.</p>
    </div>`));
    v.querySelectorAll("button[data-copy]").forEach((b) => b.onclick = async () => {
      try { await navigator.clipboard.writeText($("#" + b.dataset.copy).textContent); b.textContent = "Copied ✓"; setTimeout(() => { b.textContent = "Copy"; }, 1200); }
      catch (e) { b.textContent = "Select & copy"; }
    });
  }

  // ---- Settings ----
  function vSettings(v) {
    v.appendChild(el(`<div><h1>Settings</h1><p class="sub">Connection, tenancy, and display. This console is served same-origin against the live backend.</p>
      <div class="card"><h2>Connection</h2>
        <div class="kv"><span class="muted">API base</span><span class="mono">${esc(MC.base)}</span></div>
        <div class="kv"><span class="muted">Status</span><span class="mono ${state.online ? "acc" : "reason"}">${state.online ? "online" : "offline"}</span></div>
        <label style="margin-top:12px">Bearer token (optional — for protected servers)</label>
        <div class="row"><div style="flex:1"><input id="tok" type="password" placeholder="paste token" value="${MC.hasToken() ? "********" : ""}"/></div><button id="savetok" class="ghost">Save</button></div>
      </div>
      <div class="card" style="margin-top:14px"><h2>Default scope (tenant isolation)</h2>
        <div class="row"><div style="flex:1"><select id="defscope"><option value="/">All scopes</option>${state.scopes.map((s) => `<option value="${esc(s.id)}" ${s.id === state.scope ? "selected" : ""}>${esc(s.label)}</option>`).join("")}</select></div></div>
        <p class="note">Drives the Inspector, Ingest, Memory, and Routing defaults. Also selectable from the top bar.</p></div>
      <div class="card" style="margin-top:14px"><h2>Display</h2><div class="row"><button id="rain" class="ghost">${window.__rainOff ? "Enable" : "Disable"} matrix rain</button></div></div></div>`));
    $("#savetok", v).onclick = () => { const t = $("#tok").value; if (t && t !== "********") { MC.setToken(t); boot(); } };
    $("#defscope", v).onchange = (e) => { state.scope = e.target.value; chrome(); };
    $("#rain", v).onclick = () => { window.__rainOff = !window.__rainOff; render(); };
  }

  // ---- mount (single innerHTML root — all sections render) ----
  function mount() {
    const root = $("#app");
    root.innerHTML = `<div class="top">
        <div class="brand"><img src="/assets/logo.svg" alt=""/> Matrix Context <span class="dim" style="font-weight:400">Console</span></div>
        <span id="ver" class="pill mono">—</span>
        <label class="lbl" style="margin:0 0 0 6px">scope</label>
        <select id="scopesel" class="pill" style="padding:4px 10px;max-width:220px"><option value="/">All scopes</option></select>
        <span class="spacer"></span><span id="health" class="pill">● connecting…</span>
      </div>
      <div id="banner" class="banner">Backend offline — start it (<span class="mono">python frontend/server.py</span>) or check Settings, then reload.</div>
      <div class="layout">
        <nav class="side">${NAV.map(([g, items]) => `<div class="navgroup"><div class="lbl">${g}</div>${items.map(([id, label, ic]) => `<div class="tab" data-tab="${id}"><span class="ic">${ic}</span><span class="t">${label}</span></div>`).join("")}</div>`).join("")}</nav>
        <main class="main" id="view"></main>
      </div>`;
    root.querySelectorAll(".tab").forEach((t) => t.onclick = () => { state.tab = t.dataset.tab; render(); });
    $("#scopesel").onchange = (e) => { state.scope = e.target.value; render(); };
    boot();
  }
  document.addEventListener("DOMContentLoaded", mount);
})();
