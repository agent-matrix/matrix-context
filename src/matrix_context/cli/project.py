"""Project configuration for the ``mc`` / ``matrix-context`` CLI.

A *project* is any directory containing a ``.matrix-context/`` folder with:

    .matrix-context/
      matrix-context.db      the local SQLite store
      matrix-context.yaml    a tiny flat ``key: value`` config (no PyYAML needed)

``mc init`` creates it; every other command discovers it by walking up from the
current working directory. An explicit ``--db`` always overrides discovery, and
when there is no project at all the commands fall back to ``matrix-context.db``
in the current directory (backward compatible with the original CLI).

The config parser is intentionally a one-line-per-key flat reader so the core
package keeps its numpy-only dependency footprint (no PyYAML at runtime).
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

PROJECT_DIR = ".matrix-context"
CONFIG_NAME = "matrix-context.yaml"
LEGACY_DB = "matrix-context.db"  # cwd fallback when no project exists

DEFAULTS: dict[str, str] = {
    "name": "default",
    "db": "default.db",
    "embedder": "hashing",
    "scope": "/",
    "max_tokens": "600",
    "top_experts": "2",
}


def _db_for(name: str) -> str:
    """Store filename for a named project — matches ``mc.open(name)`` exactly."""
    return f"{name or 'default'}.db"


def _parse_flat_yaml(text: str) -> dict[str, str]:
    """Parse ``key: value`` lines, ignoring blanks and ``#`` comments."""
    out: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        key, value = line.split(":", 1)
        out[key.strip()] = value.strip().strip('"').strip("'")
    return out


def _dump_flat_yaml(cfg: dict[str, str]) -> str:
    header = ("# Matrix Context project configuration.\n"
              "# Created by `mc init`. Edit freely; one `key: value` per line.\n")
    return header + "".join(f"{k}: {v}\n" for k, v in cfg.items())


@dataclass
class Project:
    """Resolved project: where the store lives and the active configuration."""

    root: Path           # directory holding .matrix-context/ (or cwd if none)
    db: Path             # resolved SQLite path
    config: dict[str, str]
    discovered: bool     # True when a .matrix-context/ was found

    @property
    def name(self) -> str:
        return self.config.get("name", "default")

    @property
    def scope(self) -> str:
        return self.config.get("scope", "/") or "/"

    @property
    def embedder(self) -> str:
        return self.config.get("embedder", "hashing") or "hashing"

    def _int(self, key: str, default: int) -> int:
        try:
            return int(self.config.get(key, str(default)))
        except (TypeError, ValueError):
            return default

    @property
    def max_tokens(self) -> int:
        return self._int("max_tokens", 600)

    @property
    def top_experts(self) -> int:
        return self._int("top_experts", 2)


def find_root(start: Optional[Path] = None) -> Optional[Path]:
    """Walk up from ``start`` (default cwd) for a directory with ``.matrix-context/``."""
    cur = (start or Path.cwd()).resolve()
    for d in (cur, *cur.parents):
        if (d / PROJECT_DIR).is_dir():
            return d
    return None


def load(db_override: Optional[str] = None) -> Project:
    """Resolve the active project for the current working directory."""
    root = find_root()
    if root is not None:
        pdir = root / PROJECT_DIR
        cfg = DEFAULTS.copy()
        cfgf = pdir / CONFIG_NAME
        if cfgf.exists():
            cfg.update(_parse_flat_yaml(cfgf.read_text(encoding="utf-8")))
        db = Path(db_override) if db_override else pdir / cfg.get("db", _db_for(cfg["name"]))
        return Project(root, db, cfg, discovered=True)
    # No project: backward-compatible defaults rooted at the current directory.
    db = Path(db_override) if db_override else Path(LEGACY_DB)
    return Project(Path.cwd(), db, DEFAULTS.copy(), discovered=False)


def init(name: Optional[str] = None, root: Optional[Path] = None) -> Project:
    """Create (or update) ``.matrix-context/`` in ``root`` (default cwd)."""
    root = (root or Path.cwd()).resolve()
    pdir = root / PROJECT_DIR
    pdir.mkdir(parents=True, exist_ok=True)
    cfg = DEFAULTS.copy()
    cfgf = pdir / CONFIG_NAME
    if cfgf.exists():  # preserve any user edits, only override the name
        cfg.update(_parse_flat_yaml(cfgf.read_text(encoding="utf-8")))
    if name:
        cfg["name"] = name
    cfg["db"] = _db_for(cfg["name"])
    cfgf.write_text(_dump_flat_yaml(cfg), encoding="utf-8")
    return Project(root, pdir / cfg["db"], cfg, discovered=True)
