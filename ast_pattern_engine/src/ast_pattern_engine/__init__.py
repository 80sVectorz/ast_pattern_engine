"""AST Pattern Engine - A programmatic, regex-inspired AST pattern matching and manipulation library."""

from .core import Pattern, SequencePattern
from .engine import match_sequence
from .nodes.basic import (
    NodePattern,
    WildCard,
    Collect,
    Filter,
    Not,
    Contains,
    AllOf,
    AnyOf,
    Bind,
)
from .nodes.sequences import (
    Repetition,
    PatternGroup,
    OneOf,
    Optional,
)
from .visitors import (
    PatternTransformer,
    BottomUpPatternTransformer,
    PatternFinder,
    SingleOccurrenceFinder,
)
from .templates import (
    match_in_expr,
    match_call,
    match_assign,
)

__all__ = [
    # Core
    "Pattern",
    "SequencePattern",
    "match_sequence",
    # Basic Nodes
    "NodePattern",
    "WildCard",
    "Collect",
    "Filter",
    "Not",
    "Contains",
    "AllOf",
    "AnyOf",
    "Bind",
    # Sequences
    "Repetition",
    "PatternGroup",
    "OneOf",
    "Optional",
    # Visitors
    "PatternTransformer",
    "BottomUpPatternTransformer",
    "PatternFinder",
    "SingleOccurrenceFinder",
    # Templates
    "match_in_expr",
    "match_call",
    "match_assign",
]
