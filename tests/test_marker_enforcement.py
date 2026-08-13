"""
Test enforcement: All tests that use dag_bag.get_dag or Airflow DB access must be marked with @pytest.mark.requires_db.
"""

import ast
import os

import pytest

TESTS_ROOT = os.path.dirname(__file__)

REQUIRES_DB_MARK = "requires_db"

# Helper: Find all test files


def find_test_files():
    for root, _, files in os.walk(TESTS_ROOT):
        for f in files:
            if f.startswith("test_") and f.endswith(".py"):
                yield os.path.join(root, f)


# Helper: Parse AST and check for dag_bag.get_dag usage


def test_all_db_access_tests_are_marked():
    failures = []
    for file_path in find_test_files():
        with open(file_path) as f:
            source = f.read()
        tree = ast.parse(source, filename=file_path)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                # Check for dag_bag.get_dag usage
                uses_db = any(
                    isinstance(n, ast.Call)
                    and isinstance(n.func, ast.Attribute)
                    and n.func.attr == "get_dag"
                    for n in ast.walk(node)
                )
                # Check for @pytest.mark.requires_db
                has_marker = any(
                    (
                        isinstance(d, ast.Call)
                        and isinstance(d.func, ast.Attribute)
                        and isinstance(d.func.value, ast.Attribute)
                        and d.func.attr == REQUIRES_DB_MARK
                        and d.func.value.attr == "mark"
                    )
                    or (
                        isinstance(d, ast.Attribute)
                        and isinstance(d.value, ast.Attribute)
                        and d.attr == REQUIRES_DB_MARK
                        and d.value.attr == "mark"
                    )
                    for d in node.decorator_list
                )
                if uses_db and not has_marker:
                    failures.append(
                        f"{file_path}:{node.lineno} {node.name} is missing @pytest.mark.requires_db"
                    )
    if failures:
        pytest.fail("\n".join(failures))
