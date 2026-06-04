"""Push the benchmark dataset and result artifacts to the Hugging Face Hub.

Requires ``huggingface_hub`` (lazy import) and a token in the environment
(`HF_TOKEN`) or a prior `huggingface-cli login`. Kept thin and side-effect free
on import so the rest of the package stays dependency-light.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional


def _api():
    try:
        from huggingface_hub import HfApi
    except ImportError as e:  # pragma: no cover
        raise ImportError(
            "Install huggingface_hub to push: pip install huggingface_hub") from e
    return HfApi()


def push_dataset(repo_id: str, data_dir: Path, private: bool = False,
                 token: Optional[str] = None) -> str:  # pragma: no cover - network
    """Upload the generated dataset folder (jsonl + dataset card) as a dataset repo."""
    from .hf_card import write_card

    data_dir = Path(data_dir)
    infos = json.loads((data_dir / "dataset_infos.json").read_text()) \
        if (data_dir / "dataset_infos.json").exists() else {}
    write_card(data_dir / "README.md", infos.get("counts", {}))

    api = _api()
    api.create_repo(repo_id, repo_type="dataset", private=private,
                    exist_ok=True, token=token)
    api.upload_folder(repo_id=repo_id, repo_type="dataset", folder_path=str(data_dir),
                      token=token, ignore_patterns=["__pycache__/*"])
    return f"https://huggingface.co/datasets/{repo_id}"


def push_results(repo_id: str, results_path: str,
                 token: Optional[str] = None) -> str:  # pragma: no cover - network
    """Upload a results JSON (or a directory of them) under ``results/`` in the
    dataset repo."""
    api = _api()
    api.create_repo(repo_id, repo_type="dataset", exist_ok=True, token=token)
    path = Path(results_path)
    if path.is_dir():
        api.upload_folder(repo_id=repo_id, repo_type="dataset", folder_path=str(path),
                          path_in_repo="results", token=token,
                          ignore_patterns=["__pycache__/*"])
    else:
        api.upload_file(repo_id=repo_id, repo_type="dataset", path_or_fileobj=str(path),
                        path_in_repo=f"results/{path.name}", token=token)
    return f"https://huggingface.co/datasets/{repo_id}"
