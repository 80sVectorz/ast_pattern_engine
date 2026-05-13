import ast
from ast_pattern_engine.nodes.basic import Collect, WildCard
from ast_pattern_engine.nodes.sequences import Repetition
from ast_pattern_engine.engine import _match_patterns

def test_collect_inside_one_or_more_accumulates_nodes():
    nodes = [ast.parse(str(i)).body[0].value for i in range(3)]  # type: ignore
    pattern = [Repetition(Collect(WildCard(), "item"))]

    result = _match_patterns(pattern, nodes, 0, {})

    assert result, "Expected the repetition to match"
    bindings, end_pos = result[0]
    assert end_pos == len(nodes)
    assert bindings["item"] == nodes


def test_one_or_more_requires_at_least_one_match():
    pattern = [Repetition(WildCard())]

    result = _match_patterns(pattern, [], 0, {})

    assert result == []
