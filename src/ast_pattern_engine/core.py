from __future__ import annotations
import ast
from typing import Any


class Pattern(ast.AST):
    """Base class for AST matching patterns."""

    # public API
    def match_node(
        self,
        node: object,
        bindings: dict[str, object] | None = None,
        *,
        _force_list: bool = False,
    ):
        """Match *node* and return updated *bindings* or *None*."""
        raise NotImplementedError

    # helpers
    @staticmethod
    def _to_list(val: Any) -> list[Any]:
        return val if isinstance(val, list) else [val]


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
