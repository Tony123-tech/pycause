"""Level 5: SQLite-backed provenance store.

Stores the Caused DAG in SQLite and loads it back by content hash.
Two nodes with the same structural shape share a row, because we key
on content_hash(). If you want per-instance identity instead, swap
content_hash() for id(self) and store the timestamp on the row.
"""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Self

from .core import Caused

_SCHEMA = """
CREATE TABLE IF NOT EXISTS nodes (
    hash TEXT PRIMARY KEY,
    value_json TEXT NOT NULL,
    op TEXT,
    parents_json TEXT NOT NULL,
    timestamp_ns INTEGER NOT NULL,
    created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_op ON nodes(op);
CREATE INDEX IF NOT EXISTS idx_created ON nodes(created_at);
"""


def _serialize_value(v: Any) -> str:
    return json.dumps(v, default=repr, sort_keys=True)


def _deserialize_value(s: str) -> Any:
    return json.loads(s)


class ProvenanceStore:
    """SQLite store for Caused DAGs.

    Usage:
        with ProvenanceStore("provenance.db") as store:
            x = Caused(10)
            y = x * 2 + 3
            root_hash = store.save(y)
            loaded = store.load(root_hash)
            assert loaded.same_as(y)
    """

    def __init__(self, path: str | Path = ":memory:") -> None:
        self._path = str(path)
        self._conn = sqlite3.connect(self._path)
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def save(self, node: Caused) -> str:
        """Persist the whole DAG, return the root hash."""
        seen: set[int] = set()

        def _save(n: Caused) -> str:
            h = n.content_hash()
            if id(n) in seen:
                return h
            seen.add(id(n))
            for p in n.parents:
                if isinstance(p, Caused):
                    _save(p)
            parent_hashes = [
                p.content_hash() if isinstance(p, Caused) else None for p in n.parents
            ]
            parent_raw = [None if isinstance(p, Caused) else p for p in n.parents]
            self._conn.execute(
                "INSERT OR REPLACE INTO nodes "
                "(hash, value_json, op, parents_json, timestamp_ns, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    h,
                    _serialize_value(n.value),
                    n.op,
                    json.dumps(
                        {"hashes": parent_hashes, "raw": parent_raw},
                        default=repr,
                        sort_keys=True,
                    ),
                    n.timestamp,
                    time.time(),
                ),
            )
            return h

        root_hash = _save(node)
        self._conn.commit()
        return root_hash

    def load(self, h: str, _memo: dict[str, Caused] | None = None) -> Caused | None:
        """Load a Caused tree by its root hash. Returns None if not found."""
        if _memo is None:
            _memo = {}
        if h in _memo:
            return _memo[h]
        row = self._conn.execute(
            "SELECT value_json, op, parents_json, timestamp_ns "
            "FROM nodes WHERE hash = ?",
            (h,),
        ).fetchone()
        if row is None:
            return None
        value_json, op, parents_json, timestamp_ns = row
        value = _deserialize_value(value_json)
        parent_info = json.loads(parents_json)
        parent_hashes = parent_info.get("hashes", [])
        parent_raw = parent_info.get("raw", [])
        parents: list[Any] = []
        for i, ph in enumerate(parent_hashes):
            if ph is not None:
                child = self.load(ph, _memo)
                if child is not None:
                    parents.append(child)
                else:
                    parents.append(parent_raw[i] if i < len(parent_raw) else None)
            else:
                parents.append(parent_raw[i] if i < len(parent_raw) else None)
        node = Caused(value, parents, op, timestamp=timestamp_ns)
        _memo[h] = node
        return node

    def has(self, h: str) -> bool:
        row = self._conn.execute(
            "SELECT 1 FROM nodes WHERE hash = ? LIMIT 1", (h,)
        ).fetchone()
        return row is not None

    def count(self) -> int:
        row = self._conn.execute("SELECT COUNT(*) FROM nodes").fetchone()
        return int(row[0])

    def find_by_op(self, op: str) -> list[tuple[str, str]]:
        """Return (hash, value_json) pairs for nodes with the given op."""
        rows = self._conn.execute(
            "SELECT hash, value_json FROM nodes WHERE op = ?", (op,)
        ).fetchall()
        return [(r[0], r[1]) for r in rows]

    def delete(self, h: str) -> None:
        self._conn.execute("DELETE FROM nodes WHERE hash = ?", (h,))
        self._conn.commit()

    def all_hashes(self) -> list[str]:
        rows = self._conn.execute("SELECT hash FROM nodes").fetchall()
        return [r[0] for r in rows]
