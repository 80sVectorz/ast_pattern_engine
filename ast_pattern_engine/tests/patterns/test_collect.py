import ast
from ast_pattern_engine.nodes.basic import Collect, NodePattern

def test_collect_match_single_constant():
    node = ast.parse("1").body[0]
    assert isinstance(node, ast.Expr)
    node = node.value
    pattern = Collect(NodePattern(ast.Constant, value=1), "const")

    bindings = pattern.match_node(node, {})

    assert bindings is not None
    assert "const" in bindings
    assert isinstance(bindings["const"], ast.Constant)
    assert bindings["const"].value == 1
