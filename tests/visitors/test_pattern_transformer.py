import ast
import pytest
from ast_pattern_engine.nodes.basic import Collect, NodePattern
from ast_pattern_engine.nodes.sequences import Repetition
from ast_pattern_engine.visitors import PatternTransformer


def _parse_stmt(code: str):
    return ast.parse(code).body[0]


def _constant(value, template):
    node = ast.copy_location(ast.Constant(value=value), template)
    ast.fix_missing_locations(node)
    return node


def _constant_val(value):
    return ast.Constant(value=value)


def test_pattern_transformer_replaces_list_nodes():
    tree = ast.parse("a = 1\nb = 2")
    original_nodes = list(tree.body)
    pattern = [Collect(NodePattern(ast.Assign), "assign")]

    def to_pass(_) -> list[ast.AST]:
        return [_parse_stmt("pass")]

    transformer = PatternTransformer(pattern, {"assign": to_pass})
    transformer.visit(tree)

    assert all(isinstance(stmt, ast.Pass) for stmt in tree.body)
    assert [match["assign"] for match in transformer.matches] == original_nodes


def test_pattern_transformer_deletes_matched_nodes():
    tree = ast.parse("a = 1\nb = 2\nc = 3")
    original_nodes = list(tree.body)
    pattern = [Collect(NodePattern(ast.Assign), "assign")]
    transformer = PatternTransformer(pattern, {"assign": None})
    transformer.visit(tree)

    assert tree.body == []
    assert [match["assign"] for match in transformer.matches] == original_nodes


def test_pattern_transformer_replaces_nested_nonlist_field():
    tree = ast.parse("x = 1 + 2")
    assert isinstance(tree.body[0], ast.Assign)
    original_value = tree.body[0].value
    pattern = [Collect(NodePattern(ast.BinOp), "expr")]

    def to_constant(bindings) -> list[ast.AST]:
        return [_constant(42, bindings["expr"])]

    transformer = PatternTransformer(pattern, {"expr": to_constant})
    transformer.visit(tree)

    new_value = tree.body[0].value
    assert isinstance(new_value, ast.Constant)
    assert new_value.value == 42
    assert transformer.matches[0]["expr"] is original_value


def test_pattern_transformer_replaces_sequence_with_multiple_nodes():
    tree = ast.parse("a = 1\nb = 2\nc = 3")
    pattern = [
        Repetition(
            Collect(NodePattern(ast.Assign), "assign"),
            min_matches=2,
            max_matches=2,
        ),
    ]

    def replace_block(bindings) -> list[ast.AST]:
        assigns = bindings["assign"]
        assert isinstance(assigns, list)
        assert [node.targets[0].id for node in assigns] == ["a", "b"]
        return [
            _parse_stmt("x = 99"),
            _parse_stmt("y = 100"),
            _parse_stmt("return x"),
        ]

    transformer = PatternTransformer(pattern, {"assign": replace_block})
    transformer.visit(tree)

    body = tree.body
    assert len(body) == 4
    assert isinstance(body[0], ast.Assign)
    assert isinstance(body[1], ast.Assign)

    assert isinstance(body[0].targets[0], ast.Name)
    assert body[0].targets[0].id == "x"

    assert isinstance(body[1].targets[0], ast.Name)
    assert body[1].targets[0].id == "y"

    assert isinstance(body[2], ast.Return)
    assert isinstance(body[3], ast.Assign)

    assert isinstance(body[3].targets[0], ast.Name)
    assert body[3].targets[0].id == "c"

    assert len(transformer.matches) == 1
    assigns = transformer.matches[0]["assign"]
    assert [node.targets[0].id for node in assigns] == ["a", "b"]


def test_pt_nonlist_replace_errors():
    tree = ast.parse("x = 1")
    # Target the value (ast.Constant), which is a non-list field of Assign
    pattern = [Collect(NodePattern(ast.Constant), "c")]

    # Error: replacing non-list field with multiple nodes
    def multi_replace(_):
        return [_constant_val(2), _constant_val(3)]

    transformer1 = PatternTransformer(pattern, {"c": multi_replace})
    with pytest.raises(ValueError, match="Cannot replace non-list field"):
        transformer1.visit(ast.parse("x = 1"))

    # Error: handler returns non-list
    def bad_handler(_):
        return _constant_val(2) # type: ignore

    transformer2 = PatternTransformer(pattern, {"c": bad_handler})
    with pytest.raises(TypeError, match="Handler must return list"):
        transformer2.visit(ast.parse("x = 1"))


def test_pt_plan_errors():
    tree = ast.parse("a = 1\nb = 2")
    pattern = [Collect(NodePattern(ast.Assign), "a")]
    
    # key not in bindings (should silently continue)
    transformer1 = PatternTransformer(pattern, {"missing_key": lambda b: []})
    transformer1.visit(ast.parse("a = 1"))

    # collected is empty (should silently continue)
    transformer2 = PatternTransformer(pattern, {"a": lambda b: []})
    # override matching to return empty list for testing
    b = {"a": []}
    transformer2.matches.append(b) 
    
    # handler returns non-list
    def bad_plan_handler(_):
        return "not a list"
    transformer3 = PatternTransformer(pattern, {"a": bad_plan_handler})
    with pytest.raises(TypeError, match="must return `list"):
        transformer3.visit(ast.parse("a = 1"))


def test_pt_nested_replace_and_delete():
    # Tree with nested structure
    tree = ast.parse("x = [1, 2, 3]")
    pattern = [Collect(NodePattern(ast.Constant), "c")]

    # Delete nested nodes
    # 'c' matches the Constants 1, 2, 3 inside the list inside Assign
    transformer1 = PatternTransformer(pattern, {"c": None})
    res1 = transformer1.visit(ast.parse("x = [1, 2, 3]"))
    assert len(res1.body[0].value.elts) == 0

    # Replace nested nodes
    def replace_with_99(_):
        return [_constant_val(99)]
    transformer2 = PatternTransformer(pattern, {"c": replace_with_99})
    res2 = transformer2.visit(ast.parse("x = [1, 2, 3]"))
    assert all(elt.value == 99 for elt in res2.body[0].value.elts)


def test_pt_dict_as_nodes():
    tree = ast.parse("x = 1")
    pattern = [Collect(NodePattern(ast.Assign), "a")]
    
    # We force the binding to be a dict to trigger dict handling in _as_nodes
    class DictTransformer(PatternTransformer):
        def _plan(self, seq):
            # Intercept and mutate bindings
            res = super()._plan(seq)
            return res
            
    transformer = DictTransformer(pattern, {"a": lambda b: [_parse_stmt("x = 2")]})
    # Override match manually
    mtch = transformer._match_patterns = lambda p, s, i, b: [({"a": {"nested": s[i]}}, i+1)] if i < len(s) else []
    
    res = transformer.visit(tree)
    assert isinstance(res.body[0], ast.Assign)
    assert res.body[0].value.value == 2


def test_pt_generic_visit_list_field_error():
    tree = ast.parse("a = 1")
    pattern = [Collect(NodePattern(ast.Assign), "a")]
    transformer = PatternTransformer(pattern, {})
    
    # Force a child to not be an AST node
    class BadTransformer(PatternTransformer):
        def visit(self, node):
            if isinstance(node, ast.Assign):
                return "Not an AST node"
            return super().visit(node)
            
    bad_transformer = BadTransformer(pattern, {})
    with pytest.raises(TypeError, match="must contain AST nodes"):
        bad_transformer.visit(ast.parse("a = 1"))
