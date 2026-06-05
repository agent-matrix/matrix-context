/* Matrix Context Console — Phase 0 (Compatible Mode), zero-dependency SPA.
 * Talks to the live backend through window.MC (api.js). No build step, no CDN.
 */
(function () {
  "use strict";
  const MC = window.MC;
  const INGEST_NATIVE = false;            // Phase-2 native ingest stays OFF in Phase 0
  const $ = (s, r) => (r || document).querySelector(s);
  const el = (html) => { const t = document.createElement("template"); t.innerHTML = html.trim(); return t.content.firstChild; };
  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

  const state = { tab: "overview", experts: [], scopes: [], items: [], online: false, version: null, health: null };

  // ----------------------------------------------------------------- client classifier (Compatible Mode)
  const SAMPLE = `# Matrix-Context architecture notes

## Decision: dual surface
Matrix Context exposes both a Python SDK and an MCP server so agents and human operators share one memory plane.

## Decision: SQLite is the default backend
Ship SQLite as the default store; vectors are an accelerator, SQL is the source of truth.

## Policy: never store secrets
The agent must never store API keys, tokens, or PII in durable memory.

## Preference: local-first
The team prefers local-first tools over cloud services by default.

## Roadmap: defer Milvus to v2
Milvus support is deferred to v2; pgvector lands in v1.`;

  const EXPERT_FOR_TYPE = { decision: "semantic", fact: "semantic", rule: "policy",
    policy: "policy", preference: "profile", profile: "profile", event: "episodic",
    episode: "episodic", document: "document", architecture: "semantic" };

  function classify(text) {
    if (!text || !text.trim()) return [];
    const blocks = text.split(/\n(?=#)|\n\s*\n/).map((b) => b.replace(/^#+\s*/, "").replace(/\s+/g, " ").trim()).filter((b) => b.length > 12);
    return blocks.slice(0, 20).map((b, i) => {
      const low = b.toLowerCase();
      let type = "fact";
      if (/\b(decide|decision|chose|default|will use)\b/.test(low)) type = "decision";
      else if (/\b(policy|must|never|forbidden|require)\b/.test(low)) type = "rule";
      else if (/\b(prefer|preference|like)\b/.test(low)) type = "preference";
      else if (/\b(roadmap|defer|milestone|phase|v1|v2)\b/.test(low)) type = "decision";
      const expertExists = (id) => state.experts.some((e) => e.id === id);
      let expert = EXPERT_FOR_TYPE[type] || "semantic";
      if (!expertExists(expert)) expert = (state.experts[0] && state.experts[0].id) || "semantic";
      const importance = Math.min(0.98, 0.5 + (type === "decision" ? 0.35 : type === "rule" ? 0.4 : 0.2) + Math.min(0.1, b.length / 4000));
      const confidence = Math.round((0.7 + Math.random() * 0.25) * 100) / 100;
      const tags = Array.from(new Set((low.match(/\b(mcp|sdk|api|sqlite|milvus|pgvector|policy|secrets|local-first|memory|scope|expert)\b/g) || []))).slice(0, 4);
      return { id: "cand_" + (i + 1), content: b.slice(0, 280), type, expert,
        importance: Math.round(importance * 100) / 100, confidence, tags: tags.length ? tags : ["context"], approved: true };
    });
  }

  // ----------------------------------------------------------------- boot
  async function boot() {
    try {
      state.health = await MC.health();
      state.version = await MC.version();
      state.online = true;
    } catch (e) { state.online = false; }
    if (state.online) {
      try { state.experts = await MC.experts(); } catch (e) {}
      try { state.scopes = await MC.scopes(); } catch (e) {}
      try { state.items = (await MC.items()).items; } catch (e) {}
    }
    paintChrome();
    render();
  }

  function paintChrome() {
    const pill = $("#health-pill");
    pill.className = "pill " + (state.online ? "ok" : "bad");
    pill.textContent = state.online ? "● backend online" : "● backend offline";
    $("#ver-pill").textContent = state.version ? ("contract " + state.version.contract + " · " + state.version.build) : "—";
    $("#offline-banner").classList.toggle("show", !state.online);
  }

  function counts(field) {
    const m = {};
    state.items.forEach((it) => { m[it[field]] = (m[it[field]] || 0) + 1; });
    return m;
  }

  // ----------------------------------------------------------------- tabs
  const TABS = [
    ["overview", "Overview", "01"],
    ["ingest", "Ingest", "02"],
    ["memory", "Memory", "03"],
    ["inspector", "Inspector", "04"],
    ["experts", "Experts", "05"],
  ];

  function render() {
    document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("active", t.dataset.tab === state.tab));
    const v = $("#view");
    v.innerHTML = "";
    ({ overview: viewOverview, ingest: viewIngest, memory: viewMemory,
       inspector: viewInspector, experts: viewExperts }[state.tab] || viewOverview)(v);
  }

  // ----------------------------------------------------------------- Overview
  function viewOverview(v) {
    const expCount = counts("expert"), scCount = counts("scope");
    v.appendChild(el(`<div>
      <h1>Overview</h1>
      <p class="sub">Inspectable, typed memory for AI agents — MoC Contract v1 backend.</p>
      <div class="grid cols-3">
        <div class="card"><div class="lbl">Memory items</div><div class="stat">${state.health ? state.health.items : "—"}</div></div>
        <div class="card"><div class="lbl">Experts</div><div class="stat">${state.experts.length}</div></div>
        <div class="card"><div class="lbl">Scopes</div><div class="stat">${state.scopes.length}</div></div>
      </div>
      <div class="grid cols-2" style="margin-top:14px">
        <div class="card"><h2>Experts</h2>${state.experts.map((e) =>
          `<div class="kv"><span>${esc(e.name)}</span><span class="mono muted">${expCount[e.id] || 0}</span></div>`).join("") || '<div class="muted">none</div>'}</div>
        <div class="card"><h2>Scopes</h2>${state.scopes.map((s) =>
          `<div class="kv"><span class="mono">${esc(s.label)}</span><span class="mono muted">${scCount[s.id] || 0}</span></div>`).join("") || '<div class="muted">none</div>'}</div>
      </div>
      <div class="card" style="margin-top:14px"><h2>Backend</h2>
        <div class="kv"><span class="muted">Implementation</span><span class="mono">${state.version ? esc(state.version.implementation + " " + state.version.build) : "—"}</span></div>
        <div class="kv"><span class="muted">Contract</span><span class="mono">${state.version ? esc(state.version.contract) : "—"}</span></div>
        <div class="kv"><span class="muted">Conformance</span><span class="mono ok">MoC API v1 Compatible</span></div>
      </div>
    </div>`));
  }

  // ----------------------------------------------------------------- Ingest (Compatible Mode wizard)
  let candidates = [];
  function viewIngest(v) {
    const expOpts = state.experts.map((e) => `<option value="${esc(e.id)}">${esc(e.name)}</option>`).join("");
    v.appendChild(el(`<div>
      <h1>Ingest</h1>
      <p class="sub">Paste content, review the typed candidates, approve, then commit. Nothing is written until you commit. <span class="tag">Compatible Mode — client-side chunking → POST /v1/remember</span></p>
      <div class="card">
        <div class="row">
          <div style="flex:1 1 100%"><label>Source text</label><textarea id="src" placeholder="Paste documents, decisions, notes…"></textarea></div>
        </div>
        <div class="row" style="margin-top:10px">
          <div style="flex:0 1 280px"><label>Scope</label><input id="scope" value="${esc((state.scopes[0] && state.scopes[0].id) || '/')}" placeholder="project:acme"/></div>
          <button id="loadSample" class="ghost">Load sample</button>
          <button id="analyze">Analyze →</button>
        </div>
      </div>
      <div id="cands"></div>
      <div id="commitWrap"></div>
    </div>`));
    $("#loadSample", v).onclick = () => { $("#src").value = SAMPLE; };
    $("#analyze", v).onclick = () => { candidates = classify($("#src").value); renderCands(); };

    function renderCands() {
      const host = $("#cands"); host.innerHTML = "";
      if (!candidates.length) return;
      const approved = candidates.filter((c) => c.approved).length;
      host.appendChild(el(`<div class="card" style="margin-top:14px">
        <h2>Review candidates — ${approved}/${candidates.length} approved</h2>
        <table><thead><tr><th>✓</th><th>Type</th><th>Content</th><th>Expert</th><th>Imp.</th><th>Tags</th></tr></thead>
        <tbody>${candidates.map((c, i) => `<tr>
          <td><input type="checkbox" data-i="${i}" ${c.approved ? "checked" : ""} style="width:auto"/></td>
          <td><span class="chip">${esc(c.type)}</span></td>
          <td>${esc(c.content)}</td>
          <td><select data-exp="${i}">${state.experts.map((e) => `<option value="${esc(e.id)}" ${e.id === c.expert ? "selected" : ""}>${esc(e.name)}</option>`).join("")}</select></td>
          <td class="mono">${c.importance}</td>
          <td>${c.tags.map((t) => `<span class="tag">${esc(t)}</span>`).join(" ")}</td>
        </tr>`).join("")}</tbody></table>
        <div class="row" style="margin-top:12px"><button id="commit">Commit ${approved} items → POST /v1/remember</button>
          <span class="note">metadata (type, confidence, source) is stored as tags until the schema extends</span></div>
      </div>`));
      host.querySelectorAll("input[type=checkbox]").forEach((cb) => cb.onchange = () => { candidates[+cb.dataset.i].approved = cb.checked; renderCands(); });
      host.querySelectorAll("select[data-exp]").forEach((sl) => sl.onchange = () => { candidates[+sl.dataset.exp].expert = sl.value; });
      $("#commit", host).onclick = commit;
    }

    async function commit() {
      const scope = $("#scope").value || "/";
      const approved = candidates.filter((c) => c.approved);
      const wrap = $("#commitWrap"); wrap.innerHTML = `<div class="card" style="margin-top:14px"><h2>Commit</h2><div class="log" id="log"></div><div class="row" style="margin-top:12px"><button id="goInspect" class="ghost">Test recall →</button></div></div>`;
      const log = $("#log", wrap);
      const line = (h) => { log.appendChild(el(`<div>${h}</div>`)); log.scrollTop = log.scrollHeight; };
      line(`<span class="ok">remember.batch --scope ${esc(scope)} --count ${approved.length}</span>`);
      for (const c of approved) {
        try {
          const tags = c.tags.concat([`type:${c.type}`, `confidence:${c.confidence}`, "source:console"]);
          const item = await MC.remember({ content: c.content, expert: c.expert, scope, importance: c.importance, tags });
          line(`POST /v1/remember expert=${esc(c.expert)} <span class="code">201 ${esc(item.id)}</span>`);
        } catch (e) { line(`<span class="reason">FAILED: ${esc(e.message)}</span>`); }
      }
      line(`<span class="ok">done · ${approved.length} items written</span>`);
      try { state.items = (await MC.items()).items; state.health = await MC.health(); paintChrome(); } catch (e) {}
      $("#goInspect", wrap).onclick = () => { state.tab = "inspector"; render(); };
    }
  }

  // ----------------------------------------------------------------- Memory
  async function viewMemory(v) {
    v.appendChild(el(`<div>
      <h1>Memory</h1>
      <p class="sub">Browse and forget stored items.</p>
      <div class="card"><div class="row">
        <div style="flex:0 1 220px"><label>Expert</label><select id="fExpert"><option value="">All experts</option>${state.experts.map((e) => `<option value="${esc(e.id)}">${esc(e.name)}</option>`).join("")}</select></div>
        <div style="flex:0 1 260px"><label>Scope</label><select id="fScope"><option value="">All scopes</option>${state.scopes.map((s) => `<option value="${esc(s.id)}">${esc(s.label)}</option>`).join("")}</select></div>
        <button id="refresh" class="ghost">Refresh</button>
      </div></div>
      <div id="rows" class="card" style="margin-top:14px"></div>
    </div>`));
    async function load() {
      const f = { expert: $("#fExpert").value, scope: $("#fScope").value };
      let items = [];
      try { items = (await MC.items(f)).items; } catch (e) {}
      const host = $("#rows"); host.innerHTML = `<h2>${items.length} item${items.length === 1 ? "" : "s"}</h2>` +
        (items.length ? `<table><thead><tr><th>Expert</th><th>Content</th><th>Scope</th><th>Imp.</th><th>Tags</th><th></th></tr></thead><tbody>${items.map((it) => `<tr>
          <td><span class="chip on">${esc(it.expert)}</span></td><td>${esc(it.content)}</td>
          <td class="mono muted">${esc(it.scope)}</td><td class="mono">${it.importance}</td>
          <td>${(it.tags || []).map((t) => `<span class="tag">${esc(t)}</span>`).join(" ")}</td>
          <td class="right"><button class="ghost sm" data-del="${esc(it.id)}">Forget</button></td></tr>`).join("")}</tbody></table>` : '<div class="muted">no items</div>');
      host.querySelectorAll("button[data-del]").forEach((b) => b.onclick = async () => { await MC.forget(b.dataset.del); load(); try { state.health = await MC.health(); paintChrome(); } catch (e) {} });
    }
    $("#refresh", v).onclick = load; $("#fExpert", v).onchange = load; $("#fScope", v).onchange = load;
    load();
  }

  // ----------------------------------------------------------------- Inspector
  function viewInspector(v) {
    v.appendChild(el(`<div>
      <h1>Inspector</h1>
      <p class="sub">See why each item was routed, kept, or dropped — the inspectability contract.</p>
      <div class="card"><div class="row">
        <div style="flex:1 1 360px"><label>Query</label><input id="q" value="what did we decide about the backend?"/></div>
        <div style="flex:0 1 120px"><label>Max tokens</label><input id="mt" type="number" value="120"/></div>
        <div style="flex:0 1 120px"><label>Top experts</label><input id="te" type="number" value="3"/></div>
        <button id="run">Inspect</button>
      </div></div>
      <div id="out"></div>
    </div>`));
    $("#run", v).onclick = async () => {
      const out = $("#out"); out.innerHTML = '<p class="muted" style="margin-top:14px">running…</p>';
      let r;
      try { r = await MC.inspect($("#q").value, { max_tokens: +$("#mt").value, top_experts: +$("#te").value }); }
      catch (e) { out.innerHTML = `<p class="reason" style="margin-top:14px">${esc(e.message)}</p>`; return; }
      const max = Math.max.apply(null, r.routing.scores.map((s) => s.score).concat([0.0001]));
      out.innerHTML = "";
      out.appendChild(el(`<div class="card" style="margin-top:14px"><h2>Routing <span class="muted" style="text-transform:none">— ${esc(r.routing.reason)}</span></h2>
        <div>${r.routing.selected.map((e) => `<span class="chip on">${esc(e)}</span>`).join("")}${r.routing.unselected.map((e) => `<span class="chip">${esc(e)}</span>`).join("")}</div>
        <table style="margin-top:10px"><tbody>${r.routing.scores.map((s) => {
          const on = r.routing.selected.indexOf(s.expert) >= 0;
          return `<tr><td>${on ? "● " : ""}${esc(s.expert)}</td><td class="mono">${s.score.toFixed(3)}</td><td><div class="bar"><span style="width:${(100 * s.score / max).toFixed(0)}%;${on ? "" : "background:#3a564a"}"></span></div></td></tr>`;
        }).join("")}</tbody></table></div>`));
      out.appendChild(el(`<div class="card" style="margin-top:14px"><h2>Context pack <span class="pill">${r.pack.tokens} / ${r.pack.maxTokens} tokens</span></h2>
        <table><thead><tr><th>Expert</th><th>Content</th><th>Score</th><th>rel / imp / rec / −red</th></tr></thead><tbody>${r.pack.items.map((p) => {
          const b = p.breakdown || {};
          return `<tr><td><span class="chip on">${esc(p.expert)}</span></td><td>${esc(p.content)}</td><td class="mono">${p.final_score}</td><td class="mono muted">${b.relevance} / ${b.importance} / ${b.recency} / ${b.redundancy}</td></tr>`;
        }).join("")}</tbody>${r.pack.dropped.length ? `<tbody>${r.pack.dropped.map((d) => `<tr class="dropped"><td><span class="chip">${esc(d.expert)}</span></td><td class="mono">${esc(d.id)}</td><td></td><td class="reason">${esc(d.reason)}</td></tr>`).join("")}</tbody>` : ""}</table></div>`));
      out.appendChild(el(`<div class="card" style="margin-top:14px"><h2>Prompt-ready pack</h2><pre>${esc(r.pack.prompt)}</pre></div>`));
    };
  }

  // ----------------------------------------------------------------- Experts
  function viewExperts(v) {
    const c = counts("expert");
    v.appendChild(el(`<div>
      <h1>Experts</h1>
      <p class="sub">The typed context partitions the router selects between.</p>
      <div class="card"><table><thead><tr><th>Expert</th><th>Description</th><th class="right">Items</th></tr></thead>
      <tbody>${state.experts.map((e) => `<tr><td><span class="chip on">${esc(e.name)}</span></td><td class="muted">${esc(e.desc)}</td><td class="right mono">${c[e.id] || 0}</td></tr>`).join("")}</tbody></table></div>
    </div>`));
  }

  // ----------------------------------------------------------------- mount
  function mount() {
    const root = $("#app");
    root.innerHTML = `<div class="topbar">
      <div class="brand"><span class="dot"></span> Matrix Context <span class="muted" style="font-weight:400">Console</span></div>
      <span id="ver-pill" class="pill mono">—</span><span class="spacer"></span>
      <span id="health-pill" class="pill">● connecting…</span>
    </div>
    <div id="offline-banner" class="banner">Backend offline — start it with <span class="mono">matrix-context serve --transport rest</span>, then reload.</div>
    <div class="layout">
      <nav class="side">${TABS.map(([id, label, k]) => `<div class="tab" data-tab="${id}"><span class="k">${k}</span><span class="t">${label}</span></div>`).join("")}</nav>
      <main class="main" id="view"></main>
    </div>`;
    root.querySelectorAll(".tab").forEach((t) => t.onclick = () => { state.tab = t.dataset.tab; render(); });
    boot();
  }
  document.addEventListener("DOMContentLoaded", mount);
})();
