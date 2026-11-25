"""Static analysis of Python source files without importing or executing them."""

import ast
from collections import Counter
from pathlib import Path

MAX_FILE_BYTES = 1_000_000
MAX_FILES = 500
_MATCH_NODE = getattr(ast, "Match", ())


def _arg_names(args):
    names = [arg.arg for arg in args.posonlyargs + args.args]
    if args.vararg:
        names.append("*" + args.vararg.arg)
    names.extend(arg.arg for arg in args.kwonlyargs)
    if args.kwarg:
        names.append("**" + args.kwarg.arg)
    return names


def _function_info(node):
    end_line = getattr(node, "end_lineno", node.lineno)
    return {
        "name": node.name,
        "line": node.lineno,
        "end_line": end_line,
        "length": end_line - node.lineno + 1,
        "args": _arg_names(node.args),
        "is_async": isinstance(node, ast.AsyncFunctionDef),
        "has_docstring": ast.get_docstring(node) is not None,
        "complexity": _function_complexity(node),
    }


def _function_complexity(node):
    decisions = 0
    pending = list(node.body)
    while pending:
        child = pending.pop()
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        if isinstance(
            child,
            (ast.If, ast.For, ast.AsyncFor, ast.While, ast.ExceptHandler, ast.IfExp),
        ):
            decisions += 1
        elif isinstance(child, ast.BoolOp):
            decisions += len(child.values) - 1
        elif _MATCH_NODE and isinstance(child, _MATCH_NODE):
            decisions += max(0, len(child.cases) - 1)
        pending.extend(ast.iter_child_nodes(child))
    return decisions + 1


def _class_info(node):
    methods = [
        _function_info(child)
        for child in node.body
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    return {
        "name": node.name,
        "line": node.lineno,
        "bases": [ast.unparse(base) for base in node.bases],
        "methods": methods,
        "has_docstring": ast.get_docstring(node) is not None,
    }


def _collect_imports(tree):
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                found.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = "." * node.level + (node.module or "")
            found.add(module)
    return sorted(found)


def analyze_source(source, path="<string>"):
    """Return classes, top-level functions, and imports for one source string."""
    result = {
        "path": path,
        "lines": len(source.splitlines()),
        "classes": [],
        "functions": [],
        "imports": [],
        "error": None,
    }

    try:
        tree = ast.parse(source, filename=path)
    except (SyntaxError, ValueError, RecursionError) as error:
        result["error"] = f"{type(error).__name__}: {error}"
        return result

    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            result["classes"].append(_class_info(node))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            result["functions"].append(_function_info(node))

    result["imports"] = _collect_imports(tree)
    return result


def analyze_directory(root, relative_paths):
    """Analyse .py files from relative_paths located under root."""
    root_path = Path(root).resolve()
    python_paths = [path for path in relative_paths if path.lower().endswith(".py")]

    skipped = max(0, len(python_paths) - MAX_FILES)
    python_paths = python_paths[:MAX_FILES]

    files = []
    for relative_path in python_paths:
        display = relative_path.replace("\\", "/")
        target = (root_path / display).resolve()

        if root_path not in target.parents:
            files.append({"path": display, "error": "Path is outside the repository"})
            continue
        if not target.is_file():
            continue
        if target.stat().st_size > MAX_FILE_BYTES:
            files.append({"path": display, "error": "File too large to analyse"})
            continue

        source = target.read_text(encoding="utf-8", errors="replace")
        files.append(analyze_source(source, display))

    analysed = [file for file in files if "lines" in file]
    import_counts = Counter()
    all_functions = []
    for item in analysed:
        for module in item["imports"]:
            import_counts[module.lstrip(".").split(".")[0] or "."] += 1
        for function in item["functions"]:
            all_functions.append({**function, "path": item["path"]})
        for class_info in item["classes"]:
            for method in class_info["methods"]:
                all_functions.append({**method, "path": item["path"]})

    documented_functions = sum(
        function["has_docstring"] for function in all_functions
    )
    function_count = len(all_functions)

    summary = {
        "python_files": len(files),
        "total_lines": sum(file["lines"] for file in analysed),
        "classes": sum(len(file["classes"]) for file in analysed),
        "functions": sum(len(file["functions"]) for file in analysed),
        "methods": sum(
            len(class_info["methods"])
            for file in analysed
            for class_info in file["classes"]
        ),
        "parse_errors": sum(1 for file in files if file.get("error")),
        "skipped_files": skipped,
        "undocumented_functions": function_count - documented_functions,
        "docstring_coverage": (
            round(documented_functions / function_count * 100, 1)
            if function_count
            else 100.0
        ),
        "longest_functions": sorted(
            all_functions,
            key=lambda function: (
                -function["length"],
                function["path"],
                function["line"],
                function["name"],
            ),
        )[:5],
        "most_complex": sorted(
            all_functions,
            key=lambda function: (
                -function["complexity"],
                -function["length"],
                function["path"],
                function["line"],
                function["name"],
            ),
        )[:5],
        "top_imports": [
            {"name": name, "files": count}
            for name, count in import_counts.most_common(10)
        ],
    }

    return {"summary": summary, "files": files}
