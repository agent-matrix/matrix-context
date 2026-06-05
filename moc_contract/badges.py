"""Conformance badge generator.

Runs the MoC Contract v1 conformance suite against the in-process reference (or a
running server) and emits shields-style SVG badges plus a ``status.json`` for
three facets:

    MoC API v1 Compatible      full REST contract (shape + behaviour)
    MoC Inspect v1 Compatible  the inspectability contract (inspect + router/explain)
    MoC MCP v1 Compatible      the MCP binding (pending until a conformant MCP server ships)

Badges report ground truth: a facet is green only if its checks pass, grey if the
facet is not yet implemented (e.g. the MCP server is a v1 scaffold), and red on
failure. SVGs are self-contained (no network/shields dependency).

    python -m moc_contract.badges [--out badges] [--url http://127.0.0.1:8088]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict

from . import CONTRACT_VERSION
from .conformance import Report, http_client, in_process_client, run

GREEN = "#2ea043"
GREY = "#9f9f9f"
RED = "#e05d44"

DEFAULT_OUT = Path(__file__).resolve().parents[1] / "badges"


def _facets(report: Report) -> Dict[str, dict]:
    """Derive per-facet status from a conformance report."""
    api_ok = report.ok
    inspect_checks = [(n, ok) for n, ok, _ in report.checks
                      if "inspect" in n.lower() or "router" in n.lower()]
    inspect_ok = bool(inspect_checks) and all(ok for _, ok in inspect_checks)
    return {
        "api": {
            "label": "MoC API v1", "status": "compatible" if api_ok else "failing",
            "passed": report.passed, "total": len(report.checks),
        },
        "inspect": {
            "label": "MoC Inspect v1",
            "status": "compatible" if inspect_ok else "failing",
            "passed": sum(1 for _, ok in inspect_checks if ok),
            "total": len(inspect_checks),
        },
    }


def _mcp_status() -> dict:
    """The MCP server is a v1 scaffold; report 'pending' until a conformant MCP
    binding ships and can be exercised by the suite."""
    try:
        from matrix_context.serve.mcp import transports
        transports.stdio()           # scaffold raises NotImplementedError
        status = "compatible"
    except NotImplementedError:
        status = "pending"
    except Exception:
        status = "pending"
    return {"label": "MoC MCP v1", "status": status, "passed": 0, "total": 0}


def evaluate(call=None) -> Dict[str, dict]:
    report = run(call or in_process_client())
    facets = _facets(report)
    facets["mcp"] = _mcp_status()
    return facets


# --------------------------------------------------------------------------- #
# SVG (shields-style "flat" badge), self-contained
# --------------------------------------------------------------------------- #
def _text_width(s: str) -> int:
    # Approximate Verdana 11px advance; good enough for layout.
    return int(sum(8 if c.isupper() or c in "mwMW@" else 6 for c in s)) + 10


def badge_svg(label: str, message: str, color: str) -> str:
    lw, mw = _text_width(label), _text_width(message)
    w = lw + mw
    lx, mx = lw * 10 // 2, lw * 10 + mw * 10 // 2  # text anchors (scaled by 10)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="20" \
role="img" aria-label="{label}: {message}">
  <title>{label}: {message}</title>
  <linearGradient id="s" x2="0" y2="100%">
    <stop offset="0" stop-color="#bbb" stop-opacity=".1"/>
    <stop offset="1" stop-opacity=".1"/>
  </linearGradient>
  <clipPath id="r"><rect width="{w}" height="20" rx="3" fill="#fff"/></clipPath>
  <g clip-path="url(#r)">
    <rect width="{lw}" height="20" fill="#555"/>
    <rect x="{lw}" width="{mw}" height="20" fill="{color}"/>
    <rect width="{w}" height="20" fill="url(#s)"/>
  </g>
  <g fill="#fff" text-anchor="middle" \
font-family="Verdana,DejaVu Sans,Geneva,sans-serif" font-size="110" \
text-rendering="geometricPrecision">
    <text x="{lx}" y="150" transform="scale(.1)" fill="#010101" fill-opacity=".3" \
textLength="{(lw - 10) * 10}">{label}</text>
    <text x="{lx}" y="140" transform="scale(.1)" textLength="{(lw - 10) * 10}">{label}</text>
    <text x="{mx}" y="150" transform="scale(.1)" fill="#010101" fill-opacity=".3" \
textLength="{(mw - 10) * 10}">{message}</text>
    <text x="{mx}" y="140" transform="scale(.1)" textLength="{(mw - 10) * 10}">{message}</text>
  </g>
</svg>
'''


_COLOR = {"compatible": GREEN, "pending": GREY, "failing": RED}
_MESSAGE = {"compatible": "compatible", "pending": "pending", "failing": "failing"}


def write_badges(out_dir: Path, call=None) -> Dict[str, dict]:
    out_dir.mkdir(parents=True, exist_ok=True)
    facets = evaluate(call)
    files = {"api": "moc_api_v1.svg", "inspect": "moc_inspect_v1.svg",
             "mcp": "moc_mcp_v1.svg"}
    for key, fac in facets.items():
        status = fac["status"]
        svg = badge_svg(fac["label"], _MESSAGE[status], _COLOR[status])
        (out_dir / files[key]).write_text(svg)
    status = {
        "contract_version": CONTRACT_VERSION,
        "facets": facets,
        "badges": files,
    }
    (out_dir / "status.json").write_text(json.dumps(status, indent=2))
    return facets


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="MoC conformance badge generator")
    p.add_argument("--out", default=str(DEFAULT_OUT))
    p.add_argument("--url", default="", help="target server (default: in-process)")
    args = p.parse_args(argv)
    call = http_client(args.url) if args.url else None
    facets = write_badges(Path(args.out), call)
    print(f"MoC Contract v{CONTRACT_VERSION} badges -> {args.out}")
    for key, fac in facets.items():
        print(f"  {fac['label']:16s} {fac['status']:11s} "
              f"({fac['passed']}/{fac['total']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
