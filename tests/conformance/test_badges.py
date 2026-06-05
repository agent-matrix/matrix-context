"""Conformance badge generator: facets reflect ground truth, SVGs are valid."""
import xml.dom.minidom as minidom

import pytest

pytest.importorskip("jsonschema")

from moc_contract.badges import badge_svg, evaluate, write_badges  # noqa: E402


def test_facets_reflect_reference_status():
    facets = evaluate()
    # The reference REST server is API + Inspect compatible...
    assert facets["api"]["status"] == "compatible"
    assert facets["api"]["passed"] == facets["api"]["total"] >= 30
    assert facets["inspect"]["status"] == "compatible"
    # ...and MCP is honestly pending (the MCP server is a v1 scaffold).
    assert facets["mcp"]["status"] == "pending"


def test_badge_svg_is_wellformed_and_labelled():
    svg = badge_svg("MoC API v1", "compatible", "#2ea043")
    minidom.parseString(svg)                 # raises if malformed XML
    assert "MoC API v1" in svg and "compatible" in svg
    assert svg.startswith("<svg")


def test_write_badges_emits_three_svgs_and_status(tmp_path):
    facets = write_badges(tmp_path)
    for name in ("moc_api_v1.svg", "moc_inspect_v1.svg", "moc_mcp_v1.svg"):
        assert (tmp_path / name).exists()
        minidom.parse(str(tmp_path / name))
    status = (tmp_path / "status.json")
    assert status.exists()
    assert set(facets) == {"api", "inspect", "mcp"}
