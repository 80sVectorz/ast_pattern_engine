import ast
from ast_pattern_engine.nodes.basic import Collect, NodePattern
from ast_pattern_engine.visitors import PatternFinder


def test_pattern_finder_collects_node_matches():
    tree = ast.parse("a = 1\nb = 2\nc = 3")
    pattern = [Collect(NodePattern(ast.Assign), "assign")]

    finder = PatternFinder(pattern)
    finder.visit(tree)

    assert len(finder.matches) == 3
    assert [match["assign"] for match in finder.matches] == tree.body


def test_pattern_finder_scan_list():
    tree = ast.parse("a = 1\nb = 2\nc = 3")
    # A sequence of length 2 to trigger `_scan_list` len(self.pattern) > 1 branch
    pattern = [
        Collect(NodePattern(ast.Assign), "a"),
        Collect(NodePattern(ast.Assign), "b"),
    ]
    finder = PatternFinder(pattern)
    finder.visit(tree)
    # Print the matches to debug
    print("MATCHES:", finder.matches)
    assert len(finder.matches) == 1
