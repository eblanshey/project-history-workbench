#!/usr/bin/env python3

"""Docstring checker for this repository.

Given file(s) and/or directory path(s), scans for Python files and verifies:

1. Each module has a non-empty module docstring.
2. Each public function, class, and method has a non-empty docstring.

Intended to run outside FreeCAD.
"""

from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass
from pathlib import Path
import sys


@dataclass(frozen=True)
class MissingDocstring:
    """Represents a missing-docstring finding for reporting."""

    file: Path
    lineno: int
    kind: str
    name: str


def _is_public_name(name: str) -> bool:
    """Return whether the given identifier should be considered public."""
    return not name.startswith("_")


def _is_adapter_class(name: str) -> bool:
    """Return whether the given class name is an adapter implementation."""
    return name.endswith("Adapter")


def _is_protocol_class(cls: ast.ClassDef) -> bool:
    """Return whether the given class inherits from Protocol."""
    for base in cls.bases:
        if isinstance(base, ast.Name) and base.id == "Protocol":
            return True
        if isinstance(base, ast.Attribute) and base.attr == "Protocol":
            return True
    return False


def _has_nonempty_docstring(node: ast.AST) -> bool:
    """Return whether an AST node has a non-empty docstring."""
    doc = ast.get_docstring(node, clean=False)
    return bool(doc and doc.strip())


def _iter_python_files(paths: list[Path]) -> list[Path]:
    """Expand file/dir arguments into a de-duplicated list of Python files."""
    files: list[Path] = []

    for p in paths:
        if p.is_file():
            if p.suffix == ".py":
                files.append(p)
            continue

        if p.is_dir():
            files.extend(sorted(p.rglob("*.py")))
            continue

    # Deduplicate while preserving order.
    seen: set[Path] = set()
    unique: list[Path] = []
    for f in files:
        resolved = f.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        unique.append(f)
    return unique


def _check_class(
    *, file: Path, cls: ast.ClassDef, prefix: str
) -> list[MissingDocstring]:
    """Check a class (and its public methods/nested classes) for docstrings."""
    missing: list[MissingDocstring] = []

    qualname = f"{prefix}{cls.name}"

    # Skip adapter classes - they implement protocols that have docstrings
    if _is_adapter_class(cls.name):
        return missing

    # Skip Protocol classes - their methods are interface definitions
    if _is_protocol_class(cls):
        return missing

    if _is_public_name(cls.name) and not _has_nonempty_docstring(cls):
        missing.append(
            MissingDocstring(
                file=file,
                lineno=getattr(cls, "lineno", 1),
                kind="class",
                name=qualname,
            )
        )

    for stmt in cls.body:
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if _is_public_name(stmt.name) and not _has_nonempty_docstring(stmt):
                missing.append(
                    MissingDocstring(
                        file=file,
                        lineno=getattr(stmt, "lineno", 1),
                        kind="method",
                        name=f"{qualname}.{stmt.name}",
                    )
                )
        elif isinstance(stmt, ast.ClassDef):
            missing.extend(_check_class(file=file, cls=stmt, prefix=f"{qualname}."))

    return missing


def check_file(path: Path) -> list[MissingDocstring]:
    """Parse and check a single Python file for required docstrings."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return [
            MissingDocstring(file=path, lineno=1, kind="file", name="unreadable")
        ]

    try:
        tree = ast.parse(text, filename=str(path))
    except SyntaxError as exc:
        return [
            MissingDocstring(
                file=path,
                lineno=int(getattr(exc, "lineno", 1) or 1),
                kind="file",
                name="syntax-error",
            )
        ]

    missing: list[MissingDocstring] = []

    if not _has_nonempty_docstring(tree):
        missing.append(MissingDocstring(file=path, lineno=1, kind="module", name=""))

    for stmt in tree.body:
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if _is_public_name(stmt.name) and not _has_nonempty_docstring(stmt):
                missing.append(
                    MissingDocstring(
                        file=path,
                        lineno=getattr(stmt, "lineno", 1),
                        kind="function",
                        name=stmt.name,
                    )
                )
        elif isinstance(stmt, ast.ClassDef):
            missing.extend(_check_class(file=path, cls=stmt, prefix=""))

    return missing


def _format_missing(items: list[MissingDocstring]) -> str:
    """Format findings into a stable, human-readable report."""
    lines: list[str] = []
    for item in sorted(items, key=lambda x: (str(x.file), x.lineno, x.kind, x.name)):
        if item.kind == "module":
            lines.append(f"{item.file}: missing module docstring")
        else:
            lines.append(f"{item.file}:{item.lineno}: missing {item.kind} docstring: {item.name}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description=(
            "Check that Python modules have module docstrings and that public "
            "functions/classes/methods have non-empty docstrings."
        )
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Print each Python filename as it is checked",
    )
    parser.add_argument(
        "paths",
        nargs="+",
        help="File(s) and/or directory path(s) to scan recursively for *.py files",
    )
    args = parser.parse_args(argv)

    input_paths = [Path(p) for p in args.paths]
    py_files = _iter_python_files(input_paths)

    missing: list[MissingDocstring] = []
    for f in py_files:
        if args.verbose:
            sys.stdout.write(f"{f}\n")
        missing.extend(check_file(f))

    if missing:
        sys.stderr.write(_format_missing(missing) + "\n")
        sys.stderr.write(f"Found {len(missing)} missing docstrings in {len(py_files)} file(s)\n")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
