"""
i18n.py — Natural Language Generation (NLG) for the Caused symbolic math engine.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar, Literal

if TYPE_CHECKING:
    from .core import Caused


_EN_PACK: dict[str, str] = {
    "+": "{a} plus {b}",
    "-": "{a} minus {b}",
    "*": "{a} times {b}",
    "/": "{a} divided by {b}",
    "//": "{a} integer-divided by {b}",
    "%": "{a} modulo {b}",
    "**": "{a} raised to the power of {b}",
    "neg": "negative {a}",
    "pos": "positive {a}",
    "abs": "absolute value of {a}",
    "~": "bitwise complement of {a}",
    "sin": "sine of {a}",
    "cos": "cosine of {a}",
    "exp": "exponential of {a}",
    "log": "logarithm of {a}",
    "log_base": "logarithm of {a} base {b}",
    "pow_mod": "{a} raised to the power of {b} modulo {c}",
    "d": "the derivative of {a}",
    "because": "{a} because {b}",
    "and": "{a}, and {b}",
    "equals": "equals",
    "result": "{name} is {value}",
    "root_cause": "The root cause is {name} = {value}",
    "unnamed_leaf": "a constant {value}",
    "unknown_op": "an unknown operation on {a}",
}

_ZH_PACK: dict[str, str] = {
    "+": "{a} 加 {b}",
    "-": "{a} 減 {b}",
    "*": "{a} 乘 {b}",
    "/": "{a} 除以 {b}",
    "//": "{a} 整除 {b}",
    "%": "{a} 對 {b} 取餘",
    "**": "{a} 的 {b} 次方",
    "neg": "{a} 的負值",
    "pos": "{a} 的正值",
    "abs": "{a} 的絕對值",
    "~": "{a} 的位元反相",
    "sin": "{a} 的正弦",
    "cos": "{a} 的餘弦",
    "exp": "{a} 的指數",
    "log": "{a} 的對數",
    "log_base": "以 {b} 為底 {a} 的對數",
    "pow_mod": "{a} 的 {b} 次方對 {c} 取模",
    "d": "{a} 的導數",
    "because": "{a}，因為 {b}",
    "and": "{a}，而且 {b}",
    "equals": "等於",
    "result": "{name} 是 {value}",
    "root_cause": "根本原因是 {name} = {value}",
    "unnamed_leaf": "常數 {value}",
    "unknown_op": "對 {a} 的未知運算",
}

_DEFAULT_PACKS: dict[str, dict[str, str]] = {
    "en": _EN_PACK,
    "zh": _ZH_PACK,
}

_FALLBACK_LANG = "en"


class I18nEngine:
    """
    Manage language packs and translate Caused trees into sentences.
    """

    _packs: ClassVar[dict[str, dict[str, str]]] = dict(_DEFAULT_PACKS)

    @classmethod
    def register_language(cls, lang_code: str, pack: dict[str, str]) -> None:
        if not isinstance(lang_code, str) or not lang_code:
            raise ValueError("lang_code must be a non-empty string")
        if not isinstance(pack, dict):
            raise TypeError("pack must be a dict[str, str]")
        cls._packs.setdefault(lang_code, {}).update(pack)

    @classmethod
    def available_languages(cls) -> list[str]:
        return sorted(cls._packs)

    @classmethod
    def translate(cls, key: str, lang: str = _FALLBACK_LANG, **kwargs: Any) -> str:
        pack = cls._packs.get(lang, {})
        template = pack.get(key)
        if template is None:
            template = cls._packs[_FALLBACK_LANG].get(key)
        if template is None:
            return f"<{key}>"
        try:
            return template.format(**kwargs)
        except (KeyError, IndexError):
            return template

    @classmethod
    def _render_operand(cls, operand: Any, lang: str, named: dict[int, str]) -> str:
        from .core import Caused

        if isinstance(operand, Caused):
            if id(operand) in named:
                return named[id(operand)]
            return cls._render_expression(operand, lang, named)
        return repr(operand)

    @classmethod
    def _render_expression(cls, node: Caused, lang: str, named: dict[int, str]) -> str:
        op = node._op
        parents = node._parents

        if op is None or not parents:
            return repr(node._value)

        if op == "pow":
            rendered = [cls._render_operand(p, lang, named) for p in parents]
            if len(rendered) == 3:
                return cls.translate(
                    "pow_mod", lang, a=rendered[0], b=rendered[1], c=rendered[2]
                )
            if len(rendered) == 2:
                return cls.translate("**", lang, a=rendered[0], b=rendered[1])
            return cls.translate("unknown_op", lang, a=repr(node._value))

        if op == "log" and len(parents) == 2:
            a = cls._render_operand(parents[0], lang, named)
            b = cls._render_operand(parents[1], lang, named)
            return cls.translate("log_base", lang, a=a, b=b)

        if op in ("+", "-", "*", "/", "//", "%", "**") and len(parents) == 2:
            a = cls._render_operand(parents[0], lang, named)
            b = cls._render_operand(parents[1], lang, named)
            return cls.translate(op, lang, a=a, b=b)

        if op in ("neg", "pos", "abs", "~", "sin", "cos", "exp", "log", "d"):
            if len(parents) == 1:
                a = cls._render_operand(parents[0], lang, named)
                return cls.translate(op, lang, a=a)
            if op == "d":
                a = cls._render_operand(parents[0], lang, named)
                return cls.translate("d", lang, a=a)

        rendered = [cls._render_operand(p, lang, named) for p in parents]
        return cls.translate("unknown_op", lang, a=", ".join(rendered))

    @classmethod
    def _render_chain(
        cls,
        node: Caused,
        lang: str,
        named: dict[int, str],
        _visited: set[int] | None = None,
    ) -> str:
        from .core import Caused

        if _visited is None:
            _visited = set()
        if id(node) in _visited:
            return ""
        _visited = _visited | {id(node)}

        name = named.get(id(node))
        expr = cls._render_expression(node, lang, named)

        if name:
            head = f"{name} {cls.translate('equals', lang)} {expr}"
        else:
            head = expr

        reasons = []
        for p in node._parents:
            if isinstance(p, Caused) and id(p) not in _visited:
                r = cls._render_chain(p, lang, named, _visited)
                if r:
                    reasons.append(r)

        if not reasons:
            return head

        reason_text = reasons[0]
        for r in reasons[1:]:
            reason_text = cls.translate("and", lang, a=reason_text, b=r)

        return cls.translate("because", lang, a=head, b=reason_text)

    @classmethod
    def _find_root(cls, node: Caused, _visited: set[int] | None = None) -> Caused:
        from .core import Caused

        if _visited is None:
            _visited = set()
        if id(node) in _visited:
            return node
        _visited = _visited | {id(node)}

        for p in node._parents:
            if isinstance(p, Caused):
                return cls._find_root(p, _visited)
        return node

    @classmethod
    def explain(
        cls,
        node: Caused,
        lang: str = _FALLBACK_LANG,
        mode: Literal["expr", "chain", "root"] = "expr",
        names: dict[int, str] | None = None,
    ) -> str:
        if lang not in cls._packs:
            lang = _FALLBACK_LANG
        named = names or {}

        if mode == "expr":
            return cls._render_expression(node, lang, named)
        if mode == "chain":
            return cls._render_chain(node, lang, named)
        if mode == "root":
            root = cls._find_root(node)
            name = named.get(id(root), str(root._value))
            return cls.translate("root_cause", lang, name=name, value=root._value)
        raise ValueError(f"unknown mode: {mode!r}")
