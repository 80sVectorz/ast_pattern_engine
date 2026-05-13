import ast
from ast_pattern_engine.nodes.basic import Collect, WildCard, NodePattern
from ast_pattern_engine.nodes.sequences import PatternGroup
from ast_pattern_engine.engine import _match_patterns, match_sequence


def test_pattern_group_collects_inner_bindings_under_key():
    nodes = [ast.parse(src).body[0].value for src in ("1", "2")]  # type: ignore
    pattern = [
        PatternGroup(
            [
                Collect(WildCard(), "left"),
                Collect(WildCard(), "right"),
            ],
            key="pair",
        )
    ]

    result = _match_patterns(pattern, nodes, 0, {})

    assert result, "Expected PatternGroup to match"
    bindings, end_pos = result[0]
    assert end_pos == len(nodes)
    assert "pair" in bindings
    pair_bindings = bindings["pair"]
    assert isinstance(pair_bindings, dict)
    assert pair_bindings["left"] is nodes[0]
    assert pair_bindings["right"] is nodes[1]


def test_pattern_group_advances_position_for_following_patterns():
    nodes = [ast.parse(text).body[0] for text in ("a = 1", "b = 2", "c = 3")]
    pattern = [
        PatternGroup(
            [
                Collect(WildCard(), "first"),
                Collect(WildCard(), "second"),
            ],
            key="pair",
        ),
        Collect(WildCard(), "third"),
    ]

    matches = match_sequence(pattern, nodes)

    assert matches, "Expected PatternGroup to enable full sequence match"
    bindings = matches[0]
    assert "pair" in bindings
    assert bindings["third"] is nodes[2]
    pair_bindings = bindings["pair"]
    assert pair_bindings["first"] is nodes[0]
    assert pair_bindings["second"] is nodes[1]


def test_pattern_group_requires_full_match():
    nodes = [ast.parse("1").body[0].value, ast.parse("x=2").body[0]]
    pattern = [
        PatternGroup(
            [
                Collect(NodePattern(ast.Constant), "first"),
                Collect(NodePattern(ast.Constant), "second"),
            ],
            key="pair",
        )
    ]

    matches = match_sequence(pattern, nodes)
    assert len(matches) == 0
