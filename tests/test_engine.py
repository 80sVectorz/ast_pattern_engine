import ast
from ast_pattern_engine.nodes.basic import Collect, WildCard
from ast_pattern_engine.engine import match_sequence


def test_match_sequence_returns_non_overlapping_bindings():
    nodes = [ast.parse(text).body[0] for text in ("a = 1", "b = 2", "c = 3")]
    pattern = [Collect(WildCard(), "assign")]

    results = match_sequence(pattern, nodes)

    assert len(results) == 3
    assert all("assign" in match for match in results)
    assert [match["assign"] for match in results] == nodes
