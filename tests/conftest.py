import ast
import os


def names_and_imports(repo_root, path):
    """AST-scan a repo-relative Python file for imported modules and referenced names.

    Shared by the probe / causal-probe / llm-parrot structural firewalls, which each
    carried a byte-for-byte-equivalent scanner before consolidation.
    """
    with open(os.path.join(repo_root, path)) as handle:
        tree = ast.parse(handle.read(), filename=path)
    imports, names = set(), set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.add(node.module or "")
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
    return imports, names
