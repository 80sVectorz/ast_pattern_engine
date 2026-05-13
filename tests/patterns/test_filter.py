import ast
from ast_pattern_engine.nodes.basic import Filter
from ast_pattern_engine.nodes.sequences import Repetition
from ast_pattern_engine.engine import match_sequence


def test_filter_no_key():
    node = ast.parse("1").body[0].value
    # Matches, no key bound
    pattern = Filter(lambda x: isinstance(x, ast.Constant))
    assert pattern.match_node(node, {}) == {}

    # Fails
    pattern2 = Filter(lambda x: isinstance(x, ast.Name))
    assert pattern2.match_node(node, {}) is None


def test_filter_with_key_and_conflicts():
    node = ast.parse("1").body[0].value
    pattern = Filter(lambda x: isinstance(x, ast.Constant), key="my_filter")

    # Matches and binds
    res = pattern.match_node(node, {})
    assert res == {"my_filter": node}

    # Conflict on duplicate key without force
    assert pattern.match_node(node, {"my_filter": "existing"}) is None

    # When inside a Repetition, ancestor forces list
    rep_pattern = Repetition(pattern)
    # Match node directly against the filter while simulating the Repetition context
    # _ancestor_forces_list() requires the engine to have set up the Repetition parent.
    # We can just test Repetition matching directly.
    seq_nodes = [node, node]
    res_seq = match_sequence([rep_pattern], seq_nodes)
    assert len(res_seq) == 1
    assert res_seq[0]["my_filter"] == [node, node]
