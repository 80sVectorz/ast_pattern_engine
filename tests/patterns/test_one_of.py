import ast
from ast_pattern_engine.nodes.basic import Collect, WildCard, NodePattern
from ast_pattern_engine.nodes.sequences import OneOf
from ast_pattern_engine.engine import _match_patterns, match_sequence


def test_one_of_non_strict_returns_first_match():
    nodes = [ast.parse(src).body[0] for src in ("1", "2")]
    pattern = [
        OneOf(
            [
                Collect(WildCard(), "first"),
                Collect(WildCard(), "second"),
            ],
            strict=False,
            key="pair",
        )
    ]

    matches = match_sequence(pattern, nodes)

    assert len(matches) == 2, "Expected OneOf to match"
    bindings1, bindings2 = matches
    assert "pair" in bindings1
    assert "pair" in bindings2
    pair_bindings1 = bindings1["pair"]
    pair_bindings2 = bindings2["pair"]
    assert isinstance(pair_bindings1, dict)
    assert isinstance(pair_bindings2, dict)
    assert "first" in pair_bindings1
    assert "second" not in pair_bindings1
    assert pair_bindings1["first"] is nodes[0]
    assert "first" in pair_bindings2
    assert "second" not in pair_bindings2
    assert pair_bindings2["first"] is nodes[1]


def test_one_of_strict_matches_exactly_one_pattern():
    # Section A: Test strict mode blocking multiple matches.
    nodes = [ast.parse(src).body[0] for src in ("1", "2")]
    pattern = [
        OneOf(
            [
                Collect(WildCard(), "first"),
                Collect(NodePattern(ast.Expr), "second"),
            ],
            strict=True,
            key="pair",
        )
    ]

    result = _match_patterns(pattern, nodes, 0, {})
    assert len(result) == 0, (
        "Expected strict OneOf not to match because multiple sub patterns match"
    )

    # Section B: Test strict mode with exactly one matching pattern for each line
    nodes = [ast.parse(src).body[0] for src in ("1", "x=2")]
    pattern = [
        OneOf(
            [
                Collect(NodePattern(ast.Expr), "first"),
                Collect(NodePattern(ast.Assign), "second"),
            ],
            strict=True,
            key="pair",
        )
    ]

    result = match_sequence(pattern, nodes)
    assert len(result) == 2, "Expected strict OneOf to match"
    bindings1, bindings2 = result
    assert "pair" in bindings1
    pair_bindings1 = bindings1["pair"]
    assert isinstance(pair_bindings1, dict)
    assert "first" in pair_bindings1
    assert pair_bindings1["first"] is nodes[0]
    assert "second" not in pair_bindings1

    assert "pair" in bindings2
    pair_bindings2 = bindings2["pair"]
    assert isinstance(pair_bindings2, dict)
    assert "first" not in pair_bindings2
    assert "second" in pair_bindings2
    assert pair_bindings2["second"] is nodes[1]
