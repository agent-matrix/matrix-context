/* Matrix Context — live API adapter (Phase 0, Compatible Mode).
 *
 * Drop-in replacement for the design's mock `window.MC`: same method names,
 * real `fetch` against the same-origin `/v1` surface. This is the ONE place that
 * maps the backend response shapes to what the UI consumes:
 *   - remember  -> read res.item            (backend returns {item:{…}})
 *   - inspect   -> res.routing.* + res.pack.* (selected/unselected/scores/…)
 *   - version   -> contract_version / implementation_version
 *   - scopes    -> plain strings
 * No contract changes; works against MoC Contract v1 as-is.
 */
(function () {
  const BASE = location.origin + "/v1";
  // Optional bearer token (Phase 1 servers may require it; harmless if unset).
  let TOKEN = (window.localStorage && localStorage.getItem("mc_token")) || "";

  function setToken(t) {
    TOKEN = t || "";
    if (window.localStorage) localStorage.setItem("mc_token", TOKEN);
  }

  async function call(method, path, body) {
    const headers = { "Content-Type": "application/json" };
    if (TOKEN) headers["Authorization"] = "Bearer " + TOKEN;
    const opt = { method, headers };
    if (body !== undefined) opt.body = JSON.stringify(body);
    let resp;
    try {
      resp = await fetch(BASE + path, opt);
    } catch (e) {
      throw new ApiError(0, "network error — is the backend running?");
    }
    let data = {};
    try { data = await resp.json(); } catch (e) { /* empty body */ }
    if (!resp.ok) throw new ApiError(resp.status, (data && data.error) || ("HTTP " + resp.status));
    return data;
  }

  function ApiError(status, message) { this.status = status; this.message = message; }
  ApiError.prototype = Object.create(Error.prototype);

  const MC = {
    base: BASE,
    setToken,
    hasToken: () => !!TOKEN,
    ApiError,

    // ---- discovery ----
    async health() {
      const h = await call("GET", "/health");
      return { status: h.status, name: h.name, version: h.version, items: h.items };
    },
    async version() {
      const v = await call("GET", "/version");
      return {
        contract: v.contract_version,
        implementation: v.implementation,
        build: v.implementation_version,
        name: v.name,
      };
    },
    async experts() {
      const r = await call("GET", "/experts");
      return (r.experts || []).map((e) => ({ id: e.name, name: e.name, desc: e.description || "" }));
    },
    async scopes() {
      const r = await call("GET", "/scopes");
      return (r.scopes || []).map((s) => ({ id: s, label: s }));   // plain strings -> objects
    },

    // ---- items ----
    async items(filter) {
      filter = filter || {};
      const q = [];
      if (filter.scope) q.push("scope=" + encodeURIComponent(filter.scope));
      if (filter.expert) q.push("expert=" + encodeURIComponent(filter.expert));
      const r = await call("GET", "/items" + (q.length ? "?" + q.join("&") : ""));
      return { items: r.items || [], count: r.count || 0 };
    },
    async getItem(id) {
      const r = await call("GET", "/items/" + encodeURIComponent(id));
      return r.item;
    },

    // ---- write ----
    async remember(item) {
      const r = await call("POST", "/remember", {
        content: item.content,
        expert: item.expert,
        scope: item.scope,
        importance: item.importance,
        tags: item.tags || [],
        ttl: item.ttl != null ? item.ttl : null,
      });
      return r.item;                          // {id, content, expert, scope, importance, tags, …}
    },
    async forget(id) {
      const r = await call("POST", "/forget", { id });
      return !!r.deleted;
    },

    // ---- recall / inspect ----
    async inspect(query, opts) {
      opts = opts || {};
      const r = await call("POST", "/inspect", {
        query,
        scope: opts.scope || "/",
        max_tokens: opts.max_tokens || 256,
        top_experts: opts.top_experts || 3,
        pin_experts: opts.pin_experts || [],
      });
      // Normalize routing.scores (object map) -> sorted array for the UI.
      const scores = Object.entries((r.routing && r.routing.scores) || {})
        .map(([expert, score]) => ({ expert, score }))
        .sort((a, b) => b.score - a.score);
      return {
        query: r.query,
        routing: {
          selected: (r.routing && r.routing.selected_experts) || [],
          unselected: (r.routing && r.routing.unselected_experts) || [],
          scores,
          widened: !!(r.routing && r.routing.widened),
          reason: (r.routing && r.routing.reason) || "",
        },
        pack: {
          tokens: r.pack && r.pack.tokens,
          maxTokens: r.pack && r.pack.max_tokens,
          items: (r.pack && r.pack.items) || [],
          dropped: (r.pack && r.pack.dropped) || [],
          citations: (r.pack && r.pack.citations) || [],
          prompt: (r.pack && r.pack.prompt) || "",
        },
      };
    },
    async routerExplain(query, opts) {
      opts = opts || {};
      const r = await call("POST", "/router/explain", {
        query, scope: opts.scope || "/", top_experts: opts.top_experts || 3,
      });
      return {
        selected: r.selected_experts || [],
        unselected: r.unselected_experts || [],
        scores: r.scores || [],
        reason: r.reason || "",
        widened: !!r.widened,
      };
    },
  };

  window.MC = MC;
})();
