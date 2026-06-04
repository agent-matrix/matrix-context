"""Optional answer generator + judge using a small local Ollama model."""
from __future__ import annotations


def get_generator(name: str):
    if name in ("none", "", None):
        return None
    if name == "ollama":
        return OllamaGenerator()
    raise ValueError(f"unknown generator: {name}")


class OllamaGenerator:
    def __init__(self, model: str = "llama3.2:1b"):
        import ollama  # lazy
        self._ollama = ollama
        self.model = model

    def answer(self, query: str, context: str) -> str:
        prompt = (f"Use ONLY the context to answer in one short sentence.\n\n"
                  f"Context:\n{context}\n\nQuestion: {query}\nAnswer:")
        r = self._ollama.generate(model=self.model, prompt=prompt)
        return r["response"].strip()

    def judge(self, query: str, gold: str, answer: str) -> bool:
        prompt = (f"Question: {query}\nReference answer: {gold}\nModel answer: {answer}\n"
                  f"Is the model answer correct and consistent with the reference? "
                  f"Reply with only YES or NO.")
        r = self._ollama.generate(model=self.model, prompt=prompt)
        return r["response"].strip().upper().startswith("Y")
