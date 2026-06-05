"""CrewAI × Matrix Context.

Expose Matrix Context as a CrewAI **tool** so any agent in a crew can recall
routed, budgeted, inspectable memory. The tool wraps a single call —
``build_pack`` — and returns prompt-ready context.

    pip install matrix-context crewai
    python tutorials/integrations/crewai_demo.py
"""
from __future__ import annotations

from mc_ingest import SCOPE, build_context, retrieve

CTX = build_context()


def _make_tool():
    """Build a CrewAI tool, or return None if CrewAI is not installed."""
    try:
        from crewai.tools import BaseTool
        from pydantic import BaseModel, Field
    except Exception:
        return None

    class _Args(BaseModel):
        query: str = Field(..., description="What to recall from memory.")

    class MatrixContextTool(BaseTool):
        name: str = "matrix_context_recall"
        description: str = ("Recall the most relevant, typed memory for a query "
                            "(routed + budgeted + inspectable).")
        args_schema: type = _Args

        def _run(self, query: str) -> str:
            return retrieve(CTX, query, max_tokens=400, scope=SCOPE)

    return MatrixContextTool()


def main() -> None:
    tool = _make_tool()
    if tool is None:
        print("CrewAI is not installed. `pip install crewai` to run the full crew.\n"
              "Meanwhile, here is exactly what the tool returns to an agent:\n")
        print(retrieve(CTX, "What license is PostgreSQL released under?", max_tokens=300))
        return

    # The recall tool works standalone (no LLM key needed):
    print("Tool output:\n" + tool.run("What license is PostgreSQL released under?")[:500])

    # --- Full crew (needs an LLM key, e.g. OPENAI_API_KEY) ------------------
    # from crewai import Agent, Task, Crew
    # analyst = Agent(role="DB analyst", goal="Answer from project memory",
    #                 backstory="Uses Matrix Context to recall facts.",
    #                 tools=[tool], verbose=True)
    # task = Task(description="What license is PostgreSQL under?",
    #             expected_output="A one-sentence answer.", agent=analyst)
    # print(Crew(agents=[analyst], tasks=[task]).kickoff())


if __name__ == "__main__":
    main()
