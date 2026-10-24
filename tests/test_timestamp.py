import copy
import pickle
import time

from pycause.core import Caused


def test_timestamp_default():
    before = time.time_ns()
    x = Caused(10)
    after = time.time_ns()
    assert before <= x.timestamp <= after


def test_timestamp_explicit():
    x = Caused(10, timestamp=12345)
    assert x.timestamp == 12345


def test_timestamp_monotonic_on_ops():
    x = Caused(1)
    time.sleep(0.001)
    y = x + 1
    assert y.timestamp >= x.timestamp


def test_timestamp_in_to_dict():
    x = Caused(5, timestamp=999)
    d = x.to_dict()
    assert d["timestamp"] == 999


def test_from_dict_roundtrip_preserves_timestamp():
    x = Caused(5, timestamp=999)
    d = x.to_dict()
    y = Caused.from_dict(d)
    assert y.timestamp == 999


def test_content_hash_ignores_timestamp():
    a = Caused(5, timestamp=1)
    b = Caused(5, timestamp=999999)
    assert a.content_hash() == b.content_hash()


def test_pickle_preserves_timestamp():
    x = Caused(42, timestamp=777)
    data = pickle.dumps(x)
    y = pickle.loads(data)
    assert y.timestamp == 777
    assert y.value == 42


def test_deepcopy_preserves_timestamp():
    x = Caused(42, timestamp=777)
    y = copy.deepcopy(x)
    assert y.timestamp == 777
