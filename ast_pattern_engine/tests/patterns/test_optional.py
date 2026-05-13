from ast_pattern_engine.nodes.basic import Collect, WildCard
from ast_pattern_engine.nodes.sequences import Optional, OneOf, PatternGroup


def test_optional_and_oneof_construction():
    # Verify that Optional and OneOf can be nested inside PatternGroup
    # without any side-effects during construction (no message passing needed).
    pattern = PatternGroup(
        [
            Optional(Collect(WildCard(), "opt"), key="opt_key"),
            OneOf([Collect(WildCard(), "one")], key="one_key"),
        ]
    )
    assert pattern is not None
