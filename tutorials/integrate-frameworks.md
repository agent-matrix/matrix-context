# Integrate Matrix Context with LangChain, LangGraph & CrewAI

*Download a real document, give it to Matrix Context, and let the top agentic
frameworks query it — with routed, budgeted, **inspectable** memory.*

Everything here is runnable. The shared step downloads a public document
(Wikipedia → *PostgreSQL*), chunks it, and ingests it into Matrix Context. Then
each framework recalls from it with **one call**: `build_pack`.

```bash
pip install matrix-context
python tutorials/integrations/mc_ingest.py     # download + ingest + sample query
```

Code lives in [`tutorials/integrations/`](integrations/):
`mc_ingest.py` (shared) · `langchain_demo.py` · `langgraph_demo.py` · `crewai_demo.py`.

---

## The shared step — ingest a document

`mc_ingest.py` downloads the document (cached under `integrations/data/` so it
also runs offline), splits it into paragraph chunks, and ingests each as a
`document` memory:

```python
from matrix_context import ContextManager

ctx = ContextManager.create("frameworks-demo", path=":memory:")
for chunk in chunks:                       # paragraphs of the downloaded doc
    ctx.remember(chunk, expert="document", scope="doc:postgresql", importance=0.6)

# the one call every framework wraps:
context_text = ctx.build_pack("What license is PostgreSQL under?", max_tokens=400).to_prompt()
```

That `context_text` is routed (only the `document` experts that match), budgeted
(fits the token budget), and inspectable (`ctx.inspect(query)` shows why).

## 1. LangChain — a Retriever

Wrap Matrix Context as a standard LangChain `Retriever`; any LCEL chain or agent
can then use it. ([`integrations/langchain_demo.py`](integrations/langchain_demo.py))

```python
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from pydantic import ConfigDict

class MatrixContextRetriever(BaseRetriever):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    ctx: object; scope: str = "/"; max_tokens: int = 400
    def _get_relevant_documents(self, query, *, run_manager=None):
        pack = self.ctx.build_pack(query, scope=self.scope, max_tokens=self.max_tokens)
        return [Document(page_content=p.item.content,
                         metadata={"expert": p.item.expert, "score": p.final_score})
                for p in pack.items]

retriever = MatrixContextRetriever(ctx=ctx, scope="doc:postgresql")
docs = retriever.invoke("What license is PostgreSQL released under?")
```

```bash
pip install langchain-core
python tutorials/integrations/langchain_demo.py
```

Drop `retriever` into any RAG chain (e.g. `retriever | prompt | ChatOpenAI()`),
and you get typed, inspectable retrieval instead of a flat vector lookup.

## 2. LangGraph — the memory loop as a graph

Each turn becomes three nodes: **retrieve** (`build_pack`) → **generate** (LLM)
→ **remember**. ([`integrations/langgraph_demo.py`](integrations/langgraph_demo.py))

```python
from langgraph.graph import StateGraph, START, END

def retrieve(s):  return {"context": CTX.build_pack(s["question"], max_tokens=300).to_prompt()}
def generate(s):  return {"answer": llm(s["question"], s["context"])}
def remember(s):  CTX.remember(s["question"], expert="session"); CTX.remember(s["answer"], expert="semantic"); return {}

g = StateGraph(State)
g.add_node("retrieve", retrieve); g.add_node("generate", generate); g.add_node("remember", remember)
g.add_edge(START, "retrieve"); g.add_edge("retrieve", "generate"); g.add_edge("generate", "remember"); g.add_edge("remember", END)
app = g.compile()
app.invoke({"question": "What does ACID mean?"})
```

```bash
pip install langgraph
python tutorials/integrations/langgraph_demo.py    # runs with a fake LLM, no key
```

## 3. CrewAI — a recall tool

Give any agent in a crew a tool that recalls memory.
([`integrations/crewai_demo.py`](integrations/crewai_demo.py))

```python
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

class MatrixContextTool(BaseTool):
    name: str = "matrix_context_recall"
    description: str = "Recall the most relevant typed memory for a query."
    class _Args(BaseModel): query: str = Field(...)
    args_schema = _Args
    def _run(self, query: str) -> str:
        return CTX.build_pack(query, max_tokens=400).to_prompt()
```

```bash
pip install crewai
python tutorials/integrations/crewai_demo.py
```

Attach the tool to a CrewAI `Agent(tools=[MatrixContextTool()])` and your crew
can recall project/document memory mid-task.

---

## Why this beats plain RAG

A "plain RAG" pipeline embeds everything into one flat index and returns the
nearest chunks for every query. Matrix Context adds a layer on top:

| | Flat RAG | Matrix Context |
|---|---|---|
| **Selection** | nearest vectors only | **routes to typed experts** first, then retrieves |
| **Noise** | distractors leak in | budgeted pack + redundancy penalty → cleaner context |
| **Why?** | opaque | **`inspect()`**: selected/dropped experts, scores, reasons |
| **Cost** | whatever fits | **token-budgeted** packs → fewer tokens per call |
| **Robustness** | brittle to paraphrase | holds under paraphrase/adversarial (see the [benchmark](../benchmarks/README.md)) |
| **Relevance** | similarity only | similarity **+ importance + recency + scope** |

On the public MoC-RAG Benchmark, under adversarial phrasing BM25 recall drops
~36 points while MoC-RAG holds within ~17 and carries ~half the hard distractors
of the dense baseline family.

## Matrix Context vs. a vector database (Milvus, pgvector, Qdrant)

They are **not competitors** — Matrix Context sits *above* a vector store.

- A vector DB (Milvus/pgvector/Qdrant) answers *"which vectors are nearest?"* at
  scale. That is the **accelerator**.
- Matrix Context answers *"which typed, budgeted, explainable memory should this
  agent see?"* — routing, packing, scoping, and inspection — and uses the vector
  DB underneath.
- **SQL is the source of truth; vectors are a rebuildable accelerator.** You can
  start on the zero-ops SQLite default and later point the vector channel at
  pgvector, Qdrant, or Milvus **without changing the contract or your agent code**.

So you don't choose *Matrix Context or Milvus* — you run Matrix Context's typed,
inspectable recall **on top of** Milvus when you need billion-scale ANN.

## Scaling to the enterprise

- **Multi-tenant isolation** via `scope` — `scope="user:42"` or
  `scope="project:acme"` keeps one tenant's memory from leaking into another's.
- **Swap the backend, keep the contract.** SQLite → pgvector/Qdrant/Milvus is a
  configuration change; the SDK, the REST `/v1` API, and your agents are
  unchanged. SQL stays the system of record; the vector index is rebuildable.
- **Stateless, horizontally scalable API.** The **[MoC Contract v1](../moc_contract/README.md)**
  REST surface is stateless in front of a shared store — run N replicas behind a
  load balancer; scale the store independently.
- **Standards & interop.** REST (OpenAPI 3.1) + an MCP binding + a JSON-Schema
  conformance suite mean any language or framework integrates the same way, and
  multiple implementations can claim `MoC API v1 Compatible`.
- **Lifecycle & governance controls.** `importance` and `ttl` manage what's
  durable vs. ephemeral; scoped writes + the planned approval/audit plane give
  enterprises the controls real deployments need.
- **Cost control.** Token-budgeted packs cut prompt size (and spend) per call,
  while routing keeps recall high — exactly where large models waste the most.

> In short: keep your vector DB for scale, and put Matrix Context's typed,
> inspectable, budgeted recall in front of it — through the SDK, REST, or MCP.

## Run it all

```bash
pip install matrix-context
python tutorials/integrations/mc_ingest.py        # core: download + ingest + query
pip install langchain-core && python tutorials/integrations/langchain_demo.py
pip install langgraph     && python tutorials/integrations/langgraph_demo.py
pip install crewai        && python tutorials/integrations/crewai_demo.py
```

New to the basics first? Start with
**[Build your first chatbot](build-your-first-chatbot.md)**.
