# Architecture

Four planes: **ingest → store → route → serve**. SQL is the governance plane;
vectors are an accelerator. A query is routed to a subset of typed *context
experts* (session, profile, semantic, episodic, document, policy), retrieved
with hybrid BM25 + dense fusion (RRF), then assembled into a token-budgeted
pack scored by relevance, importance, recency decay and an MMR redundancy
penalty. `inspect()` exposes every decision.
