from __future__ import annotations
from collections.abc import Sequence

from ast_pattern_engine.core import Pattern


class SequencePattern(Pattern):
    def match_node(
        self,
        node: object,
        bindings: dict[str, object] | None = None,
        *,
        _force_list: bool = False,
    ):
        # Matching is handled by engine._match_sequence
        raise NotImplementedError(
            f"{self.__class__.__name__} node does not support matching single AST node."
        )


class Repetition(SequencePattern):
    """Matches a single pattern zero or more times.

    Also supports specifying min and max match count thresholds

    Args:
        pattern: The pattern to match.
        min_matches: Minimum number of matches required. Default is 1.
        max_matches: Maximum number of allowed matches. Defaults to None.
    """

    pattern: Pattern
    min_matches: int
    max_matches: int | None

    def __init__(
        self,
        pattern: Pattern,
        min_matches: int = 1,
        max_matches: int | None = None,
    ):
        """Repetition node.

        Args:
            pattern: The pattern to match.
            min_matches: Minimum number of matches required. Default is 1.
            max_matches: Maximum number of allowed matches. Defaults to None.
        """
        self.pattern = pattern
        self.min_matches = min_matches
        self.max_matches = max_matches


class PatternGroup(SequencePattern):
    """Matches a compound pattern/pattern group to an AST node sequence.

    Args:
        pattern: The compound pattern to match.
        key: Optional key to bind the matched pattern to.
    """

    pattern: Sequence[Pattern]
    key: str | None

    def __init__(self, pattern: Sequence[Pattern], key: str | None = None) -> None:
        """PatternGroup node.

        Args:
            pattern: The compound pattern to match.
            key: Optional key to bind the matched pattern to.
        """
        self.pattern = list(pattern)
        self.key = key


class OneOf(SequencePattern):
    """Matches one of several patterns.

    Can be set to be strict and only match if *exactly* one pattern matches. If not
    set to be strict, the first successful match is returned.

    Args:
        patterns: The patterns to match
        strict: Whether to be strict and only match if *exactly* one pattern matches
        key: Optional key to bind the matched pattern to
    """

    patterns: list[Pattern]
    strict: bool
    key: str | None

    def __init__(
        self, patterns: Sequence[Pattern], strict: bool = False, key: str | None = None
    ) -> None:
        """OneOf node.

        Args:
            patterns: The patterns to match
            strict: Whether to be strict and only match if *exactly* one pattern matches
            key: Optional key to bind the matched pattern to
        """
        self.patterns = list(patterns)
        self.strict = strict
        self.key = key


class Optional(SequencePattern):
    """Matches a pattern zero or one times.

    Args:
        pattern: The pattern to match.
        key: Optional key to bind the matched pattern to.
    """

    pattern: Pattern
    key: str | None

    def __init__(self, pattern: Pattern, key: str | None = None) -> None:
        """Optional node.

        Args:
            pattern: The pattern to match.
            key: Optional key to bind the matched pattern to.
        """
        self.pattern = pattern
        self.key = key
