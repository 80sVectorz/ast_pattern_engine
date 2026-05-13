import ast
from ast_pattern_engine.nodes.basic import Collect, NodePattern
from ast_pattern_engine.visitors import SingleOccurrenceFinder


def test_single_occurrence_finder_returns_first_match():
    tree = ast.parse("a = 1\nb = 2")
    pattern = [Collect(NodePattern(ast.Assign), "assign")]

    finder = SingleOccurrenceFinder(pattern)
    finder.visit(tree)

    assert finder.found_match()
    assert finder.match_node is tree.body[0]


def test_single_occurrence_finder_handles_absence():
    tree = ast.parse("pass")
    pattern = [Collect(NodePattern(ast.Assign), "assign")]

    finder = SingleOccurrenceFinder(pattern)
    finder.visit(tree)

    assert not finder.found_match()
    assert finder.match_node is None


def test_single_occurrence_finder_early_exit():
    tree = ast.parse("a = 1\nb = 2")
    pattern = [NodePattern(ast.Assign)]
    finder = SingleOccurrenceFinder(pattern)

    # We manually set found to True to test early exit in visit
    finder.found = True
    finder.visit(tree)
    assert finder.match_node is None  # Didn't actually match because it early exited
