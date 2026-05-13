import ast
from typing import Any
from collections.abc import Sequence, Callable

from ast_pattern_engine.core import Pattern
from ast_pattern_engine.engine import _match_patterns

type ReplaceResult = ast.AST | list[ast.AST] | None


class PatternTransformer(ast.NodeTransformer):
    """Pattern find & replace tool with a "first come first served" replace approach.

    The transformer walks list fields left-to-right, matching the provided
    pattern sequence against non-overlapping spans. Every successful match
    appends the binding dict to self.matches before running actions.

    The actions mapping decides how collected bindings rewrite the tree:

    - 'handler': callable receiving the full bindings dict and returning
      list[ast.AST] to splice in place of the collected anchor(s).
    - None: delete every node collected under that key.

    This makes the transformer suitable for structural rewrites driven by
    Collect/Repetition patterns while also exposing the matches for
    analysis or testing.

    Args:
        pattern: Sequence of pattern nodes matched against each candidate span.
        actions: Mapping from collect keys to replacement handlers or None.
    """

    def __init__(
        self,
        pattern: Sequence[Pattern],
        actions: dict[str, Callable[[dict[str, Any]], list[ast.AST]] | None],
    ):
        super().__init__()
        self.pattern = pattern
        self.actions = actions
        self.matches: list[dict[str, Any]] = []

    def _record(self, bindings: dict[str, Any]) -> None:
        """Internal helper so we have just one place that appends."""
        self.matches.append(bindings)

    def _normalize_replace_for_nonlist(self, rep: ReplaceResult, field: str) -> ast.AST:
        """Normalize a replacement for a non-list field.

        - ast.AST -> ast.AST
        - [ast.AST] with len=1 -> element
        - None or list with len!=1 -> error
        """
        if isinstance(rep, ast.AST):
            return rep
        if isinstance(rep, list):
            if len(rep) == 1 and isinstance(rep[0], ast.AST):
                return rep[0]
            raise ValueError(
                f"Cannot replace non-list field {field} with {len(rep)} nodes"
            )
        raise ValueError(f"Cannot delete non-list field {field}")

    # helpers to interpret collected values

    @staticmethod
    def _as_nodes(value: Any) -> list[ast.AST]:
        """Extract AST nodes from arbitrarily nested values.

        The value may be:
        - ast.AST: returned as a single-element list
        - list: flattened recursively
        - dict: values scanned recursively (no special key required)
        - other: ignored

        Returns:
            All AST nodes found, in encounter order.
        """
        out: list[ast.AST] = []

        def rec(v: Any) -> None:
            if isinstance(v, ast.AST):
                out.append(v)
            elif isinstance(v, list):
                for it in v:
                    rec(it)
            elif isinstance(v, dict):
                for it in v.values():
                    rec(it)

        rec(value)
        return out

    def _replace_within(
        self,
        parent: ast.AST,
        target: ast.AST,
        repl: list[ast.AST],
    ) -> bool:
        """Replace `target` somewhere inside `parent` with `repl`.

        Returns:
            Boolean indicating whether a replacement was performed.
        """

        def walk(node: ast.AST) -> bool:
            for field, val in ast.iter_fields(node):
                if val is target:
                    if len(repl) != 1:
                        raise ValueError(
                            f"Cannot replace non-list field {field} with {len(repl)} nodes"
                        )
                    setattr(node, field, repl[0])
                    return True
                if isinstance(val, list):
                    for i, elem in enumerate(val):
                        if elem is target:
                            val[i : i + 1] = repl
                            return True
                if isinstance(val, ast.AST) and walk(val):
                    return True
                if isinstance(val, list):
                    for elem in val:
                        if isinstance(elem, ast.AST) and walk(elem):
                            return True
            return False

        return walk(parent)

    def _delete_within(self, parent: ast.AST, target: ast.AST) -> bool:
        """Delete `target` if it appears in a list field somewhere inside `parent`.

        Returns:
            Boolean indicating whether a deletion was performed.
        """

        def walk(node: ast.AST) -> bool:
            for _, val in ast.iter_fields(node):
                if isinstance(val, list):
                    i = 0
                    while i < len(val):
                        elem = val[i]
                        if elem is target:
                            del val[i]
                            return True
                        if isinstance(elem, ast.AST) and walk(elem):
                            return True
                        i += 1
                elif isinstance(val, ast.AST) and walk(val):
                    return True
            return False

        return walk(parent)

    def _contains(self, root: ast.AST, target: ast.AST) -> bool:
        """Check if target occurs anywhere in root's subtree.

        Returns:
            Boolean indicating if target occurs anywhere in root's subtree.
        """
        if root is target:
            return True
        for _, v in ast.iter_fields(root):
            if isinstance(v, ast.AST):
                if self._contains(v, target):
                    return True
            elif isinstance(v, list):
                for it in v:
                    if isinstance(it, ast.AST) and self._contains(it, target):
                        return True
        return False

    def _find_owner_in_span(
        self, span: list[ast.AST], anchor: ast.AST
    ) -> ast.AST | None:
        """Find the owner of an anchor in a span of nodes.

        Returns:
            The first node in span whose subtree contains anchor.
            None if no such node exists.
        """
        for n in span:
            if self._contains(n, anchor):
                return n
        return None

    # plan replacements / removals for node sequences

    def _plan(self, seq: list[ast.AST]) -> tuple[dict[int, list[ast.AST]], set[int]]:
        repl: dict[int, list[ast.AST]] = {}
        remove: set[int] = set()
        i = 0
        while i < len(seq):
            mtch = _match_patterns(self.pattern, seq, i, {})
            if not mtch:
                i += 1
                continue

            bindings, new_pos = mtch[0]
            self._record(bindings)
            span_nodes = seq[i:new_pos]

            for key, action in self.actions.items():
                if key not in bindings:
                    continue

                collected = self._as_nodes(bindings[key])
                if not collected:
                    continue

                list_anchors = [n for n in collected if n in span_nodes]

                if action is None:
                    # Remove only list elements; ignore nested nodes
                    if list_anchors:
                        remove.update(id(n) for n in list_anchors)
                    else:
                        # Best-effort nested delete, but soft-fail if not in a list field
                        owner = (
                            self._find_owner_in_span(span_nodes, collected[0])
                            or span_nodes[0]
                        )
                        for n in collected:
                            self._delete_within(owner, n)
                    continue

                # Replacement
                r = action(bindings) or []
                if not isinstance(r, list):
                    raise TypeError("Handler must return `list[ast.AST]`.")

                if list_anchors:
                    # Replace the first list element anchor and remove the rest
                    repl[id(list_anchors[0])] = r
                    remove.update(id(n) for n in list_anchors[1:])
                else:
                    # Replace nested child within its owner
                    owner = (
                        self._find_owner_in_span(span_nodes, collected[0])
                        or span_nodes[0]
                    )
                    # Try each collected node until one is found in owner
                    replaced = False
                    for n in collected:
                        if self._replace_within(owner, n, r):
                            replaced = True
                            break
                    if not replaced:
                        raise ValueError(
                            "Could not locate collected child in matched subtree for in-place replacement."
                        )

            i = new_pos

        return repl, remove

    def generic_visit(self, node: ast.AST) -> ast.AST:
        """Transform children, then apply sequential matching in list fields."""
        for field, old_value in ast.iter_fields(node):
            if isinstance(old_value, list):
                # Visit children
                children: list[ast.AST] = []
                for v in old_value:
                    if isinstance(v, ast.AST):
                        nv = self.visit(v)
                        if nv is None:
                            continue
                        if not isinstance(nv, ast.AST):
                            raise TypeError("List fields must contain AST nodes.")
                        children.append(nv)
                    else:
                        children.append(v)

                # Plan and splice sequential replacements/removals
                if children and all(isinstance(c, ast.AST) for c in children):
                    replace, remove = self._plan(children)
                    new_children: list[ast.AST] = []
                    for ch in children:
                        rid = id(ch)
                        if rid in replace:
                            new_children.extend(replace[rid])
                        elif rid not in remove:
                            new_children.append(ch)
                    setattr(node, field, new_children)
                else:
                    setattr(node, field, children)

            elif isinstance(old_value, ast.AST):
                visited = self.visit(old_value)
                if isinstance(visited, ast.AST):
                    rep = self._maybe_replace(visited)
                    if rep is not None:
                        new_node = self._normalize_replace_for_nonlist(rep, field)
                        setattr(node, field, new_node)
                else:
                    # Deleting or expanding is not valid for non-list fields.
                    setattr(node, field, old_value)

        return node

    def _maybe_replace(self, node: ast.AST) -> ast.AST | list[ast.AST] | None:
        """Try to match `self.pattern` against just `node` and apply actions.

        Returns:
        -------
            - ast.AST: replace this node with a single node
            - list[ast.AST]: splice multiple nodes (only valid in list fields)
            - None: delete this node
        """
        res = _match_patterns(self.pattern, [node], 0, {})
        if not res:
            return None

        bindings, _ = res[0]
        self._record(bindings)

        did_inplace = False

        for key, action in self.actions.items():
            if key not in bindings:
                continue

            collected = self._as_nodes(bindings[key])

            # Case 1: the action targets THIS node -> replace/delete the node itself
            if node in collected:
                if action is None:
                    return None
                repl = action(bindings) or []
                if not isinstance(repl, list):
                    raise TypeError("Handler must return list[ast.AST].")
                if len(repl) == 0:
                    return None
                if len(repl) == 1:
                    return repl[0]
                return repl  # multi-element expansion only valid in list fields

            # Case 2: the action targets nested anchors -> mutate in place
            if action is None:
                for n in collected:
                    did_inplace |= self._delete_within(node, n)
            else:
                repl = action(bindings) or []
                if not isinstance(repl, list):
                    raise TypeError("Handler must return list[ast.AST].")
                for n in collected:
                    did_inplace |= self._replace_within(node, n, repl)

        # If we only did in-place nested edits, keep this node (signal "no top-level replace")
        return None


class BottomUpPatternTransformer(ast.NodeTransformer):
    """Like PatternTransformer, but applies changes *after* visiting all children.

    This enables bottom-up rewriting (i.e., transforming from the leaves upward).

    Args:
        pattern: Sequence of pattern nodes matched against each candidate span.
        actions: Mapping from collect keys to replacement handlers or None.
    """

    def __init__(
        self,
        pattern: Sequence[Pattern],
        actions: dict[str, Callable[[dict[str, Any]], list[ast.AST]] | None],
    ):
        super().__init__()
        self.pattern = pattern
        self.actions = actions
        self.matches: list[dict[str, Any]] = []

    def _record(self, bindings: dict[str, Any]) -> None:
        self.matches.append(bindings)

    @staticmethod
    def _as_nodes(value: Any) -> list[ast.AST]:
        """Extract AST nodes from arbitrarily nested values.

        Returns:
            All AST nodes found within value.
        """
        out: list[ast.AST] = []

        def rec(v: Any) -> None:
            if isinstance(v, ast.AST):
                out.append(v)
            elif isinstance(v, list):
                for it in v:
                    rec(it)
            elif isinstance(v, dict):
                for it in v.values():
                    rec(it)

        rec(value)
        return out

    def visit(self, node: ast.AST) -> ast.AST | list[ast.AST] | None:
        # First, transform children recursively (bottom-up)
        for field, value in list(ast.iter_fields(node)):
            if isinstance(value, list):
                new_list = []
                for item in value:
                    if isinstance(item, ast.AST):
                        new_item = self.visit(item)
                        if new_item is None:
                            continue
                        elif isinstance(new_item, list):
                            new_list.extend(new_item)
                        else:
                            new_list.append(new_item)
                    else:
                        new_list.append(item)
                setattr(node, field, new_list)
            elif isinstance(value, ast.AST):
                new_value = self.visit(value)
                setattr(node, field, new_value)

        # Then apply pattern matching to this node
        res = _match_patterns(self.pattern, [node], 0, {})
        if res:
            bindings, _ = res[0]
            self._record(bindings)
            for key, action in self.actions.items():
                if key in bindings:
                    if action is not None:
                        replacements = action(bindings)
                        if len(replacements) == 0:
                            return None
                        return (
                            replacements[0] if len(replacements) == 1 else replacements
                        )
                    else:
                        return None  # delete the matched node

        return node


class PatternFinder(ast.NodeVisitor):
    """Collect bindings for every occurrence of `pattern` in an AST.

    Args:
        pattern: Sequence of pattern nodes to search for.
    """

    def __init__(self, pattern: Sequence[Pattern]):
        super().__init__()
        self.visited: set[int] = set()
        self.pattern = pattern
        self.matches: list[dict[str, Any]] = []

    def generic_visit(self, node: ast.AST):
        if id(node) in self.visited:
            return

        self.visited.add(id(node))
        res = _match_patterns(self.pattern, [node], 0, {})
        if res:
            self.matches.append(res[0][0])
        for _, val in ast.iter_fields(node):
            if isinstance(val, list):
                if len(self.pattern) > 1:
                    self._scan_list(val)
                for elem in val:
                    if isinstance(elem, ast.AST):
                        self.visit(elem)
            elif isinstance(val, ast.AST):
                self.visit(val)

    def _scan_list(self, seq: list[ast.AST]):
        i = 0
        while i < len(seq):
            res = _match_patterns(self.pattern, seq, i, {})
            if res:
                binds, new_pos = res[-1]
                self.matches.append(binds)
                i = new_pos
            else:
                i += 1


class SingleOccurrenceFinder(ast.NodeVisitor):
    """Quickly checks whether a single match of the given pattern sequence exists in an AST.

    Returns True on the first match, short-circuiting the traversal.

    Args:
        pattern: Sequence of pattern nodes to search for.
    """

    match_node: ast.AST | None
    match_bindings: dict[str, Any]

    def __init__(self, pattern: Sequence[Pattern]):
        super().__init__()
        self.match_node = None
        self.match_bindings = {}
        self.pattern = pattern
        self.found = False

    def visit(self, node: ast.AST):
        if self.found:
            return  # short-circuit: we've already found a match

        res = _match_patterns(self.pattern, [node], 0, {})
        if res:
            self.found = True
            self.match_node = node
            self.match_bindings = res[0][0]
            return

        # Continue traversal
        for _, val in ast.iter_fields(node):
            if isinstance(val, list):
                for item in val:
                    if isinstance(item, ast.AST):
                        self.visit(item)
                        if self.found:
                            return
            elif isinstance(val, ast.AST):
                self.visit(val)
                if self.found:
                    return

    def found_match(self) -> bool:
        return self.found
