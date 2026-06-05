"""Publish the MoC-RAG Benchmark leaderboard to a Hugging Face Gradio Space.

Single source of truth: ``benchmarks/moc_rag_benchmark/space/`` (the Gradio
``app.py`` + Space card + bundled result artifacts under ``space/results/``).
The Space is self-contained — it reads the bundled JSON, so it needs no dataset
access or token at runtime.

Token via env (never commit it):

    HF_TOKEN=...  python -m benchmarks.moc_rag_benchmark.deploy_space \
        --repo ruslanmv/moc-rag-leaderboard [--private]

Used by ``.github/workflows/deploy-benchmark-space.yml`` (reads the HF_TOKEN
repository secret). Without HF_TOKEN the deploy no-ops so CI stays green on forks.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path

SPACE = Path(__file__).resolve().parent / "space"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Deploy the MoC-RAG leaderboard to HF Spaces")
    ap.add_argument("--repo", required=True, help="e.g. ruslanmv/moc-rag-leaderboard")
    ap.add_argument("--private", action="store_true", help="create/keep the Space private")
    args = ap.parse_args(argv)

    token = os.environ.get("HF_TOKEN")
    if not token:
        print("HF_TOKEN not set — skipping deploy.")
        return 0

    from huggingface_hub import HfApi
    api = HfApi(token=token)
    api.create_repo(args.repo, repo_type="space", space_sdk="gradio",
                    private=args.private, exist_ok=True, token=token)
    if args.private:
        # Keep visibility in sync when re-deploying an existing Space.
        api.update_repo_settings(args.repo, repo_type="space", private=True, token=token)
    api.upload_folder(repo_id=args.repo, repo_type="space", folder_path=str(SPACE),
                      token=token, commit_message="Deploy MoC-RAG benchmark leaderboard",
                      ignore_patterns=["__pycache__/*", "*.pyc"])
    print(f"Space: https://huggingface.co/spaces/{args.repo}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
