![PyPI - Version](https://img.shields.io/pypi/v/ast-pattern-engine)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/ast-pattern-engine)
![Pytest](https://img.shields.io/badge/pytest-tested-orange)
![MIT License](https://img.shields.io/badge/License-MIT-blue)
![Codecov](https://codecov.io/gh/80sVectorz/ast_pattern_engine/branch/main/graph/badge.svg)
![GitHub Workflow Status](https://github.com/80sVectorz/ast_pattern_engine/actions/workflows/ci.yml/badge.svg)

# AST Pattern Engine

A powerful, programmatic, regex-inspired AST pattern matching and manipulation library for Python.

## Philosophy: The "Gradual Pipeline"

Instead of relying on fragile regex on source code or magic string-to-AST parsers, `ast_pattern_engine` provides an internal DSL for building explicit, structural patterns. 

It is designed with a "Gradual Pipeline" philosophy: instead of writing one massive, monolithic pattern expression to do everything at once, you chain small, focused patterns and visitors. Like casting a wide net and progressively filtering down in stages. 

## Installation

```bash
pip install ast_pattern_engine
```
```bash
uv add ast_pattern_engine
```

*(Requires Python 3.10+)*

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

*(See the `examples/` directory for full runnable code).*

## Primitives

The engine provides several primitives to build robust sequences:
- `NodePattern`: Match specific AST node types and assert on their fields.
- `Collect` / `Bind`: Extract sub-trees out of a matched pattern to use in your handlers.
- `OneOf`: Match one of several possible patterns (similar to regex `|`).
- `Repetition`: Match a pattern sequentially 1 or more times (similar to regex `*` and `+`).
- `Optional`: Match a pattern 0 or 1 times (similar to regex `?`).
- `Filter`: Apply arbitrary Python lambdas to check node states during matching.

## Templates

To reduce boilerplate when building patterns, the library includes a `templates` module with helpers for common operations:
- `match_call(func_name, **kwargs)`
- `match_assign(target_name, value)`
- `match_in_expr(pattern)`
