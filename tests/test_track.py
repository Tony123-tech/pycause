# pyright: reportFunctionMemberAccess=false

from typing import Any, cast

import pytest

from pycause.core import Caused
from pycause.track import TrackedCall, track


def test_track_records_result():
    @track
    def f(x, y):
        return x * y + 3

    a = Caused(2)
    b = Caused(5)
    c = f(a, b)
    assert isinstance(c, Caused)
    assert c.value == 13
    assert isinstance(f.last_call, TrackedCall)


def test_track_records_inputs():
    @track
    def f(x, y):
        return x + y

    a = Caused(2)
    b = Caused(3)
    f(a, b)
    inputs = f.last_call.input_causeds()
    assert len(inputs) == 2
    assert inputs[0] is a
    assert inputs[1] is b


def test_track_records_dependency_roots():
    @track
    def f(x, y):
        return x * y

    a = Caused(2)
    b = Caused(3)
    f(a, b)
    roots = f.last_call.dependency_roots()
    assert len(roots) == 2


def test_track_explain_deps():
    @track
    def f(x, y):
        return x + y

    a = Caused(1)
    b = Caused(2)
    f(a, b)
    msg = f.last_call.explain_deps()
    assert "depends on 2 root" in msg


def test_track_records_error():
    @track
    def f(x):
        raise ValueError("boom")

    a = Caused(1)
    with pytest.raises(ValueError):
        f(a)
    assert f.last_call.error is not None
    assert isinstance(f.last_call.error, ValueError)


def test_track_non_caused_return():
    @track
    def f(x):
        return x.value * 2

    a = Caused(5)
    result = f(a)
    assert result == 10
    assert f.last_call.dependency_roots() == []


def test_track_with_default_args():
    @track
    def f(x, y=10):
        return x + y

    a = Caused(1)
    f(a)
    inputs = f.last_call.input_causeds()
    assert len(inputs) == 1


def test_track_with_kwargs():
    @track
    def f(x, y):
        return x + y

    a = Caused(1)
    b = Caused(2)
    f(x=a, y=b)
    inputs = f.last_call.input_causeds()
    assert len(inputs) == 2


def test_track_nested_list_arg():
    @track
    def f(pair):
        return pair[0] + pair[1]

    a = Caused(1)
    b = Caused(2)
    f([a, b])
    inputs = f.last_call.input_causeds()
    assert len(inputs) == 2


def test_track_preserves_func_metadata():
    @track
    def my_func(x):
        """Docstring here."""
        return x

    assert my_func.__name__ == "my_func"
    assert my_func.__doc__ == "Docstring here."


def test_track_not_callable():
    with pytest.raises(TypeError):
        track(cast(Any, 42))


def test_track_chain():
    @track
    def add(x, y):
        return x + y

    @track
    def mul(x, y):
        return x * y

    a = Caused(2)
    b = Caused(3)
    c = Caused(4)
    mid = add(a, b)
    result = mul(mid, c)
    roots = mul.last_call.dependency_roots()
    assert len(roots) == 3
    assert result.value == 20


def test_track_no_last_call_initially():
    @track
    def f(x):
        return x

    assert f.last_call is None


def test_track_explain_deps_non_caused():
    @track
    def f(x):
        return x.value + 1

    a = Caused(5)
    f(a)
    msg = f.last_call.explain_deps()
    assert "no provenance" in msg


def test_track_explain_deps_constant():
    @track
    def f(x):
        return Caused(99)

    a = Caused(1)
    f(a)
    msg = f.last_call.explain_deps()
    assert "Caused(99)" in msg
    assert "1 root" in msg
