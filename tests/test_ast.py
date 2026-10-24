from pycause.core import Caused, pretty_print_ast


def test_constant():
    x = Caused(42)
    assert x.to_ast() == {"type": "Constant", "value": 42}


def test_simple_binary():
    x = Caused(10)
    y = x - 5
    z = y * 2
    ast = z.to_ast()
    assert ast["type"] == "BinOp"
    assert ast["op"] == "Mult"
    assert ast["left"]["op"] == "Sub"
    assert ast["left"]["left"] == {"type": "Constant", "value": 10}
    assert ast["left"]["right"] == {"type": "Constant", "value": 5}
    assert ast["right"] == {"type": "Constant", "value": 2}


def test_pretty_print():
    x = Caused(10)
    z = (x - 5) * 2
    out = pretty_print_ast(z.to_ast())
    expected = "Mult:\n" "  Sub:\n" "    10\n" "    5\n" "  2"
    assert out == expected


def test_unary_neg():
    x = Caused(10)
    y = -x
    ast = y.to_ast()
    assert ast["type"] == "UnaryOp"
    assert ast["op"] == "USub"
    assert ast["operand"] == {"type": "Constant", "value": 10}


def test_unary_invert():
    x = Caused(0b1010)
    y = ~x
    ast = y.to_ast()
    assert ast["type"] == "UnaryOp"
    assert ast["op"] == "Invert"


def test_abs_call():
    x = Caused(-5)
    y = abs(x)
    ast = y.to_ast()
    assert ast["type"] == "Call"
    assert ast["func"] == "Abs"
    assert ast["args"] == [{"type": "Constant", "value": -5}]


def test_sin_call():
    x = Caused(0)
    y = x.sin()
    ast = y.to_ast()
    assert ast["type"] == "Call"
    assert ast["func"] == "Sin"


def test_log_one_arg():
    x = Caused(8)
    y = x.log()
    ast = y.to_ast()
    assert ast["type"] == "Call"
    assert ast["func"] == "Log"
    assert len(ast["args"]) == 1


def test_log_with_base():
    x = Caused(8)
    b = Caused(2)
    y = x.log(b)
    ast = y.to_ast()
    assert ast["type"] == "Call"
    assert ast["func"] == "Log"
    assert len(ast["args"]) == 2


def test_modular_pow():
    x = Caused(2)
    y = Caused(10)
    z = Caused(1000)
    r = pow(x, y, z)
    ast = r.to_ast()
    assert ast["type"] == "Call"
    assert ast["func"] == "PowMod"
    assert len(ast["args"]) == 3


def test_modular_pow_evaluate():
    x = Caused(2)
    y = Caused(10)
    z = Caused(1000)
    r = pow(x, y, z)
    assert r.evaluate() == pow(2, 10, 1000)


def test_plain_pow():
    x = Caused(2)
    y = Caused(3)
    r = x**y
    ast = r.to_ast()
    assert ast["type"] == "BinOp"
    assert ast["op"] == "Pow"


def test_shared_node_becomes_ref():
    x = Caused(5)
    y = x * x
    ast = y.to_ast()
    assert ast["type"] == "BinOp"
    assert ast["left"] == {"type": "Constant", "value": 5}
    assert ast["right"]["type"] == "Ref"


def test_shared_node_ref_matches_first_visit():
    x = Caused(5)
    y = x * x
    seen: dict[int, str] = {}
    ast = y.to_ast(seen)
    assert ast["right"]["type"] == "Ref"
    assert ast["right"]["ref"] == seen[id(x)]


def test_content_hash_deterministic():
    x = Caused(3)
    y = Caused(4)
    a = (x + y) * 2
    b = (Caused(3) + Caused(4)) * 2
    assert a.content_hash() == b.content_hash()


def test_content_hash_distinguishes_order():
    x = Caused(3)
    y = Caused(4)
    a = x - y
    b = y - x
    assert a.content_hash() != b.content_hash()


def test_content_hash_is_sha256():
    x = Caused(1)
    h = x.content_hash()
    assert len(h) == 64
    assert all(c in "0123456789abcdef" for c in h)
