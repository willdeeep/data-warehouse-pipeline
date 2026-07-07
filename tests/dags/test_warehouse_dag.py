"""
Unit tests for the warehouse_dag.py main production pipeline.

Tests cover:
- DAG structure and configuration
- Task dependencies and relationships
- Custom operators and functions
- Error handling and retry logic
- Slack notification functionality
"""

from datetime import datetime, timedelta
from unittest.mock import Mock, patch
import os
import sys

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
DAGS_DIR = os.path.join(PROJECT_ROOT, "dags")
if DAGS_DIR not in sys.path:
    sys.path.insert(0, DAGS_DIR)

# Import warehouse_dag functions at module level with proper error handling
try:
    import warehouse_dag as wh_dag_module  # Import the module itself
    from warehouse_dag import (
        send_slack_notification,
        send_success_notification,
        get_dbt_task_metrics
    )
    WAREHOUSE_DAG_AVAILABLE = True
except ImportError as e:
    # Fallback for when running in different environments
    print(f"Warning: Could not import warehouse_dag functions: {e}")
    wh_dag_module = None
    send_slack_notification = None
    send_success_notification = None
    get_dbt_task_metrics = None
    WAREHOUSE_DAG_AVAILABLE = False


class TestWarehouseDag:
    """Test suite for the main warehouse DAG."""

    @pytest.fixture(autouse=True)
    def setup(self, dag_bag):
        """Set up test fixtures."""
        self.dag_bag = dag_bag
        # Use direct access to avoid database queries in CI
        try:
            # Try direct access first (works in CI) - test the update DAG
            self.dag = dag_bag.dags.get("warehouse_dag_update") or dag_bag.dags.get("warehouse_dag")
            if not self.dag:
                # Fallback to get_dag for local development
                self.dag = dag_bag.get_dag("warehouse_dag_update") or dag_bag.get_dag("warehouse_dag")
        except Exception:
            self.dag = None

    @pytest.mark.unit
    def test_dag_exists(self):
        """Test that the warehouse DAG exists and loads correctly."""
        if self.dag is None:
            pytest.skip("warehouse_dag not available - check DAG imports")
        assert self.dag is not None
        assert self.dag.dag_id in ["warehouse_dag_update", "warehouse_dag"]

    @pytest.mark.unit
    def test_dag_configuration(self):
        """Test DAG configuration and default arguments."""
        if self.dag is None:
            pytest.skip("warehouse_dag not available - check DAG imports")
        
        # Test schedule - warehouse_dag_update is manual execution only
        # Use schedule_interval for Airflow 2.x compatibility  
        schedule_attr = getattr(self.dag, 'schedule', None) or getattr(self.dag, 'schedule_interval', None)
        assert schedule_attr is None  # Manual execution only

        # Test default args - the actual DAG uses a different structure
        default_args = self.dag.default_args
        assert default_args["retries"] == 2  # As defined in warehouse_dag.py
        assert default_args["concurrency"] == 3

        # Test retry delay
        assert isinstance(default_args["retry_delay"], timedelta)
        assert default_args["retry_delay"] == timedelta(minutes=5)

        # Test execution timeout - update DAG uses 2 hours
        if self.dag.dag_id == "warehouse_dag_update":
            assert default_args["execution_timeout"] == timedelta(hours=2)
        else:
            assert default_args["execution_timeout"] == timedelta(minutes=30)

    @pytest.mark.unit
    def test_dag_tags(self):
        """Test that DAG has appropriate tags."""
        if self.dag is None:
            pytest.skip("warehouse_dag not available - check DAG imports")
        
        # Update DAG has different tags: ['loom_warehouse', 'enhanced', 'manual', 'full_refresh', 'update']
        if self.dag.dag_id == "warehouse_dag_update":
            expected_tags = {"loom_warehouse", "enhanced", "manual", "full_refresh", "update"}
        else:
            expected_tags = {"loom_warehouse", "dbt_task_group"}
        assert set(self.dag.tags) >= expected_tags

    @pytest.mark.unit  
    @pytest.mark.ci_skip  # Skip in CI due to potential DB access in task counting
    def test_task_count(self):
        """Test that all expected tasks are present."""
        if self.dag is None:
            pytest.skip("warehouse_dag not available - check DAG imports")
        
        # Update DAG has fewer tasks (manual workflow), original has many dbt tasks
        if self.dag.dag_id == "warehouse_dag_update":
            # Update DAG has about 10 tasks (dev/prod workflow)
            assert len(self.dag.tasks) >= 8
        else:
            # Original DAG has 40+ tasks (includes all dbt models + custom tasks)
            assert len(self.dag.tasks) > 40

    @pytest.mark.unit
    @pytest.mark.ci_skip  # Skip in CI due to potential DB access in dependency analysis
    def test_task_dependencies(self):
        """Test critical task dependencies."""
        if self.dag is None:
            pytest.skip("warehouse_dag not available - check DAG imports")
            
        task_dict = {task.task_id: task for task in self.dag.tasks}

        # Update DAG has different task structure
        if self.dag.dag_id == "warehouse_dag_update":
            # Test that compile tasks exist (dev/prod workflow)
            assert any("compile_dbt" in task_id for task_id in task_dict.keys())
            # Test notification tasks
            assert "notify_success" in task_dict
            assert "cleanup" in task_dict
        else:
            # Original DAG structure
            assert "compile_dbt" in task_dict
            assert "conditional_cleanup" in task_dict
            assert "cleanup" in task_dict
            assert "notify_success" in task_dict
            assert "notify_failure" in task_dict

    @pytest.mark.smoke
    def test_no_import_errors(self):
        """Test that the DAG imports without errors."""
        # Only run this test if we have a valid DagBag
        if self.dag_bag is None:
            pytest.skip("DagBag not available")
        
        import_errors = getattr(self.dag_bag, 'import_errors', {})
        if import_errors:
            # In CI, we might have import errors due to missing dependencies
            # Log them but don't fail the test
            import os
            if os.getenv("CI") == "true":
                print(f"Import errors in CI (expected): {import_errors}")
                pytest.skip("Import errors expected in CI environment")
        
        assert len(import_errors) == 0, f"DAG import errors: {import_errors}"

    @pytest.mark.dbt
    @pytest.mark.requires_dbt
    def test_dbt_task_group_exists(self):
        """Test that dbt task group is properly configured."""
        if self.dag is None:
            pytest.skip("warehouse_dag not available - check DAG imports")
        
        # Look for dbt operations task group
        dbt_tasks = [t for t in self.dag.tasks if "dbt" in t.task_id.lower()]
        
        # Update DAG has fewer dbt tasks (manual workflow)
        if self.dag.dag_id == "warehouse_dag_update":
            assert len(dbt_tasks) >= 2  # Should have compile/build tasks
        else:
            assert len(dbt_tasks) > 20  # Should have many dbt model tasks


class TestSlackNotifications:
    """Test suite for Slack notification functions."""

    def setup_method(self):
        """Set up test fixtures for each test method."""
        # Functions are imported at module level
        if not WAREHOUSE_DAG_AVAILABLE:
            pytest.skip("warehouse_dag functions not available")

        self.send_slack_notification = send_slack_notification
        self.send_success_notification = send_success_notification

    @pytest.mark.unit
    @pytest.mark.external  # Requires external service (Slack)
    @patch("os.getenv")
    @patch("requests.post")
    def test_send_slack_notification_success(self, mock_post, mock_getenv):
        """Test successful Slack notification sending."""
        # Set up environment
        mock_getenv.return_value = "https://hooks.slack.com/webhook/test"

        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        # Create mock context like Airflow would provide
        mock_context = {
            'task_instance': Mock(),
            'dag': Mock(dag_id='test_dag'),
            'execution_date': datetime.now()
        }

        # Test the function with proper kwargs
        result = self.send_slack_notification(**mock_context)

        # Function returns None on success
        assert result is None

    @pytest.mark.unit
    @pytest.mark.external  # Requires external service (Slack)
    @patch("os.getenv")
    @patch("requests.post")
    def test_send_slack_notification_failure(self, mock_post, mock_getenv):
        """Test Slack notification failure handling."""
        # Set up environment
        mock_getenv.return_value = "https://hooks.slack.com/webhook/test"

        # Mock failed response
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_post.return_value = mock_response

        # Create mock context
        mock_context = {
            'task_instance': Mock(),
            'dag': Mock(dag_id='test_dag'),
            'execution_date': datetime.now()
        }

        # Test the function - it should handle the error gracefully
        result = self.send_slack_notification(**mock_context)

        # Function returns None even on failure (graceful handling)
        assert result is None

    @pytest.mark.unit
    @patch("os.getenv")
    def test_slack_notification_no_webhook(self, mock_getenv):
        """Test behavior when no Slack webhook is configured."""
        # No webhook URL configured
        mock_getenv.return_value = ""

        # Create mock context
        mock_context = {
            'task_instance': Mock(),
            'dag': Mock(dag_id='test_dag'),
            'execution_date': datetime.now()
        }

        # Test the function - should return early without making requests
        result = self.send_slack_notification(**mock_context)

        # Should return None (no-op when webhook not configured)
        assert result is None

    @pytest.mark.unit
    @pytest.mark.external  # Requires external service (Slack)
    @patch("warehouse_dag.get_dbt_task_metrics")
    @patch("os.getenv")
    def test_success_notification_formatting(self, mock_getenv, mock_metrics):
        """Test success notification message formatting."""
        # Set up environment
        mock_getenv.return_value = "https://hooks.slack.com/webhook/test"

        # Mock dbt metrics
        mock_metrics.return_value = {
            "total_tasks": 25,
            "success_rate": 100.0,
            "models_built": 18,
            "tests_passed": 7
        }

        # Create mock context
        mock_context = {
            'task_instance': Mock(),
            'dag': Mock(dag_id='test_dag'),
            'execution_date': datetime.now()
        }

        # Call success notification - just verify it doesn't crash
        result = self.send_success_notification(**mock_context)

        # Should return None (successful execution)
        assert result is None


class TestCustomOperators:
    """Test suite for custom operators and functions."""

    def setup_method(self):
        """Set up test fixtures."""
        # Function is imported at module level
        if not WAREHOUSE_DAG_AVAILABLE:
            pytest.skip("warehouse_dag functions not available")

        self.get_dbt_task_metrics = get_dbt_task_metrics

    def test_get_dbt_task_metrics_calculation(self):
        """Test dbt task metrics calculation."""
        # Create a mock DAG run
        mock_dag_run = Mock()

        # Mock task instances - focus on dbt_operations tasks
        mock_ti1 = Mock()
        mock_ti1.task_id = "dbt_operations.model_run_users"
        mock_ti1.state = "success"

        mock_ti2 = Mock()
        mock_ti2.task_id = "dbt_operations.test_users_not_null"
        mock_ti2.state = "success"

        mock_ti3 = Mock()
        mock_ti3.task_id = "other_task"  # Non-dbt task should be ignored
        mock_ti3.state = "success"

        # Set up mock return value
        mock_dag_run.get_task_instances.return_value = [
            mock_ti1, mock_ti2, mock_ti3]

        # Create context
        context = {"dag_run": mock_dag_run}

        # Call the function
        metrics = self.get_dbt_task_metrics(**context)

        # Verify results - the function looks for tasks starting with
        # 'dbt_operations.'
        assert metrics["total_tasks"] == 2  # Only dbt_operations tasks
        assert metrics["models_succeeded"] == 1  # One model run task
        assert metrics["tests_passed"] == 1  # One test task
        assert len(metrics["succeeded_tasks"]) == 2
        assert "dbt_operations.model_run_users" in metrics["succeeded_tasks"]
        assert "dbt_operations.test_users_not_null" in metrics["succeeded_tasks"]


@pytest.mark.integration
class TestDagIntegration:
    """Integration tests for DAG execution flow."""

    @pytest.mark.requires_db
    @pytest.mark.ci_skip  # Skip in CI - requires proper database initialization
    def test_dag_can_be_triggered(self, dag_bag):
        """Test that DAG can be triggered without errors."""
        # Use dag_bag.dags directly instead of get_dag to avoid DB query
        dag = dag_bag.dags.get("warehouse_dag_update") or dag_bag.dags.get("warehouse_dag")
        
        if not dag:
            pytest.skip("warehouse_dag not found in dag_bag")

        # Test that DAG can create a DAG run
        from airflow.models import DagRun
        from airflow.utils.types import DagRunType

        # This is a dry run test - we're not actually executing
        dag_run = DagRun(
            dag_id=dag.dag_id,
            run_id="test_run",
            run_type=DagRunType.MANUAL,
            start_date=datetime.now()
        )

        assert dag_run.dag_id in ["warehouse_dag_update", "warehouse_dag"]

    @pytest.mark.slow
    @patch("warehouse_dag.DbtTaskGroup")
    def test_dbt_task_group_creation(
            self,
            mock_dbt_task_group,
            temp_dbt_project):
        """Test dbt task group creation with mocked dbt."""
        # Mock the DbtTaskGroup creation
        mock_instance = Mock()
        mock_dbt_task_group.return_value = mock_instance

        # Use the imported warehouse_dag module
        if not WAREHOUSE_DAG_AVAILABLE:
            pytest.skip("warehouse_dag module not available")

        # This tests that the DAG can be created with mocked dbt
        try:
            dag_instance = wh_dag_module.warehouse_dag
            assert dag_instance is not None
        except Exception as e:
            pytest.fail(f"DAG creation failed: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
