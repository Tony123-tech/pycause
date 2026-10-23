from __future__ import annotations

import cmath
import copy
import math
import operator
from collections.abc import Callable, Iterator
from typing import Any, ClassVar

_OP_FUNCS: dict[str, Callable[..., Any]] = {
    "+": operator.add,
    "-": operator.sub,
    "*": operator.mul,
    "/": operator.truediv,
    "//": operator.floordiv,
    "%": operator.mod,
    "**": operator.pow,
    "neg": operator.neg,
    "pos": operator.pos,
    "abs": operator.abs,
    "~": operator.invert,
    "sin": cmath.sin,
    "cos": cmath.cos,
    "exp": cmath.exp,
    "log": cmath.log,
}


def _is_finite(x: Any) -> bool:
    """
    Return True if x is a finite real or complex number.

    Only int, float, complex are checked. Other types (Decimal,
    Fraction, str, ...) return True (assumed finite), because
    Caused._value is documented to be int, float, or complex.
    """
    if isinstance(x, complex):
        return math.isfinite(x.real) and math.isfinite(x.imag)
    if isinstance(x, (int, float)):
        return math.isfinite(x)
    return True


class Caused:
    """
    Immutable numeric value with a causal chain.

    parents contains all operands (Caused and plain scalars) in
    evaluation order, so ``(a + 10).parents == (a, 10)``. This means
    ``(a + 10).same_as(a + Caused(10))`` is False.

    evaluate() recomputes the value from leaves upward using _OP_FUNCS.

    substitute(var, value) replaces var by value and recomputes.
    The replacement is by identity (``is``), not by value.

    simplify() performs constant folding AND basic algebraic
    simplification (x+0, x*1, x*0, x-0, x-x, x/1, x/x, x**1, x**0).
    x-x, x/x, and x*0 require finite operands (nan and inf are not
    folded, since e.g. inf * 0 = nan). x/x -> 1 requires a is b (the
    same object); two distinct Caused objects with the same value are
    not folded, to preserve their causal chains. simplify() may
    discard the causal chain for folded subtrees.

    differentiate(var) supports +, -, *, /, ** (constant exponent),
    neg, abs, sin, cos, exp, log. a**b with b as Caused is supported
    when a > 0 (or a is complex). Bitwise invert and modular pow raise
    NotImplementedError. The result tree may be deep; call simplify()
    if you need a compact expression.

    Note: log() and log(base) use cmath, so log of a negative
    number returns a complex value. If you need real-only semantics,
    check the sign of the argument before calling.
    """

    __slots__ = ("_frozen", "_op", "_parents", "_value")

    __match_args__ = ("value", "parents", "op")

    def __init__(
        self,
        value: Any,
        parents: list | tuple | None = None,
        op: str | None = None,
    ) -> None:
        if isinstance(value, Caused):
            raise TypeError(
                "Caused value cannot be another Caused; use Caused(value.value)"
            )
        object.__setattr__(self, "_value", value)
        object.__setattr__(self, "_parents", tuple(parents) if parents else ())
        object.__setattr__(self, "_op", op)
        object.__setattr__(self, "_frozen", True)

    def __setattr__(self, name: str, value: Any) -> None:
        if getattr(self, "_frozen", False):
            raise AttributeError("Caused is immutable")
        object.__setattr__(self, name, value)

    def __delattr__(self, name: str) -> None:
        raise AttributeError("Caused is immutable")

    @property
    def value(self) -> Any:
        return self._value

    @property
    def parents(self) -> tuple:
        return self._parents

    @property
    def op(self) -> str | None:
        return self._op

    def _combine(
        self, other: Any, op_func: Callable[[Any, Any], Any], symbol: str
    ) -> Caused:
        if not isinstance(other, Caused):
            return Caused(op_func(self._value, other), [self, other], symbol)
        return Caused(op_func(self._value, other._value), [self, other], symbol)

    def __add__(self, other: Any) -> Caused:
        return self._combine(other, operator.add, "+")

    def __sub__(self, other: Any) -> Caused:
        return self._combine(other, operator.sub, "-")

    def __mul__(self, other: Any) -> Caused:
        return self._combine(other, operator.mul, "*")

    def __truediv__(self, other: Any) -> Caused:
        return self._combine(other, operator.truediv, "/")

    def __floordiv__(self, other: Any) -> Caused:
        return self._combine(other, operator.floordiv, "//")

    def __mod__(self, other: Any) -> Caused:
        return self._combine(other, operator.mod, "%")

    def __pow__(self, other: Any, modulo: Any = None) -> Caused:
        if modulo is not None:
            if isinstance(other, Caused):
                return Caused(
                    pow(self._value, other._value, modulo), [self, other], "pow"
                )
            return Caused(pow(self._value, other, modulo), [self, other], "pow")
        return self._combine(other, operator.pow, "**")

    def __radd__(self, other: Any) -> Caused:
        return self._combine(other, operator.add, "+")

    def __rmul__(self, other: Any) -> Caused:
        return self._combine(other, operator.mul, "*")

    def _rcombine(
        self, other: Any, op_func: Callable[[Any, Any], Any], symbol: str
    ) -> Caused:
        if isinstance(other, Caused):
            return Caused(op_func(other._value, self._value), [other, self], symbol)
        return Caused(op_func(other, self._value), [other, self], symbol)

    def __rsub__(self, other: Any) -> Caused:
        return self._rcombine(other, operator.sub, "-")

    def __rtruediv__(self, other: Any) -> Caused:
        return self._rcombine(other, operator.truediv, "/")

    def __rfloordiv__(self, other: Any) -> Caused:
        return self._rcombine(other, operator.floordiv, "//")

    def __rmod__(self, other: Any) -> Caused:
        return self._rcombine(other, operator.mod, "%")

    def __rpow__(self, other: Any) -> Caused:
        return self._rcombine(other, operator.pow, "**")

    def __neg__(self) -> Caused:
        return Caused(-self._value, [self], "neg")

    def __pos__(self) -> Caused:
        return Caused(+self._value, [self], "pos")

    def __abs__(self) -> Caused:
        return Caused(abs(self._value), [self], "abs")

    def __invert__(self) -> Caused:
        return Caused(~self._value, [self], "~")

    def sin(self) -> Caused:
        return Caused(cmath.sin(self._value), [self], "sin")

    def cos(self) -> Caused:
        return Caused(cmath.cos(self._value), [self], "cos")

    def exp(self) -> Caused:
        return Caused(cmath.exp(self._value), [self], "exp")

    def log(self, base: Any = None) -> Caused:
        if base is None:
            return Caused(cmath.log(self._value), [self], "log")
        base_val = base._value if isinstance(base, Caused) else base
        if base_val == 1:
            raise ValueError("log base cannot be 1")
        return Caused(
            cmath.log(self._value) / cmath.log(base_val),
            [self, base],
            "log",
        )

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Caused):
            return bool(self._value == other._value)
        if isinstance(other, (int, float, complex, str, bool)):
            return bool(self._value == other)
        return NotImplemented

    def __ne__(self, other: object) -> bool:
        result = self.__eq__(other)
        if result is NotImplemented:
            return result
        return not result

    def _cmp_value(self, other: Any) -> Any:
        return other._value if isinstance(other, Caused) else other

    def __lt__(self, other: Any) -> bool:
        return bool(self._value < self._cmp_value(other))

    def __le__(self, other: Any) -> bool:
        return bool(self._value <= self._cmp_value(other))

    def __gt__(self, other: Any) -> bool:
        return bool(self._value > self._cmp_value(other))

    def __ge__(self, other: Any) -> bool:
        return bool(self._value >= self._cmp_value(other))

    def __hash__(self) -> int:
        try:
            return hash(self._value)
        except TypeError as e:
            raise TypeError(
                f"Caused with unhashable value "
                f"({type(self._value).__name__}) cannot be hashed"
            ) from e

    def __bool__(self) -> bool:
        return bool(self._value)

    def __format__(self, spec: str) -> str:
        return format(self._value, spec)

    def __copy__(self) -> Caused:
        return self

    def __deepcopy__(self, memo: dict) -> Caused:
        if id(self) in memo:
            return memo[id(self)]
        result = Caused(
            copy.deepcopy(self._value, memo),
            tuple(
                copy.deepcopy(p, memo) if not isinstance(p, Caused) else p
                for p in self._parents
            ),
            self._op,
        )
        memo[id(self)] = result
        return result

    def evaluate(self) -> Any:
        """
        Recompute the value from leaves upward using _OP_FUNCS.
        For 'log' with a base (parents = (self, base)), use
        cmath.log(a) / cmath.log(base). Raises ValueError if base == 1.
        log of a negative number returns a complex value (cmath).
        """
        if not self._parents:
            return self._value
        if self._op == "pow":
            vals = [p.evaluate() if isinstance(p, Caused) else p for p in self._parents]
            if len(vals) == 3:
                return pow(vals[0], vals[1], vals[2])
            return pow(vals[0], vals[1])
        if self._op == "log" and len(self._parents) == 2:
            a = self._parents[0]
            b = self._parents[1]
            a_val = a.evaluate() if isinstance(a, Caused) else a
            b_val = b.evaluate() if isinstance(b, Caused) else b
            if b_val == 1:
                raise ValueError("log base cannot be 1")
            return cmath.log(a_val) / cmath.log(b_val)
        vals = [p.evaluate() if isinstance(p, Caused) else p for p in self._parents]
        return _OP_FUNCS[self._op](*vals)

    def substitute(
        self,
        var: Caused,
        value: Any,
        _memo: dict[int, Caused] | None = None,
    ) -> Caused:
        """
        Replace var (by identity, ``is``) with value and recompute.
        Uses _memo to avoid recomputing shared DAG subtrees.
        """
        if _memo is None:
            _memo = {}
        if id(self) in _memo:
            return _memo[id(self)]
        if self is var:
            result = Caused(value)
            _memo[id(self)] = result
            return result
        if not self._parents:
            _memo[id(self)] = self
            return self
        new_parents = [
            p.substitute(var, value, _memo) if isinstance(p, Caused) else p
            for p in self._parents
        ]
        new_value = Caused(0, new_parents, self._op).evaluate()
        result = Caused(new_value, new_parents, self._op)
        _memo[id(self)] = result
        return result

    def explain(
        self,
        depth: int = 0,
        max_depth: int = 5,
        _stack: set[int] | None = None,
    ) -> str:
        if _stack is None:
            _stack = set()
        indent = "  " * depth
        line = f"{indent}{self._value!r}"
        if id(self) in _stack:
            return f"{line}  <cycle>"
        if depth >= max_depth or not self._parents:
            return line
        _stack.add(id(self))
        try:
            children = "\n".join(
                (
                    p.explain(depth + 1, max_depth, _stack)
                    if isinstance(p, Caused)
                    else f"{'  ' * (depth + 1)}{p!r}"
                )
                for p in self._parents
            )
        finally:
            _stack.discard(id(self))
        return f"{line}\n{children}"

    _UNARY_PREFIX: ClassVar[dict[str, str]] = {"neg": "-", "pos": "+", "~": "~"}
    _UNARY_FUNC: ClassVar[dict[str, str]] = {
        op: op for op in ("abs", "sin", "cos", "exp", "log")
    }

    def __str__(self) -> str:
        if not self._parents or self._op is None:
            return str(self._value)
        parts = [str(p) if isinstance(p, Caused) else repr(p) for p in self._parents]
        if self._op in self._UNARY_FUNC and len(parts) == 1:
            return f"{self._UNARY_FUNC[self._op]}({parts[0]})"
        if self._op in self._UNARY_PREFIX and len(parts) == 1:
            return f"({self._UNARY_PREFIX[self._op]}{parts[0]})"
        if self._op == "log" and len(parts) == 2:
            return f"log({parts[0]}, {parts[1]})"
        if self._op == "pow":
            return f"pow({', '.join(parts)})"
        sep = f" {self._op} "
        return f"({sep.join(parts)})"

    def __repr__(self) -> str:
        return f"Caused({self._value!r})"

    def __getnewargs__(self) -> tuple:
        return (self._value, self._parents, self._op)

    def to_dict(self, _stack: set[int] | None = None) -> dict:
        if _stack is None:
            _stack = set()
        if id(self) in _stack:
            return {
                "value": self._value,
                "parents": [],
                "op": self._op,
                "cycle": True,
            }
        _stack.add(id(self))
        try:
            parents_serialized = [
                p.to_dict(_stack) if isinstance(p, Caused) else p for p in self._parents
            ]
        finally:
            _stack.discard(id(self))
        return {
            "value": self._value,
            "parents": parents_serialized,
            "op": self._op,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Caused:
        parents = [
            (
                cls.from_dict(p)
                if isinstance(p, dict) and "value" in p and not p.get("cycle")
                else p
            )
            for p in d.get("parents", [])
        ]
        return cls(d["value"], parents, d.get("op"))

    def same_as(self, other: Any) -> bool:
        if not isinstance(other, Caused):
            return False
        if self._value != other._value or self._op != other._op:
            return False
        if len(self._parents) != len(other._parents):
            return False
        for a, b in zip(self._parents, other._parents):
            if isinstance(a, Caused) and isinstance(b, Caused):
                if not a.same_as(b):
                    return False
            elif a != b:
                return False
        return True

    def differentiate(
        self, var: Caused, _memo: dict[tuple[int, int], Caused] | None = None
    ) -> Caused:
        """
        Symbolic derivative with respect to var.

        Supported: +, -, *, /, ** (a constant, or a > 0 with b as
        Caused), neg, abs, sin, cos, exp, log.
        Raises NotImplementedError for ~ and modular pow.
        Raises ValueError for abs at 0, for a**b with a <= 0 (real,
        a != 0), and for log with base 1.

        log(a, b) uses cmath, so a or b negative returns a complex
        value. If you need real-only semantics, check the sign of
        the arguments before calling.

        The result tree may be deep (each product/quotient adds a
        few nodes). Call simplify() if you need a compact expression.
        """
        if _memo is None:
            _memo = {}
        key = (id(self), id(var))
        if key in _memo:
            return _memo[key]

        if self is var:
            result = Caused(1, [self], "d")
            _memo[key] = result
            return result

        if self._op == "d":
            result = Caused(0, [self], "d")
            _memo[key] = result
            return result

        if not self._parents or self._op is None:
            result = Caused(0, [self], "d")
            _memo[key] = result
            return result

        op = self._op
        p = self._parents

        if op in ("+", "-") and len(p) == 2:
            a, b = p
            da = a.differentiate(var, _memo) if isinstance(a, Caused) else Caused(0)
            db = b.differentiate(var, _memo) if isinstance(b, Caused) else Caused(0)
            result = da + db if op == "+" else da - db
            _memo[key] = result
            return result

        if op == "*" and len(p) == 2:
            a, b = p
            da = a.differentiate(var, _memo) if isinstance(a, Caused) else Caused(0)
            db = b.differentiate(var, _memo) if isinstance(b, Caused) else Caused(0)
            result = da * b + a * db
            _memo[key] = result
            return result

        if op == "/" and len(p) == 2:
            a, b = p
            da = a.differentiate(var, _memo) if isinstance(a, Caused) else Caused(0)
            db = b.differentiate(var, _memo) if isinstance(b, Caused) else Caused(0)
            result = (da * b - a * db) / (b**2)
            _memo[key] = result
            return result

        if op == "**" and len(p) == 2:
            a, b = p
            if isinstance(a, Caused) and not isinstance(b, Caused):
                da = a.differentiate(var, _memo)
                result = b * (a ** (b - 1)) * da
                _memo[key] = result
                return result
            a_val = a._value if isinstance(a, Caused) else a
            if isinstance(a_val, (int, float)):
                if a_val == 0:
                    if not isinstance(b, Caused) and b > 0:
                        _memo[key] = Caused(0)
                        return Caused(0)
                    raise ValueError(
                        "d/dx 0**b is undefined when b is not a positive constant"
                    )
                if a_val < 0:
                    raise ValueError("d/dx a**b requires a > 0")
            da = a.differentiate(var, _memo) if isinstance(a, Caused) else Caused(0)
            db = b.differentiate(var, _memo) if isinstance(b, Caused) else Caused(0)
            log_a = a.log() if isinstance(a, Caused) else Caused(cmath.log(a_val))
            result = self * (db * log_a + b * da / a)
            _memo[key] = result
            return result

        if op == "neg" and len(p) == 1:
            a = p[0]
            da = a.differentiate(var, _memo) if isinstance(a, Caused) else Caused(0)
            result = -da
            _memo[key] = result
            return result

        if op == "abs" and len(p) == 1:
            a = p[0]
            da = a.differentiate(var, _memo) if isinstance(a, Caused) else Caused(0)
            a_val = a._value if isinstance(a, Caused) else a
            if a_val == 0:
                raise ValueError("derivative of abs at 0 is undefined")
            sign = 1 if a_val > 0 else -1
            result = Caused(sign) * da
            _memo[key] = result
            return result

        if op == "sin" and len(p) == 1:
            a = p[0]
            da = a.differentiate(var, _memo) if isinstance(a, Caused) else Caused(0)
            result = (
                a.cos() * da if isinstance(a, Caused) else Caused(cmath.cos(a)) * da
            )
            _memo[key] = result
            return result

        if op == "cos" and len(p) == 1:
            a = p[0]
            da = a.differentiate(var, _memo) if isinstance(a, Caused) else Caused(0)
            sin_a = a.sin() if isinstance(a, Caused) else Caused(cmath.sin(a))
            result = -sin_a * da
            _memo[key] = result
            return result

        if op == "exp" and len(p) == 1:
            a = p[0]
            da = a.differentiate(var, _memo) if isinstance(a, Caused) else Caused(0)
            result = self * da
            _memo[key] = result
            return result

        if op == "log" and len(p) == 1:
            a = p[0]
            da = a.differentiate(var, _memo) if isinstance(a, Caused) else Caused(0)
            result = da / a if isinstance(a, Caused) else da / Caused(a)
            _memo[key] = result
            return result

        if op == "log" and len(p) == 2:
            a, b = p
            da = a.differentiate(var, _memo) if isinstance(a, Caused) else Caused(0)
            db = b.differentiate(var, _memo) if isinstance(b, Caused) else Caused(0)
            a_val = a._value if isinstance(a, Caused) else a
            b_val = b._value if isinstance(b, Caused) else b
            if b_val == 1:
                raise ValueError("log base cannot be 1")
            ln_a = cmath.log(a_val)
            ln_b = cmath.log(b_val)
            result = (da / a_val) / ln_b - (ln_a * db) / (b_val * ln_b**2)
            _memo[key] = result
            return result

        if op == "~":
            raise NotImplementedError("differentiate() does not support bitwise invert")

        if op == "pow":
            raise NotImplementedError("differentiate() does not support modular pow")

        raise NotImplementedError(f"differentiate() does not support op={op!r}")

    def simplify(self) -> Caused:
        """
        Constant folding and basic algebraic simplification.

        Folds fully-constant subtrees. Also simplifies:
        x+0, 0+x, x-0, x-x -> 0 (if x is x and x is finite),
        x*1, 1*x, x*0 -> 0 (if the non-zero side is finite),
        x/1, x/x -> 1 (if x is x, x != 0, and x is finite),
        x**1, x**0 -> 1.

        x-x -> 0 and x/x -> 1 require a is b (the same object). Two
        distinct Caused objects with the same value are not folded,
        to preserve their causal chains.

        May discard the causal chain for folded subtrees.
        """
        if not self._parents:
            return self
        new_parents: list[Any] = []
        for p in self._parents:
            if isinstance(p, Caused):
                new_parents.append(p.simplify())
            else:
                new_parents.append(p)
        op = self._op
        if op in ("+", "-") and len(new_parents) == 2:
            a, b = new_parents
            a_val = a._value if isinstance(a, Caused) else a
            b_val = b._value if isinstance(b, Caused) else b
            if op == "+" and b_val == 0:
                return a if isinstance(a, Caused) else Caused(a)
            if op == "+" and a_val == 0:
                return b if isinstance(b, Caused) else Caused(b)
            if op == "-" and b_val == 0:
                return a if isinstance(a, Caused) else Caused(a)
            if op == "-" and a is b and _is_finite(a_val):
                return Caused(0)
        if op == "*" and len(new_parents) == 2:
            a, b = new_parents
            a_val = a._value if isinstance(a, Caused) else a
            b_val = b._value if isinstance(b, Caused) else b
            if b_val == 1:
                return a if isinstance(a, Caused) else Caused(a)
            if a_val == 1:
                return b if isinstance(b, Caused) else Caused(b)
            if b_val == 0 and _is_finite(a_val):
                return Caused(0)
            if a_val == 0 and _is_finite(b_val):
                return Caused(0)
        if op == "/" and len(new_parents) == 2:
            a, b = new_parents
            b_val = b._value if isinstance(b, Caused) else b
            if b_val == 1:
                return a if isinstance(a, Caused) else Caused(a)
            if a is b:
                a_val = a._value if isinstance(a, Caused) else a
                if a_val != 0 and _is_finite(a_val):
                    return Caused(1)
        if op == "**" and len(new_parents) == 2:
            a, b = new_parents
            b_val = b._value if isinstance(b, Caused) else b
            if b_val == 1:
                return a if isinstance(a, Caused) else Caused(a)
            if b_val == 0:
                return Caused(1)
        has_non_leaf = any(isinstance(p, Caused) for p in new_parents)
        if not has_non_leaf:
            return Caused(self._value)
        return Caused(self._value, new_parents, op)

    def walk(self, order: str = "preorder") -> Iterator[Caused]:
        if order not in ("preorder", "postorder"):
            raise ValueError(f"unknown order: {order!r}")
        if order == "preorder":
            yield self
        for p in self._parents:
            if isinstance(p, Caused):
                yield from p.walk(order)
        if order == "postorder":
            yield self

    def stats(self) -> dict:
        visited: set[int] = set()
        node_count = 0
        leaf_count = 0
        op_counts: dict[str, int] = {}
        max_depth = 0

        def _visit(node: Caused, depth: int) -> None:
            nonlocal node_count, leaf_count, max_depth
            if id(node) in visited:
                return
            visited.add(id(node))
            node_count += 1
            max_depth = max(max_depth, depth)
            if not node._parents:
                leaf_count += 1
                return
            if node._op:
                op_counts[node._op] = op_counts.get(node._op, 0) + 1
            for p in node._parents:
                if isinstance(p, Caused):
                    _visit(p, depth + 1)

        _visit(self, 0)
        return {
            "nodes": node_count,
            "leaves": leaf_count,
            "depth": max_depth,
            "ops": op_counts,
        }

    def format_tree(self) -> str:
        lines: list[str] = []
        stack: set[int] = set()
        seen: set[int] = set()

        def _render(node: Any, prefix: str, is_last: bool, is_root: bool) -> None:
            connector = "" if is_root else ("└── " if is_last else "├── ")
            is_caused = isinstance(node, Caused)
            if is_caused:
                label = f"{node._value!r}"
                if node._op:
                    label = f"{node._op} → {label}"
                if id(node) in stack:
                    lines.append(f"{prefix}{connector}{label}  <cycle>")
                    return
                if id(node) in seen:
                    lines.append(f"{prefix}{connector}{label}  <shared>")
                    return
                seen.add(id(node))
                stack.add(id(node))
            else:
                label = repr(node)
            try:
                lines.append(f"{prefix}{connector}{label}")
                if is_caused and node._parents:
                    child_prefix = prefix + (
                        "" if is_root else ("    " if is_last else "│   ")
                    )
                    for i, p in enumerate(node._parents):
                        _render(p, child_prefix, i == len(node._parents) - 1, False)
            finally:
                if is_caused:
                    stack.discard(id(node))

        _render(self, "", True, True)
        return "\n".join(lines)
