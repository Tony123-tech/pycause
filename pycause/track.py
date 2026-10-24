"""Level 3 lightweight: @track decorator.

Records the input Caused objects and the returned Caused object for
each function call. It does not intercept execution, so local variable
flow inside the function is not captured. The returned Caused tree
already encodes the arithmetic that produced it, so input/output
provenance is sufficient for most practical purposes.

If you need full intra-function tracking later, this is the place to
swap in sys.settrace or an AST rewrite. The TrackedCall shape is
designed to stay compatible with either implementation.
"""

from __future__ import annotations

import functools
import inspect
from collections.abc import Callable
from typing import Any

from .core import Caused


class TrackedCall:
    """One invocation of a tracked function."""

    __slots__ = ("args", "error", "func_name", "kwargs", "result")

    def __init__(
        self,
        func_name: str,
        args: tuple,
        kwargs: dict,
        result: Any,
        error: BaseException | None = None,
    ) -> None:
        self.func_name = func_name
        self.args = args
        self.kwargs = kwargs
        self.result = result
        self.error = error

    def input_causeds(self) -> list[Caused]:
        """Return every Caused found in args or kwargs, deduplicated."""
        seen: set[int] = set()
        out: list[Caused] = []

        def _collect(obj: Any) -> None:
            if isinstance(obj, Caused):
                if id(obj) not in seen:
                    seen.add(id(obj))
                    out.append(obj)
                return
            if isinstance(obj, (list, tuple, set)):
                for item in obj:
                    _collect(item)
                return
            if isinstance(obj, dict):
                for v in obj.values():
                    _collect(v)

        for a in self.args:
            _collect(a)
        for v in self.kwargs.values():
            _collect(v)
        return out

    def dependency_roots(self) -> list[Caused]:
        """Return the leaf Caused objects that the result depends on."""
        if not isinstance(self.result, Caused):
            return []
        seen: set[int] = set()
        out: list[Caused] = []

        def _walk(node: Caused) -> None:
            if id(node) in seen:
                return
            seen.add(id(node))
            if not node.parents:
                out.append(node)
                return
            for p in node.parents:
                if isinstance(p, Caused):
                    _walk(p)

        _walk(self.result)
        return out

    def explain_deps(self, lang: str | None = None) -> str:
        """Describe the dependency roots in plain text."""
        if self.error is not None:
            return f"{self.func_name} raised {type(self.error).__name__}"
        if not isinstance(self.result, Caused):
            return (
                f"{self.func_name} returned {type(self.result).__name__}, no provenance"
            )
        roots = self.dependency_roots()
        if not roots:
            return f"{self.func_name} returned a constant, no dependencies"
        parts = [f"Caused({r.value!r})" for r in roots]
        return f"{self.func_name} depends on {len(roots)} root(s): {', '.join(parts)}"

    def __repr__(self) -> str:
        return f"TrackedCall({self.func_name!r}, result={self.result!r})"


def track(func: Callable) -> Callable:
    """Decorator that records input/output provenance for a function.

    Usage:
        @track
        def f(x, y):
            return x * y + 3

        a = Caused(2)
        b = Caused(5)
        c = f(a, b)
        c.why()
        f.last_call.explain_deps()
    """
    if not callable(func):
        raise TypeError(f"@track expects a callable, got {type(func).__name__}")

    sig = inspect.signature(func)

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()
            call_args = bound.args
            call_kwargs = bound.kwargs
        except TypeError:
            call_args = args
            call_kwargs = kwargs

        try:
            result = func(*args, **kwargs)
        except BaseException as e:
            wrapper.last_call = TrackedCall(  # type: ignore[attr-defined]
                func.__name__, call_args, call_kwargs, None, e
            )
            raise

        wrapper.last_call = TrackedCall(  # type: ignore[attr-defined]
            func.__name__, call_args, call_kwargs, result
        )
        return result

    wrapper.last_call = None  # type: ignore[attr-defined]
    return wrapper
