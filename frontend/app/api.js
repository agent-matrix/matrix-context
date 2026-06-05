/* Matrix Context — live API adapter (same-origin /v1, MoC Contract v1).
 * Maps backend shapes for the UI: remember->item, inspect->routing/.pack,
 * version->contract_version/implementation_version, scopes->plain strings.
 */
(function () {
  const BASE = location.origin + "/v1";
  let TOKEN = (window.localStorage && localStorage.getItem("mc_token")) || "";
  function setToken(t) { TOKEN = t || ""; if (window.localStorage) localStorage.setItem("mc_token", TOKEN); }

  async function call(method, path, body) {
    const headers = { "Content-Type": "application/json" };
    if (TOKEN) headers["Authorization"] = "Bearer " + TOKEN;
    const opt = { method, headers };
    if (body !== undefined) opt.body = JSON.stringify(body);
    let resp;
    try { resp = await fetch(BASE + path, opt); }
    catch (e) { throw { status: 0, message: "network error — is the backend running?" }; }
    let data = {}; try { data = await resp.json(); } catch (e) {}
    if (!resp.ok) throw { status: resp.status, message: (data && data.error) || ("HTTP " + resp.status) };
    return data;
  }

  window.MC = {
    base: BASE, setToken, hasToken: () => !!TOKEN,
    async health() { return await call("GET", "/health"); },
    async version() {
      const v = await call("GET", "/version");
      return { contract: v.contract_version, implementation: v.implementation, build: v.implementation_version, name: v.name };
    },
    async experts() {
      const r = await call("GET", "/experts");
      return (r.experts || []).map((e) => ({ id: e.name, name: e.name, desc: e.description || "" }));
    },
    async scopes() {
      const r = await call("GET", "/scopes");
      return (r.scopes || []).map((s) => ({ id: s, label: s }));
    },
    async items(f) {
      f = f || {}; const q = [];
      if (f.scope) q.push("scope=" + encodeURIComponent(f.scope));
      if (f.expert) q.push("expert=" + encodeURIComponent(f.expert));
      const r = await call("GET", "/items" + (q.length ? "?" + q.join("&") : ""));
      return { items: r.items || [], count: r.count || 0 };
    },
    async remember(item) {
      const r = await call("POST", "/remember", {
        content: item.content, expert: item.expert, scope: item.scope,
        importance: item.importance, tags: item.tags || [], ttl: item.ttl != null ? item.ttl : null,
      });
      return r.item;
    },
    async forget(id) { return !!(await call("POST", "/forget", { id })).deleted; },
    async inspect(query, opts) {
      opts = opts || {};
      const r = await call("POST", "/inspect", {
        query, scope: opts.scope || "/", max_tokens: opts.max_tokens || 256,
        top_experts: opts.top_experts || 3, pin_experts: opts.pin_experts || [],
      });
      const scores = Object.entries((r.routing && r.routing.scores) || {})
        .map(([expert, score]) => ({ expert, score })).sort((a, b) => b.score - a.score);
      return {
        query: r.query,
        routing: {
          selected: (r.routing && r.routing.selected_experts) || [],
          unselected: (r.routing && r.routing.unselected_experts) || [],
          scores, widened: !!(r.routing && r.routing.widened), reason: (r.routing && r.routing.reason) || "",
        },
        pack: {
          tokens: r.pack && r.pack.tokens, maxTokens: r.pack && r.pack.max_tokens,
          items: (r.pack && r.pack.items) || [], dropped: (r.pack && r.pack.dropped) || [],
          citations: (r.pack && r.pack.citations) || [], prompt: (r.pack && r.pack.prompt) || "",
        },
      };
    },
    async routerExplain(query, opts) {
      opts = opts || {};
      const r = await call("POST", "/router/explain", { query, scope: opts.scope || "/", top_experts: opts.top_experts || 3 });
      return { selected: r.selected_experts || [], unselected: r.unselected_experts || [], scores: r.scores || [], reason: r.reason || "", widened: !!r.widened };
    },
  };
})();
