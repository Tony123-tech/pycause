"""Level 15: Visualization exports.

Turns a Caused DAG into formats suitable for external tools:

- to_dot()        Graphviz DOT (for `dot -Tpng`)
- to_mermaid()    Mermaid JS (for GitHub / Notion / md preview)
- to_json_graph() node-link JSON (for D3.js, vis.js, Cytoscape)
- to_html()       standalone HTML with vis-network

Raw (non-Caused) parents are rendered as synthetic nodes with ids of
the form "raw_<repr>". Two raw values with the same repr collapse into
one node, which matches how you'd read the expression visually.
"""

from __future__ import annotations

import json
from typing import Any

from .core import Caused


def _caused_id(node: Caused, use_content_hash: bool) -> str:
    if use_content_hash:
        return "n_" + node.content_hash()[:16]
    return "n_" + format(id(node), "x")


def _node_id(node: Any, use_content_hash: bool) -> str:
    if isinstance(node, Caused):
        return _caused_id(node, use_content_hash)
    return "raw_" + repr(node)


def _node_label(node: Any) -> str:
    if not isinstance(node, Caused):
        return repr(node)
    if node.op is None:
        return repr(node.value)
    return f"{node.op} = {node.value!r}"


def _collect_graph(
    root: Caused,
    use_content_hash: bool,
) -> tuple[list[Any], list[tuple[Any, Any]]]:
    """Return (nodes, edges) in deterministic traversal order.

    Nodes may be Caused or raw values. Raw values are deduplicated by
    repr, so two literal 2s appear as one node.
    """
    nodes: list[Any] = []
    edges: list[tuple[Any, Any]] = []
    seen_caused: set[Any] = set()
    seen_raw: set[str] = set()

    def _key(n: Any) -> Any:
        if isinstance(n, Caused):
            return n.content_hash() if use_content_hash else id(n)
        return repr(n)

    def _walk(n: Any) -> None:
        k = _key(n)
        if isinstance(n, Caused):
            if k in seen_caused:
                return
            seen_caused.add(k)
        else:
            if k in seen_raw:
                return
            seen_raw.add(k)

        nodes.append(n)
        if isinstance(n, Caused):
            for p in n.parents:
                edges.append((n, p))
                _walk(p)

    _walk(root)
    return nodes, edges


def _escape_dot(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def to_dot(root: Caused, use_content_hash: bool = False) -> str:
    """Export the Caused DAG as a Graphviz DOT string.

    Usage:
        print(to_dot(expr))
        # pipe to: dot -Tpng -o out.png
    """
    nodes, edges = _collect_graph(root, use_content_hash)
    lines = ["digraph Caused {", '  rankdir="LR";']
    for n in nodes:
        nid = _node_id(n, use_content_hash)
        label = _escape_dot(_node_label(n))
        if isinstance(n, Caused) and n.op is not None:
            lines.append(f'  {nid} [label="{label}"];')
        else:
            lines.append(f'  {nid} [label="{label}", shape=box, style=rounded];')
    for child, parent in edges:
        cid = _node_id(child, use_content_hash)
        pid = _node_id(parent, use_content_hash)
        lines.append(f"  {cid} -> {pid};")
    lines.append("}")
    return "\n".join(lines)


def to_mermaid(root: Caused, use_content_hash: bool = False) -> str:
    """Export the Caused DAG as a Mermaid flowchart string.

    Usage:
        print(to_mermaid(expr))
        # paste into any Mermaid-enabled markdown viewer
    """
    nodes, edges = _collect_graph(root, use_content_hash)
    lines = ["graph LR"]
    for n in nodes:
        nid = _node_id(n, use_content_hash)
        label = _node_label(n).replace('"', "#quot;")
        if isinstance(n, Caused) and n.op is not None:
            lines.append(f'  {nid}("{label}")')
        else:
            lines.append(f'  {nid}["{label}"]')
    for child, parent in edges:
        cid = _node_id(child, use_content_hash)
        pid = _node_id(parent, use_content_hash)
        lines.append(f"  {cid} --> {pid}")
    return "\n".join(lines)


def _is_jsonable(v: Any) -> bool:
    try:
        json.dumps(v)
        return True
    except (TypeError, ValueError):
        return False


def to_json_graph(
    root: Caused,
    use_content_hash: bool = False,
    indent: int | None = 2,
) -> str:
    """Export the Caused DAG as node-link JSON (D3.js / Cytoscape compatible)."""
    nodes, edges = _collect_graph(root, use_content_hash)
    node_entries: list[dict[str, Any]] = []
    for n in nodes:
        if isinstance(n, Caused):
            entry: dict[str, Any] = {
                "id": _node_id(n, use_content_hash),
                "value": n.value if _is_jsonable(n.value) else repr(n.value),
                "op": n.op,
                "timestamp": n.timestamp,
                "is_leaf": n.op is None,
                "kind": "caused",
            }
            if use_content_hash:
                entry["content_hash"] = n.content_hash()
        else:
            entry = {
                "id": _node_id(n, use_content_hash),
                "value": n if _is_jsonable(n) else repr(n),
                "op": None,
                "timestamp": None,
                "is_leaf": True,
                "kind": "raw",
            }
        node_entries.append(entry)

    edge_entries: list[dict[str, str]] = []
    for child, parent in edges:
        edge_entries.append(
            {
                "source": _node_id(child, use_content_hash),
                "target": _node_id(parent, use_content_hash),
            }
        )

    graph = {
        "directed": True,
        "multigraph": False,
        "graph": {"root": _node_id(root, use_content_hash)},
        "nodes": node_entries,
        "edges": edge_entries,
    }
    return json.dumps(graph, indent=indent, default=repr)


def to_html(
    root: Caused,
    use_content_hash: bool = False,
    title: str = "Caused Provenance",
) -> str:
    """Export as a standalone HTML page using vis-network."""
    nodes, edges = _collect_graph(root, use_content_hash)
    vis_nodes = []
    for n in nodes:
        label = _node_label(n)
        if isinstance(n, Caused) and n.op is not None:
            color = "#fff3e0"
        else:
            color = "#e0f7fa"
        vis_nodes.append(
            {
                "id": _node_id(n, use_content_hash),
                "label": label,
                "shape": "box",
                "color": color,
            }
        )
    vis_edges = []
    for child, parent in edges:
        vis_edges.append(
            {
                "from": _node_id(child, use_content_hash),
                "to": _node_id(parent, use_content_hash),
                "arrows": "to",
            }
        )
    data_json = json.dumps({"nodes": vis_nodes, "edges": vis_edges}, default=repr)
    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>{title}</title>
  <script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
  <style>
    body {{ margin: 0; font-family: sans-serif; }}
    #net {{ width: 100vw; height: 100vh; border: 0; }}
  </style>
</head>
<body>
  <div id="net"></div>
  <script>
    var data = {data_json};
    var nodes = new vis.DataSet(data.nodes);
    var edges = new vis.DataSet(data.edges);
    var container = document.getElementById('net');
    var options = {{
      layout: {{ direction: 'LR' }},
      physics: {{ stabilization: true }},
      edges: {{ smooth: true }}
    }};
    new vis.Network(container, {{ nodes: nodes, edges: edges }}, options);
  </script>
</body>
</html>"""
