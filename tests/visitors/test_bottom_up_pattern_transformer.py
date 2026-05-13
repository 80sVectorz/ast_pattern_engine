import ast
from ast_pattern_engine.nodes.basic import Collect, NodePattern
from ast_pattern_engine.visitors import BottomUpPatternTransformer


def _parse_stmt(code: str):
    return ast.parse(code).body[0]


def _constant(value, template):
    node = ast.copy_location(ast.Constant(value=value), template)
    ast.fix_missing_locations(node)
    return node


def test_bottom_up_pattern_transformer_collapses_children_before_parent():
    source = "def foo():\n    return (1 + 2) + (3 + 4)\n"
    tree = ast.parse(source)
    pattern = [Collect(NodePattern(ast.BinOp), "expr")]

    def collapse_sum(bindings) -> list[ast.AST]:
        expr = bindings["expr"]
        left, right = expr.left, expr.right
        assert isinstance(left, ast.Constant)
        assert isinstance(right, ast.Constant)
        assert isinstance(left.value, int)
        assert isinstance(right.value, int)
        total = left.value + right.value
        return [_constant(total, expr)]

    transformer = BottomUpPatternTransformer(pattern, {"expr": collapse_sum})
    transformer.visit(tree)

    func = tree.body[0]
    assert isinstance(func, ast.FunctionDef)
    ret_stmt = func.body[0]
    assert isinstance(ret_stmt, ast.Return)
    assert isinstance(ret_stmt.value, ast.Constant)
    assert ret_stmt.value.value == 10
    assert len(transformer.matches) == 3

    col_offsets = [bindings["expr"].col_offset for bindings in transformer.matches]
    assert col_offsets == [12, 22, 11]


def test_bu_transformer_list_manipulation():
    tree = ast.parse("x = 1\ny = 2\nz = 3")
    pattern = [Collect(NodePattern(ast.Assign), "a")]

    # Delete node (returns None)
    transformer1 = BottomUpPatternTransformer(pattern, {"a": None})
    res1 = transformer1.visit(ast.parse("x = 1\ny = 2\nz = 3"))
    assert len(res1.body) == 0

    # Return empty list (deletes node)
    transformer2 = BottomUpPatternTransformer(pattern, {"a": lambda b: []})
    res2 = transformer2.visit(ast.parse("x = 1\ny = 2\nz = 3"))
    assert len(res2.body) == 0

    # Return multiple nodes (expands)
    def expand(_):
        return [_parse_stmt("pass"), _parse_stmt("pass")]

    transformer3 = BottomUpPatternTransformer(pattern, {"a": expand})
    res3 = transformer3.visit(ast.parse("x = 1"))
    assert len(res3.body) == 2
    assert isinstance(res3.body[0], ast.Pass)

    # Return non-list error? (It returns None or a single node or list).
    # In BottomUp, returning a single node vs list of 1 node is handled.


def test_bu_dict_as_nodes():
    # Calling the staticmethod directly to cover the dict recursion
    nodes = BottomUpPatternTransformer._as_nodes({"key": ast.parse("pass").body[0]})
    assert len(nodes) == 1
    assert isinstance(nodes[0], ast.Pass)
