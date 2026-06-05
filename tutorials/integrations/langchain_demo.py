"""LangChain × Matrix Context.

Wrap Matrix Context as a LangChain **Retriever** so any LCEL chain or agent can
pull routed, budgeted, inspectable memory. The retriever returns the same items
``build_pack`` selects — as LangChain ``Document`` objects.

    pip install matrix-context langchain-core
    python tutorials/integrations/langchain_demo.py
"""
from __future__ import annotations

from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from pydantic import ConfigDict

from mc_ingest import SCOPE, build_context


class MatrixContextRetriever(BaseRetriever):
    """A LangChain retriever backed by Matrix Context's routed recall."""

    model_config = ConfigDict(arbitrary_types_allowed=True)
    ctx: object                 # a matrix_context.ContextManager
    scope: str = "/"
    max_tokens: int = 400

    def _get_relevant_documents(self, query, *, run_manager=None) -> list[Document]:
        pack = self.ctx.build_pack(query, scope=self.scope, max_tokens=self.max_tokens)
        return [Document(page_content=p.item.content,
                         metadata={"expert": p.item.expert, "score": p.final_score})
                for p in pack.items]


def main() -> None:
    ctx = build_context()
    retriever = MatrixContextRetriever(ctx=ctx, scope=SCOPE, max_tokens=300)

    query = "What license is PostgreSQL released under?"
    docs = retriever.invoke(query)               # standard LangChain interface
    print(f"Q: {query}\nMatrix Context returned {len(docs)} documents:")
    for d in docs:
        print(f"  [{d.metadata['expert']}] {d.page_content[:110]}…")

    # --- Optional: a full RAG chain with an LLM (needs a key) ---------------
    # from langchain_openai import ChatOpenAI            # pip install langchain-openai
    # from langchain_core.prompts import ChatPromptTemplate
    # from langchain_core.runnables import RunnablePassthrough
    # from langchain_core.output_parsers import StrOutputParser
    # prompt = ChatPromptTemplate.from_template(
    #     "Answer using only this context:\n{context}\n\nQuestion: {question}")
    # chain = ({"context": retriever | (lambda ds: "\n".join(d.page_content for d in ds)),
    #           "question": RunnablePassthrough()}
    #          | prompt | ChatOpenAI(model="gpt-4o-mini") | StrOutputParser())
    # print("\nAnswer:", chain.invoke(query))


if __name__ == "__main__":
    main()
