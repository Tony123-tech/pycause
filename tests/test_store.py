from pycause.core import Caused
from pycause.store import ProvenanceStore


def test_save_and_load_roundtrip():
    with ProvenanceStore(":memory:") as store:
        x = Caused(10)
        y = x * 2 + 3
        h = store.save(y)
        loaded = store.load(h)
        assert loaded is not None
        assert loaded.same_as(y)


def test_load_missing_returns_none():
    with ProvenanceStore(":memory:") as store:
        assert store.load("deadbeef") is None


def test_shared_node_stored_once():
    with ProvenanceStore(":memory:") as store:
        x = Caused(5)
        y = x * x
        store.save(y)
        assert store.count() == 2


def test_has_and_delete():
    with ProvenanceStore(":memory:") as store:
        x = Caused(42)
        h = store.save(x)
        assert store.has(h)
        store.delete(h)
        assert not store.has(h)


def test_find_by_op():
    with ProvenanceStore(":memory:") as store:
        x = Caused(3)
        y = x + 4
        store.save(y)
        rows = store.find_by_op("+")
        assert len(rows) == 1


def test_persist_to_file(tmp_path):
    db = tmp_path / "prov.db"
    with ProvenanceStore(db) as store:
        x = Caused(7)
        y = x**2
        h = store.save(y)
    with ProvenanceStore(db) as store:
        loaded = store.load(h)
        assert loaded is not None
        assert loaded.same_as(y)


def test_timestamp_preserved():
    with ProvenanceStore(":memory:") as store:
        x = Caused(9, timestamp=123456)
        h = store.save(x)
        loaded = store.load(h)
        assert loaded is not None
        assert loaded.timestamp == 123456


def test_complex_tree_roundtrip():
    with ProvenanceStore(":memory:") as store:
        a = Caused(2)
        b = Caused(3)
        c = (a + b) * (a - b)
        h = store.save(c)
        loaded = store.load(h)
        assert loaded is not None
        assert loaded.same_as(c)
        assert loaded.evaluate() == c.evaluate()
