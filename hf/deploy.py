"""Publish the Matrix Context Console to a Hugging Face Docker Space.

Single source of truth: ``frontend/`` (UI + launcher) and ``src/`` (backend).
This assembles the Space build context — the ``hf/`` Dockerfile + card plus
``pyproject.toml`` + ``src/`` + ``frontend/`` — and uploads it. The frontend is
NOT duplicated in the repo; it is included at deploy time.

Usage (token via env; never commit it):
    HF_TOKEN=...  python hf/deploy.py --repo ruslanmv/matrix-context-console [--private]

Used by .github/workflows/deploy-hf-space.yml (reads the HF_TOKEN secret).
"""
from __future__ import annotations

import argparse
import os
import shutil
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HF = ROOT / "hf"
_IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", "*.db", "*.matrix-context.db")


def stage(dst: Path) -> Path:
    """Build the Space context: Dockerfile + card + pyproject + src + frontend."""
    dst.mkdir(parents=True, exist_ok=True)
    shutil.copy2(HF / "Dockerfile", dst / "Dockerfile")
    shutil.copy2(HF / "README.md", dst / "README.md")        # the HF Space card
    shutil.copy2(HF / ".dockerignore", dst / ".dockerignore")
    shutil.copy2(ROOT / "pyproject.toml", dst / "pyproject.toml")
    shutil.copytree(ROOT / "src", dst / "src", dirs_exist_ok=True, ignore=_IGNORE)
    shutil.copytree(ROOT / "frontend", dst / "frontend", dirs_exist_ok=True, ignore=_IGNORE)
    return dst


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Deploy the Matrix Context Console to HF Spaces")
    ap.add_argument("--repo", required=True, help="e.g. ruslanmv/matrix-context-console")
    ap.add_argument("--private", action="store_true", help="create a private Space")
    args = ap.parse_args(argv)

    token = os.environ.get("HF_TOKEN")
    if not token:
        print("HF_TOKEN not set — skipping deploy."); return 0

    from huggingface_hub import HfApi
    api = HfApi(token=token)
    api.create_repo(args.repo, repo_type="space", space_sdk="docker",
                    private=args.private, exist_ok=True, token=token)
    with tempfile.TemporaryDirectory() as tmp:
        ctx = stage(Path(tmp) / "space")
        api.upload_folder(repo_id=args.repo, repo_type="space", folder_path=str(ctx),
                          token=token, commit_message="Deploy Matrix Context Console",
                          ignore_patterns=["__pycache__/*", "*.pyc"])
    print(f"Space: https://huggingface.co/spaces/{args.repo}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
