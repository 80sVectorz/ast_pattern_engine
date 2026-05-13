from typing import Any
from collections.abc import Sequence

from ast_pattern_engine.core import Pattern
from ast_pattern_engine.nodes.sequences import (
    PatternGroup,
    Repetition,
    Optional,
    OneOf,
)


def _match_patterns(
    pattern_nodes: Sequence[Pattern],
    nodes: list[Any],
    pos: int,
    bindings: dict[str, Any],
    *,
    _force_list: bool = False,
) -> list[tuple[dict[str, Any], int]]:
    """Match a sequence of patterns to a sequence of AST nodes."""
    if not pattern_nodes:
        return [(bindings, pos)]
    first, *remaining = pattern_nodes
    out: list[tuple[dict[str, Any], int]] = []

    match first:
        case PatternGroup(pattern=sub_pattern, key=key):
            res = _match_patterns(sub_pattern, nodes, pos, dict(bindings), _force_list=_force_list)
            if res:
                new_bindings = res[-1][0]
                if key is not None:
                    new_bindings = {key: new_bindings}

                out.append((new_bindings, res[-1][1]))

        case Repetition(
            pattern=sub_pattern, min_matches=min_matches, max_matches=max_matches
        ):
            new_bindings = dict(bindings)
            n_reps = 0
            while n_reps < (max_matches or len(nodes)) and pos < len(nodes):
                res = _match_patterns([sub_pattern], nodes, pos, dict(new_bindings), _force_list=True)
                if not res:
                    break
                new_bindings, pos = res[-1]
                n_reps += 1

            if n_reps >= min_matches:
                out.append((new_bindings, pos))

        case OneOf(patterns=sub_patterns, key=key, strict=strict):
            new_bindings = dict(bindings)
            new_pos = pos
            n_matches = 0
            for pattern in sub_patterns:
                res = _match_patterns([pattern], nodes, pos, dict(bindings), _force_list=_force_list)
                if res:
                    n_matches += 1
                    if n_matches == 1:
                        # Store only the first match.
                        new_bindings, new_pos = res[-1]
                    if not strict:
                        # No need to check for more matches in non strict mode.
                        break

            pos = new_pos

            if n_matches == 1:
                if first.key is not None:
                    new_bindings = {first.key: new_bindings}
                # If the pattern is strict it expects only one match.
                # n_matches cannot be > 1 when not strict because of early exiting in the loop above.
                out.append((new_bindings, pos))

        case Optional(pattern=sub_pattern, key=key):
            res = _match_patterns([sub_pattern], nodes, pos, dict(bindings), _force_list=_force_list)
            if res:
                new_bindings, new_pos = res[-1]
                if key is not None:
                    new_bindings = {key: new_bindings}
                out.append((new_bindings, new_pos))
            else:
                # The pattern is optional, so if it fails, we consume 0 nodes
                # and continue matching the rest of the sequence.
                out.append((bindings, pos))

        case _:
            # single node pattern
            if pos < len(nodes):
                res = first.match_node(nodes[pos], dict(bindings), _force_list=_force_list)
                if res is not None:
                    out.append((res, pos + 1))

    # Match remaining patterns
    if out and remaining:
        rem_res = _match_patterns(remaining, nodes, out[-1][1], out[-1][0], _force_list=_force_list)
        if not rem_res:
            return []
        out.extend(rem_res)

    return out


def match_sequence(
    patterns: Sequence[Pattern], nodes: list[Any]
) -> list[dict[str, Any]]:
    """Return list of binding dicts for non-overlapping matches in `nodes`.

    Args:
        patterns: The sequence of patterns to match.
        nodes: The list of AST nodes to match against.

    Returns:
        List of binding dictionaries for each successful match.
    """
    results: list[dict[str, Any]] = []
    i = 0
    while i < len(nodes):
        m = _match_patterns(patterns, nodes, i, {})
        if not m:
            i += 1
            continue
        b, new_pos = m[-1]
        results.append(b)
        i = new_pos
    return results
