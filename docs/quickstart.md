# Quickstart

```bash
pip install "matrix-context[embeddings]"
```
```python
from matrix_context import ContextManager
ctx = ContextManager.create("my-agent")
ctx.remember("The user prefers local-first tools", expert="profile", importance=0.9)
print(ctx.build_pack("what does the user like?", max_tokens=200).to_prompt())
print(ctx.inspect("what does the user like?"))
```
