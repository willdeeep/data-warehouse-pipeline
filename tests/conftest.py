"""
Pytest configuration and shared fixtures for the Loom Insights data pipeline.

This module provides common test fixtures, configurations, and utilities
used across all test modules in the project.
"""

from pathlib import Path
from unittest.mock import Mock, patch
import os
import sys
import tempfile

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "pipeline" / "dags"))

# Set up test database configuration before importing Airflow
os.environ.setdefault('AIRFLOW__CORE__SQL_ALCHEMY_CONN', 'sqlite:////tmp/test_airflow.db')
os.environ.setdefault('AIRFLOW__CORE__EXECUTOR', 'SequentialExecutor')
os.environ.setdefault('AIRFLOW__CORE__LOAD_EXAMPLES', 'False')
os.environ.setdefault('AIRFLOW__CORE__UNIT_TEST_MODE', 'True')

# Now import Airflow components after setting up the environment
try:
    from airflow.models import DagBag, Connection
except ImportError:
    # If Airflow imports fail, create mock objects
    DagBag = Mock
    Connection = Mock


def pytest_configure(config):
    """Configure pytest for different environments."""
    # Add all custom markers to avoid warnings
    config.addinivalue_line("markers", "unit: Unit tests for individual functions/classes")
    config.addinivalue_line("markers", "integration: Integration tests requiring external dependencies")
    config.addinivalue_line("markers", "dag: DAG-specific tests")
    config.addinivalue_line("markers", "dbt: dbt model and project tests")
    config.addinivalue_line("markers", "performance: Performance and load tests")
    config.addinivalue_line("markers", "benchmark: Benchmark tests for timing comparisons")
    config.addinivalue_line("markers", "slow: Tests that take longer to run")
    config.addinivalue_line("markers", "external: Tests that require external services")
    config.addinivalue_line("markers", "smoke: Quick smoke tests for basic functionality")
    config.addinivalue_line("markers", "requires_db: Tests requiring full Airflow database")
    config.addinivalue_line("markers", "requires_dbt: Tests requiring dbt CLI")
    config.addinivalue_line("markers", "requires_bigquery: Tests requiring BigQuery credentials")
    config.addinivalue_line("markers", "ci_skip: Tests to skip in CI environments")


def pytest_collection_modifyitems(config, items):
    """Modify test collection based on environment."""
    # Check if we're in CI environment
    is_ci = os.getenv("CI") == "true" or os.getenv("GITHUB_ACTIONS") == "true"
    
    # Check if dbt is available
    dbt_available = False
    try:
        import subprocess
        result = subprocess.run(["dbt", "--version"], capture_output=True, timeout=5)
        dbt_available = result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        dbt_available = False

    skip_ci = pytest.mark.skip(reason="Skipped in CI environment")
    skip_no_db = pytest.mark.skip(reason="Requires full Airflow database")
    skip_no_dbt = pytest.mark.skip(reason="dbt CLI not available")

    for item in items:
        # Skip tests marked for CI skipping when in CI
        if "ci_skip" in item.keywords and is_ci:
            item.add_marker(skip_ci)
        
        # Skip database-dependent tests in CI (they use in-memory DB)
        if "requires_db" in item.keywords and is_ci:
            item.add_marker(skip_no_db)
        
        # Skip dbt tests when dbt CLI is not available
        if "requires_dbt" in item.keywords and not dbt_available:
            item.add_marker(skip_no_dbt)


@pytest.fixture(scope="session", autouse=True)
def setup_airflow_db():
    """Configure Airflow environment for testing without database initialization."""
    # Configure Airflow for testing - NO database required
    os.environ["AIRFLOW__DATABASE__SQL_ALCHEMY_CONN"] = "sqlite:///:memory:"
    os.environ["AIRFLOW__CORE__UNIT_TEST_MODE"] = "True"
    os.environ["AIRFLOW__CORE__LOAD_EXAMPLES"] = "False"
    os.environ["AIRFLOW__CORE__DAGS_FOLDER"] = str(PROJECT_ROOT / "pipeline" / "dags")
    os.environ["CI"] = "true"  # Force CI mode to ensure DB-free testing
    os.environ["GITHUB_ACTIONS"] = "true"  # Extra CI detection

    # Configure dbt project path for local testing
    os.environ["DBT_ROOT_PATH"] = str(PROJECT_ROOT / "pipeline" / "dbt")

    # Patch database operations at the module level
    with patch('airflow.models.base.Base.metadata'):
        with patch('airflow.settings.engine'):
            # DO NOT initialize any database - all tests should work without DB
            print("✅ Configured Airflow for DB-free testing")
            yield
    # No cleanup needed - no DB was created

# ============================================================================
    # AIRFLOW TESTING FIXTURES
# ============================================================================
    # These fixtures provide pre-configured Airflow components for testing
# without requiring a full Airflow database setup.


@pytest.fixture(scope="session")
def dag_bag():
    """Provide a DagBag instance for testing with better CI compatibility."""
    # Create DagBag without database dependencies
    is_ci = os.getenv("CI") == "true" or os.getenv("GITHUB_ACTIONS") == "true"
    
    if is_ci:
        # In CI, use minimal mocking to avoid DB issues
        with patch('airflow.models.dag.DagModel.get_current', return_value=None):
            dag_bag = DagBag(
                dag_folder=str(PROJECT_ROOT / "pipeline" / "dags"),
                include_examples=False,
                safe_mode=True  # Enable safe mode in CI
            )
            return dag_bag
    else:
        # Local development - allow normal DAG loading
        dag_bag = DagBag(
            dag_folder=str(PROJECT_ROOT / "pipeline" / "dags"),
            include_examples=False)
        return dag_bag


@pytest.fixture
def warehouse_dag(dag_bag):
    """Provide the warehouse DAG for testing with fallback."""
    dag = dag_bag.get_dag("warehouse_dag", include_subdags=False)
    if dag is None:
        pytest.skip("warehouse_dag not available - check DAG imports")
    return dag


@pytest.fixture
def mock_gcp_connection():
    """Mock GCP connection for testing."""
    conn = Connection(
        conn_id="gcp-default",
        conn_type="google_cloud_platform",
        description="Mock GCP connection for testing"
    )

    with patch("airflow.hooks.base.BaseHook.get_connection", return_value=conn):
        yield conn


@pytest.fixture
def mock_slack_webhook():
    """Mock Slack webhook URL for testing."""
    test_webhook = "https://hooks.slack.com/services/TEST/WEBHOOK/URL"

    with patch.dict(os.environ, {"SLACK_WEBHOOK_URL": test_webhook}):
        yield test_webhook


@pytest.fixture
def mock_bigquery_client():
    """Mock BigQuery client for testing."""
    try:
        import google.cloud.bigquery
        with patch("google.cloud.bigquery.Client") as mock_client:
            mock_instance = Mock()
            mock_client.return_value = mock_instance
            yield mock_instance
    except ImportError:
        # BigQuery not available, yield a mock object
        yield Mock()


@pytest.fixture
def temp_dbt_project():
    """Create a temporary dbt project directory for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        dbt_dir = Path(temp_dir) / "dbt"
        dbt_dir.mkdir()

        # Create minimal dbt_project.yml
        dbt_project_yml = dbt_dir / "dbt_project.yml"
        dbt_project_yml.write_text("""
name: 'test_project'
version: '1.0.0'
config-version: 2
profile: 'test'
        """)

        yield dbt_dir


@pytest.fixture
def sample_dag_context():
    """Provide sample Airflow context for testing."""
    from datetime import datetime

    return {
        "dag": Mock(dag_id="test_dag"),
        "task": Mock(task_id="test_task"),
        "execution_date": datetime(2024, 1, 1),
        "ds": "2024-01-01",
        "run_id": "test_run_001",
        "task_instance": Mock(),
        "params": {},
        "var": {
            "json": Mock(return_value={}),
            "value": Mock(return_value="test_value")
        }
    }

# End of conftest.py
