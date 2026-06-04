# Routing

Two tiers. A fast centroid gate scores the query against each expert's blended
item/description centroid. On low confidence or an indecisive margin it widens
selection rather than guessing — the seam where a v1 LLM classifier plugs in.
Deterministic keyword rules provide a transparent prior. The whole payoff is
gated on embedding quality; see `eval/`.
