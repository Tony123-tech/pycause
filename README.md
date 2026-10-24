# Caused

An immutable numeric value that remembers how it was computed.

Python 3.10+. No dependencies.

## Install

Drop `caused.py` into your project.

## Quick start

```python
from caused import Caused

a = Caused(1)
b = Caused(2)
c = (a + b) * 10

c.value          # 30
str(c)           # '((1 + 2) * 10)'
c.explain()      # indented tree
c.format_tree()  # ASCII tree
c.stats()        # node/leaf/depth/op histogram
```

## Design

`Caused(value, parents, op)`:

- `value` — numeric result.
- `parents` — every operand in evaluation order, including plain scalars. `(a + 10).parents == (a, 10)`.
- `op` — operator that produced `value`, or `None` for a leaf.

Immutable: `__slots__`, frozen flag, read-only properties, tuple `parents`. `__setattr__` and `__delattr__` raise `AttributeError`.

`same_as` compares structurally (value, op, parents recursively). `__eq__` compares only `value`.

## Operations

Binary `+ - * / // % **`, reflected `10 + a`, unary `-a +a abs ~`, and `pow(a, b, m)`. Each returns a new `Caused`. Reflected operators preserve evaluation order, so `10 - a` stores `(10, a)`.

Comparison delegates to `value`. `__eq__` returns `NotImplemented` outside `int / float / complex / str / bool`. `__hash__` hashes `value`, raising `TypeError` for unhashable values.

## Evaluation

`evaluate()` recomputes from leaves upward via an operator table. `pow(a, b, m)` and `log(a, base)` are handled explicitly.

`substitute(var, value)` replaces `var` by identity and recomputes, memoized for shared DAG subtrees.

## Simplification

`simplify()` does constant folding plus:

- `x + 0`, `0 + x`, `x - 0` → `x`
- `x - x` → `0` (same object, finite)
- `x * 1`, `1 * x` → `x`
- `x * 0` → `0` (non-zero side finite)
- `x / 1` → `x`
- `x / x` → `1` (same object, non-zero, finite)
- `x ** 1` → `x`, `x ** 0` → `1`

`nan` and `inf` are never folded (`inf * 0` is `nan`, `inf - inf` is `nan`). Distinct objects with equal value are not folded.

## Differentiation

`differentiate(var)` returns a `Caused` for the symbolic derivative.

Supported: `+ - * / **` (constant exponent, or `a > 0` with `Caused` exponent), `neg`, `abs`, `sin`, `cos`, `exp`, `log` (with or without base).

Raises:

- `ValueError` — `abs` at `0`; `a ** b` with real `a < 0`; `a ** b` with `a == 0` and non-positive or `Caused` `b`; `log` base `1`.
- `NotImplementedError` — bitwise invert, modular `pow`.

`log` uses `cmath`; negative arguments produce complex results. Result trees can be deep; call `simplify()` to compact. Memo keyed on `(id(self), id(var))`.

## Serialization

`to_dict()` / `from_dict()`, cycle-safe (`"cycle": True`). Pickle via `__getnewargs__`; cycles and shared subtrees survive.

## Inspection

- `explain(max_depth=5)` — indented value tree, cycle-safe.
- `format_tree()` — ASCII tree with `<cycle>` and `<shared>`.
- `stats()` — nodes, leaves, depth, operator histogram.
- `walk("preorder" | "postorder")` — iterate nodes.

## Copy

`__copy__` returns `self`. `__deepcopy__` deep-copies scalar operands and `value`, shares `Caused` parents.

## Pattern matching

`__match_args__ = ("value", "parents", "op")`:

```python
match c:
    case Caused(value=v, parents=(), op=None):
        print(f"leaf: {v}")
    case Caused(op="+"):
        print("addition")
```

## Formatting

`__format__` delegates to `value`: `f"{c:.2f}"`.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
