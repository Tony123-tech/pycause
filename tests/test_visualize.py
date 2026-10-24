import json

from pycause.core import Caused
from pycause.visualize import (
    to_dot,
    to_html,
    to_json_graph,
    to_mermaid,
)


def _simple_expr():
    x = Caused(10)
    y = x - 5
    z = y * 2
    return z


def test_to_dot_contains_nodes():
    z = _simple_expr()
    dot = to_dot(z)
    assert "digraph Caused" in dot
    assert "10" in dot
    assert "5" in dot
    assert "2" in dot


def test_to_dot_contains_edges():
    z = _simple_expr()
    dot = to_dot(z)
    assert "->" in dot


def test_to_dot_leaf_has_box_shape():
    x = Caused(42)
    dot = to_dot(x)
    assert "shape=box" in dot


def test_to_dot_no_cycle_hang():
    x = Caused(5)
    y = x * x
    dot = to_dot(y)
    assert dot.count("->") == 2


def test_to_mermaid_starts_with_graph():
    z = _simple_expr()
    m = to_mermaid(z)
    assert m.startswith("graph LR")


def test_to_mermaid_contains_arrows():
    z = _simple_expr()
    m = to_mermaid(z)
    assert "-->" in m


def test_to_json_graph_is_valid_json():
    z = _simple_expr()
    s = to_json_graph(z)
    data = json.loads(s)
    assert "nodes" in data
    assert "edges" in data


def test_to_json_graph_node_count():
    z = _simple_expr()
    data = json.loads(to_json_graph(z))
    assert len(data["nodes"]) == 5


def test_to_json_graph_edge_count():
    z = _simple_expr()
    data = json.loads(to_json_graph(z))
    assert len(data["edges"]) == 4


def test_to_json_graph_leaf_flag():
    x = Caused(7)
    data = json.loads(to_json_graph(x))
    assert data["nodes"][0]["is_leaf"] is True


def test_to_json_graph_internal_node_flag():
    z = _simple_expr()
    data = json.loads(to_json_graph(z))
    internal = [n for n in data["nodes"] if not n["is_leaf"]]
    assert len(internal) == 2


def test_to_json_graph_content_hash_mode():
    z = _simple_expr()
    data = json.loads(to_json_graph(z, use_content_hash=True))
    caused_nodes = [n for n in data["nodes"] if n["kind"] == "caused"]
    for n in caused_nodes:
        assert "content_hash" in n
        assert len(n["content_hash"]) == 64


def test_to_html_is_self_contained():
    z = _simple_expr()
    html = to_html(z)
    assert "<!DOCTYPE html>" in html
    assert "vis-network" in html
    assert "vis.DataSet" in html


def test_to_html_embeds_json():
    z = _simple_expr()
    html = to_html(z)
    assert '"nodes"' in html
    assert '"edges"' in html


def test_shared_node_appears_once():
    x = Caused(5)
    y = x * x
    data = json.loads(to_json_graph(y))
    leaf_count = sum(1 for n in data["nodes"] if n["is_leaf"] and n["kind"] == "caused")
    assert leaf_count == 1
