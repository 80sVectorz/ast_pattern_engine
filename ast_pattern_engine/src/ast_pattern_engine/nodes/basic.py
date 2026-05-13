from __future__ import annotations
from collections.abc import Sequence
import ast
from typing import Any
from collections.abc import Callable

from ast_pattern_engine.core import Pattern
from ast_pattern_engine.engine import _match_patterns

from ast_pattern_engine.visitors import SingleOccurrenceFinder


class Bind(Pattern):
    """Bind the current node to `name`.

    This is syntactic sugar for:
        >>> Collect(WildCard(), "x")

    Args:
        key: The key to bind the node(s) or value(s) to.
    """

    key: str

    def __init__(self, key: str):
        self.key = key

    def match_node(self, node: Any, bindings: dict[str, Any] | None = None, *, _force_list: bool = False):
        bindings = bindings or {}
        if self.key in bindings:
            if not _force_list:
                return None
            bindings[self.key] = self._to_list(bindings[self.key]) + [node]
        else:
            bindings[self.key] = [node] if _force_list else node
        return bindings


class WildCard(Pattern):
    """Matches any node."""

    def __init__(self): ...

    def match_node(self, node: Any, bindings: dict[str, Any] | None = None, *, _force_list: bool = False):
        bindings = bindings or {}
        return bindings


class NodePattern(Pattern):
    """Match an AST node of `node_type` with constraints on its fields.

    Args:
        node_type: The AST node class to match (e.g., ast.Assign).
        **field_patterns: Patterns or exact values to match against the node's fields.
    """

    def __init__(self, node_type: type[ast.AST], **field_patterns: Pattern | Any):
        self.node_type = node_type
        self.field_patterns = field_patterns

    def match_node(self, node: Any, bindings: dict[str, Any] | None = None, *, _force_list: bool = False):
        bindings = bindings or {}
        if not isinstance(node, self.node_type):
            return None
        merged = dict(bindings)
        for field, pat in self.field_patterns.items():
            val = getattr(node, field, None)
            if isinstance(pat, Pattern):
                if val is None:
                    return None
                # Match list-valued field
                if isinstance(val, list) and not isinstance(pat, Bind):
                    res = _match_patterns([pat], val, 0, {}, _force_list=_force_list)
                    if not res:
                        return None
                    sub_bind = res[-1][0]
                else:
                    sub_bind = pat.match_node(val, {}, _force_list=_force_list)
                    if sub_bind is None:
                        return None
                # merge sub bindings
                for k, v in sub_bind.items():
                    if k in merged:
                        if not _force_list:
                            return None
                        merged[k] = self._to_list(merged[k]) + self._to_list(v)
                    else:
                        merged[k] = (
                            self._to_list(v) if _force_list else v
                        )
            else:
                if val != pat:
                    return None
        return merged


class Collect(Pattern):
    """Collect the matched node under `key` and merge sub-bindings into current scope.

    Args:
        pattern: The pattern to match.
        key: The key to bind the pattern result to.
    """

    pattern: Pattern
    """The pattern to match."""

    key: str
    """The key to bind the pattern result to."""

    def __init__(self, pattern: Pattern, key: str):
        self.pattern = pattern
        self.key = key

    def match_node(
        self, node: Any, bindings: dict[str, Any] | None = None, *, _force_list: bool = False
    ) -> None | dict[str, Any]:
        bindings = bindings or {}
        # Collect is a binding boundary — inner patterns always see _force_list=False
        inner = self.pattern.match_node(node, {}, _force_list=False)
        if inner is None:
            return None
        merged = dict(bindings)

        if _force_list:
            if inner:
                # Inside a repetition wrapper with inner bindings;
                # append the inner-dict itself to the list under key.
                if self.key in merged:
                    merged[self.key].append(inner)
                else:
                    merged[self.key] = [inner]
                return merged
            else:
                if self.key in merged:
                    merged[self.key].append(node)
                else:
                    merged[self.key] = [node]
                return merged

        # Outside repetition - store node and merge inner bindings
        if self.key in merged:
            return None  # Scalar expected, duplicate found
        merged[self.key] = node
        for k, v in inner.items():
            if k in merged:
                return None  # Scalar expected, duplicate found
            merged[k] = v
        return merged


class Filter(Pattern):
    """Match nodes where `predicate(node)` returns `True` and optionally bind `node` to `key`.

    Args:
        predicate: A callable that returns True if the node matches.
        key: Optional key to bind the matched node to.
    """

    predicate: Callable[[Any], bool]
    """The predicate to match."""

    key: str | None
    """The key to bind the node to."""

    def __init__(self, predicate: Callable[[Any], bool], key: str | None = None):
        self.predicate = predicate
        self.key = key

    def match_node(self, node: Any, bindings: dict[str, Any] | None = None, *, _force_list: bool = False):
        bindings = bindings or {}
        if not self.predicate(node):
            return None
        if self.key is None:
            return bindings
        if self.key in bindings:
            if not _force_list:
                return None
            bindings[self.key] = self._to_list(bindings[self.key]) + [node]
        else:
            bindings[self.key] = [node] if _force_list else node
        return bindings


class Not(Pattern):
    """Match any node that is not matched by `pattern`.

    Args:
        pattern: The pattern that must fail for this to match.
    """

    def __init__(self, pattern: Pattern):
        self.pattern = pattern

    def match_node(self, node: Any, bindings: dict[str, Any] | None = None, *, _force_list: bool = False):
        bindings = bindings or {}

        # Use _match_patterns so that SequencePatterns (like OneOf) don't
        # raise NotImplementedError when their .match() is called directly.
        res = _match_patterns([self.pattern], [node], 0, {})

        if res:
            return None
        return bindings


class Contains(Pattern):
    """Matches a pattern that is contained anywhere within the node's sub-tree.

    Args:
        pattern: The pattern or sequence of patterns to search for in the sub-tree.
    """

    def __init__(self, pattern: Sequence[Pattern]):
        self.pattern = list(pattern)

    def match_node(self, node: Any, bindings: dict[str, Any] | None = None, *, _force_list: bool = False):
        bindings = bindings or {}
        finder = SingleOccurrenceFinder(self.pattern)
        finder.visit(node)

        if finder.found_match():
            found_bindings = finder.match_bindings

            merged = dict(bindings)
            for k, v in found_bindings.items():
                if k in merged:
                    return None  # Duplicate key
                merged[k] = v
            return merged

        return None


class AllOf(Pattern):
    """Matches if all patterns in the sequence match the node.

    Args:
        patterns: Sequence of patterns that must all match the node.
    """

    patterns: Sequence[Pattern]
    """The patterns to match."""

    def __init__(self, patterns: Sequence[Pattern]):
        self.patterns = list(patterns)

    def match_node(self, node: Any, bindings: dict[str, Any] | None = None, *, _force_list: bool = False):
        bindings = bindings or {}
        new_bindings = dict(bindings)

        for pattern in self.patterns:
            new_bindings = pattern.match_node(node, new_bindings, _force_list=_force_list)
            if new_bindings is None:
                return None
        return new_bindings


class AnyOf(Pattern):
    """Match any of the patterns in the sequence.

    Args:
        patterns: Sequence of patterns where at least one must match.
    """

    patterns: list[Pattern]
    """The patterns to match."""

    def __init__(self, patterns: Sequence[Pattern]):
        self.patterns = list(patterns)

    def match_node(self, node: Any, bindings: dict[str, Any] | None = None, *, _force_list: bool = False):
        bindings = bindings or {}
        merged = dict(bindings)
        matched_any = False

        for p in self.patterns:
            # Test each pattern against the original node
            res = p.match_node(node, {}, _force_list=_force_list)
            if res is not None:
                matched_any = True
                # Merge successful bindings
                for k, v in res.items():
                    if k in merged:
                        return None  # duplicate key safeguard
                    merged[k] = v

        if not matched_any:
            return None

        return merged
