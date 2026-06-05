# AST Pattern Engine

A powerful, programmatic, regex-inspired AST pattern matching and manipulation library for Python.

## Quick Start

Here is a simple pipeline that rewrites `dict.get("key")` calls into direct subscript access `dict["key"]`:

```python
from typing import Any
import ast
from ast_pattern_engine import BottomUpPatternTransformer, Bind, NodePattern

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
# We use BottomUpPatternTransformer so nested `.get()` calls
# are safely transformed from the inside-out.
transformer = BottomUpPatternTransformer(pattern, {"key": rewrite_dict_get})
transformer.visit(tree)

print(ast.unparse(tree))
# Output: value = my_dict[other_dict['foo']]
```

For more in-depth examples, refer to the [Guide](guide.md) or the [API Reference](reference/core.md).
