import ast
from ast_pattern_engine.nodes.basic import AnyOf, NodePattern, Collect

def test_any_of_matches_and_conflicts():
    node = ast.parse("1").body[0].value
    
    # First matches
    pattern1 = AnyOf([
        NodePattern(ast.Constant),
        NodePattern(ast.Name)
    ])
    assert pattern1.match_node(node, {"existing": 1}) == {"existing": 1}
    
    # Second matches
    pattern2 = AnyOf([
        NodePattern(ast.Name),
        NodePattern(ast.Constant)
    ])
    assert pattern2.match_node(node, {}) == {}
    
    # None matches
    pattern3 = AnyOf([
        NodePattern(ast.Name),
        NodePattern(ast.Assign)
    ])
    assert pattern3.match_node(node, {}) is None

    # Match produces conflicting key
    pattern4 = AnyOf([
        Collect(NodePattern(ast.Constant), "c")
    ])
    assert pattern4.match_node(node, {"c": "conflict"}) is None
