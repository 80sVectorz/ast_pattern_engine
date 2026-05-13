"""Dictionary get method rewrite example.

This example shows how to use the AST Pattern Engine to rewrite all `dict.get("key")` calls
into direct dictionary subscript access `dict["key"]`.
"""

from typing import Any
import ast
from ast_pattern_engine import BottomUpPatternTransformer, Bind, NodePattern


def test_dict_get_rewrite() -> None:
    source = "value = my_dict.get(other_dict.get('foo'))"
    tree = ast.parse(source)

    # 1. Build the explicit structural pattern
    # Matches: <obj>.get(<key>)
    pattern = [
        NodePattern(
            ast.Call,
            func=NodePattern(ast.Attribute, attr="get", value=Bind("obj")),
            args=Bind("key"),
        )
    ]

    # 2. Define the rewrite logic
    def rewrite_dict_get(bindings: dict[str, Any]) -> list[ast.AST]:
        obj = bindings["obj"]
        key = bindings["key"][0]  # args is a list

        # Return the new node to replace the matched node
        new_node = ast.Subscript(value=obj, slice=key, ctx=ast.Load())
        return [new_node]

    # 3. Apply the transformer
    # We use BottomUpPatternTransformer so that nested `.get()` calls
    # are transformed from the inside-out successfully.
    transformer = BottomUpPatternTransformer(pattern, {"key": rewrite_dict_get})
    transformer.visit(tree)

    new_source = ast.unparse(tree)
    print("Rewritten source:\n", new_source)

    # Assert for validation
    assert new_source == "value = my_dict[other_dict['foo']]"


if __name__ == "__main__":
    test_dict_get_rewrite()
