"""
Example DAGs test. This test ensures that all Dags have tags, retries set to two,
    and no import errors. This is an example pytest and may not be fit the context
of your DAGs. Feel free to add and remove tests.
"""

import logging
import os
from contextlib import contextmanager

import pytest
from airflow.models import DagBag


@contextmanager
def suppress_logging(namespace):
    """
    Context manager to temporarily suppress logging for a specific namespace.

    This is useful during testing to reduce noise from expected warnings
    and debug messages that would otherwise clutter test output.

    Args:
        namespace (str): The logging namespace to suppress (e.g., "airflow")

    Yields:
        None: Context where logging is suppressed

    Example:
        with suppress_logging("airflow"):
            # Airflow logs will be suppressed here
            dag_bag=DagBag()
    """
    logger = logging.getLogger(namespace)
    old_value = logger.disabled
    logger.disabled = True
    try:
        yield
    finally:
        logger.disabled = old_value


def get_import_errors():
    """
    Extract DAG import errors for parametrized testing.

    This function loads all DAGs and returns any import errors that occurred
    during the loading process. The errors are formatted for use in pytest
    parametrized tests, allowing each import error to be tested individually.

    Returns:
        list[tuple]: List of (file_path, error_message) tuples. Always includes
                    (None, None) as the first item to ensure at least one test
                    case exists even when there are no import errors.

    Note:
        This function suppresses Airflow logging to reduce test output noise
        while still capturing critical import errors.
    """
    # Get the project root directory and point to the dags folder
    import pathlib

    project_root = pathlib.Path(__file__).parent.parent.parent
    dags_folder = str(project_root / "dags")

    with suppress_logging("airflow"):
        dag_bag = DagBag(dag_folder=dags_folder, include_examples=False)

        def strip_path_prefix(path):
            return os.path.relpath(path, str(project_root))

        # prepend (None, None) to ensure that a test object is always
        # created even if it's a no op.
        return [(None, None)] + [
            (strip_path_prefix(k), v.strip()) for k, v in dag_bag.import_errors.items()
        ]


def get_dags():
    """
    Extract all DAGs for parametrized testing.

    This function loads all DAGs from the DagBag and returns them in a format
    suitable for pytest parametrized tests. Each DAG can then be tested
    individually for various properties like tags, retries, configuration, etc.

    Returns:
        list[tuple]: List of (dag_id, dag_object, file_location) tuples for
                    each successfully loaded DAG.

    Note:
        This function suppresses Airflow logging to reduce test output noise
        while still loading all DAG objects for testing.
    """
    # Get the project root directory and point to the dags folder
    import pathlib

    project_root = pathlib.Path(__file__).parent.parent.parent
    dags_folder = str(project_root / "dags")

    with suppress_logging("airflow"):
        dag_bag = DagBag(dag_folder=dags_folder, include_examples=False)

    def strip_path_prefix(path):
        return os.path.relpath(path, str(project_root))

    return [(k, v, strip_path_prefix(v.fileloc)) for k, v in dag_bag.dags.items()]


# ============================================================================
# PARAMETRIZED IMPORT ERROR TESTS
# ============================================================================
# These tests verify that all DAG files can be imported without errors.
# Each import error is tested individually to provide specific failure
# information.


@pytest.mark.parametrize(
    "rel_path,rv", get_import_errors(), ids=[x[0] for x in get_import_errors()]
)
def test_file_imports(rel_path, rv):
    """Test for import errors on a file"""
    if rel_path and rv:
        raise Exception(f"{rel_path} failed to import with message \n {rv}")


APPROVED_TAGS = {
    "loom_warehouse",
    "dbt_task_group",
    "export",
    "bigquery",
    "gcs",
    "enhanced",
    "slack",
    "dev",
    "test",
    "production",
    "etl",
    "warehouse",
    "example",
    "dbt",
    "metrics",
    "analytics",
    "daily",
    "weekly",
    "ebay",
    "slack_notifications",
    "manual",
    "full_refresh",
    "update",
}

# ============================================================================
# PARAMETRIZED DAG PROPERTY TESTS
# ============================================================================
# These tests verify that all DAGs follow organizational standards including
# proper tagging, retry configuration, and other required properties.


@pytest.mark.parametrize("dag_id,dag,fileloc", get_dags(), ids=[x[2] for x in get_dags()])
def test_dag_tags(dag_id, dag, fileloc):
    """
    test if a DAG is tagged and if those TAGs are in the approved list
    """
    assert dag.tags, f"{dag_id} in {fileloc} has no tags"
    if APPROVED_TAGS:
        assert not set(dag.tags) - APPROVED_TAGS


@pytest.mark.parametrize("dag_id,dag, fileloc", get_dags(), ids=[x[2] for x in get_dags()])
def test_dag_retries(dag_id, dag, fileloc):
    """
    test if a DAG has retries set
    """
    retries = dag.default_args.get("retries", None)
    assert retries is not None and retries >= 1, (
        f"{dag_id} in {fileloc} must have task retries >= 1. Currently: {retries}"
    )
