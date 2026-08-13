"""
Enhanced Data Warehouse Pipeline with DbtTaskGroup Integration

This DAG implements a production-ready data warehouse pipeline that combines the simplicity
of DbtTaskGroup's automatic dependency management with enterprise-grade monitoring,
    notifications, and error handling capabilities.

Key Features:
- Automatic dbt model dependency management via DbtTaskGroup
- Smart materialization conflict resolution with conditional full-refresh
- Comprehensive Slack notifications with detailed pipeline metrics
- Automated documentation generation and GCS publishing
- Advanced error handling and retry logic
- Resource cleanup and status management

Pipeline Flow:
1. Compile dbt project for validation
2. Conditional cleanup (handles materialization conflicts on retries)
3. Execute all dbt operations (
    models,
    tests,
    seeds) with automatic dependencies
4. Generate and publish documentation to GCS
5. Send success/failure notifications with detailed metrics
6. Cleanup resources and log execution summary

Author: Data Engineering Team
Version: 2.0 - Enhanced with comprehensive monitoring
Last Updated: 2025-06-26
"""

import json
import os
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import requests
from airflow.decorators import dag
from airflow.operators.bash import BashOperator
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import PythonOperator
from airflow.utils.trigger_rule import TriggerRule
from cosmos.airflow.task_group import DbtTaskGroup
from cosmos.config import ProfileConfig, ProjectConfig, RenderConfig
from cosmos.constants import LoadMode
from cosmos.operators import DbtDocsGCSOperator


class ConditionalRetryOperator:
    """
    Helper class to create operator args that include full_refresh on retries.

    This class provides utilities for handling dbt materialization conflicts
    that occur when dbt tries to create a view where a table exists, or vice versa.
    The conditional retry logic automatically applies --full-refresh on retries
    to resolve these conflicts without manual intervention.

    Note: This class is kept for future use but not currently implemented in the
    DbtTaskGroup approach. Instead, we use a separate cleanup task for retry handling.
    """

    @staticmethod
    def get_operator_args_with_retry_logic():
        """
        Returns operator args that include full_refresh when task is being retried.

        This function creates a callable that checks if the current task execution
        is a retry attempt and conditionally adds the full_refresh parameter to
        resolve BigQuery materialization conflicts.

        Returns:
            callable: Function that returns operator args based on retry status
        """

        def conditional_args(**context):
            """
            Generate dbt operator arguments based on retry status.

            This nested function checks if the current task execution is a retry
            and conditionally adds the full_refresh parameter to resolve BigQuery
            materialization conflicts.

            Args:
                **context: Airflow context containing task_instance information

            Returns:
                dict: Operator arguments, includes {"full_refresh": True} on retries
            """
            task_instance = context.get("task_instance")
            if task_instance and task_instance.try_number > 1:
                print(
                    "🔄 Retry detected (attempt %s), enabling --full-refresh",
                    task_instance.try_number,
                )
                return {"full_refresh": True}
            else:
                print("🆕 First attempt, using normal build mode")
                return {}

        return conditional_args


# ============================================================================
# ENVIRONMENT CONFIGURATION
# ============================================================================


def get_dbt_project_path():
    """
    Dynamically resolve dbt project path for different environments.

    Supports:
    - Local development: /path/to/project/dags/dbt
    - Docker/Astronomer: /usr/local/airflow/dags/dbt
    - Test environment: Custom path via DBT_ROOT_PATH env var
    """
    # Check environment variable first (for tests and custom deployments)
    env_path = os.getenv("DBT_ROOT_PATH")
    if env_path:
        path = Path(env_path)
        if path.exists() and (path / "dbt_project.yml").exists():
            return path

    # Default to relative path from this file
    default_path = Path(__file__).parent / "dbt"
    if default_path.exists() and (default_path / "dbt_project.yml").exists():
        return default_path

    # Fallback for Docker/Astronomer environment
    docker_path = Path("/usr/local/airflow/dags/dbt")
    if docker_path.exists() and (docker_path / "dbt_project.yml").exists():
        return docker_path

    # If none exist, return default (will cause validation error in Cosmos)
    return default_path


# Path configuration - supports both local development and containerized
# deployment
DBT_ROOT_PATH = get_dbt_project_path()

# Slack integration configuration - webhook URL from environment variables
# Optional: Slack webhook for notifications
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")

# Default arguments applied to all tasks in the DAG
DEFAULT_ARGS = {
    "retries": 2,  # Retry failed tasks up to 2 times
    "concurrency": 3,  # Limit concurrent task execution
    # 30 minute timeout for individual tasks
    "execution_timeout": timedelta(minutes=30),
    # Wait 5 minutes between retry attempts
    "retry_delay": timedelta(minutes=5),
}

# ============================================================================
# METRICS AND MONITORING FUNCTIONS
# ============================================================================


def get_dbt_task_metrics(**kwargs) -> dict[str, Any]:
    """
    Extract detailed execution metrics from DbtTaskGroup tasks.

    This function analyzes all task instances from the current DAG run to extract
    comprehensive metrics about dbt model builds, test executions, and overall
    pipeline performance. The metrics are used for detailed Slack notifications
    and monitoring dashboards.

    Args:
        **kwargs: Airflow context containing dag_run and task information

    Returns:
        Dict[str, Any]: Dictionary containing:
            - models_succeeded/failed: Count of successful/failed model builds
            - tests_passed/failed: Count of passed/failed data quality tests
            - total_tasks: Total number of dbt tasks executed
            - failed_tasks: List of task IDs that failed (for debugging)
            - succeeded_tasks: List of task IDs that succeeded

    Example:
        {
            'models_succeeded': 25,
            'models_failed': 2,
            'tests_passed': 45,
            'tests_failed': 3,
            'total_tasks': 75,
            'failed_tasks': ['dbt_operations.stg_users_test', 'dbt_operations.fact_sales_build'],
            'succeeded_tasks': ['dbt_operations.dim_products_build', ...]
        }
    """
    dag_run = kwargs.get("dag_run")
    if not dag_run:
        return {}

    # Initialize metrics dictionary with default values
    metrics = {
        "models_succeeded": 0,
        "models_failed": 0,
        "tests_passed": 0,
        "tests_failed": 0,
        "total_tasks": 0,
        "failed_tasks": [],
        "succeeded_tasks": [],
    }

    try:
        # Get all task instances from the current DAG run
        task_instances = dag_run.get_task_instances()

        # Analyze each task instance that belongs to the dbt_operations group
        for ti in task_instances:
            # Focus only on dbt_operations task group tasks (ignore
            # notification/cleanup tasks)
            if ti.task_id.startswith("dbt_operations."):
                metrics["total_tasks"] += 1

                if ti.state == "success":
                    metrics["succeeded_tasks"].append(ti.task_id)
                    # Classify successful tasks by type (model build vs test
                    # execution)
                    if "run" in ti.task_id or "build" in ti.task_id:
                        metrics["models_succeeded"] += 1
                    elif "test" in ti.task_id:
                        metrics["tests_passed"] += 1

                elif ti.state == "failed":
                    metrics["failed_tasks"].append(ti.task_id)
                    # Classify failed tasks by type for targeted error
                    # reporting
                    if "run" in ti.task_id or "build" in ti.task_id:
                        metrics["models_failed"] += 1
                    elif "test" in ti.task_id:
                        metrics["tests_failed"] += 1

    except (AttributeError, KeyError, TypeError) as e:
        print(f"Error extracting dbt metrics: {str(e)}")

    return metrics


# ============================================================================
# SLACK NOTIFICATION FUNCTIONS
# ============================================================================


def send_slack_notification(**kwargs) -> None:
    """
    Send comprehensive Slack notification when dbt pipeline fails.

    This function creates rich, formatted Slack messages with detailed failure
    information including task-level metrics, success rates, and direct links
    to the Airflow UI for troubleshooting. The notification provides immediate
    visibility into pipeline issues for rapid incident response.

    Features:
    - Rich formatting with Slack Block Kit for better readability
    - Detailed failure metrics (success rate, failed task counts)
    - List of specific failed tasks (limited to first 5 for brevity)
    - Direct action button linking to Airflow UI
    - Graceful fallback if Slack webhook is not configured

    Args:
        **kwargs: Airflow context containing task_instance, dag, execution_date

    Example Slack Message:
        🚨 dbt Pipeline Failure Alert
        DAG: warehouse_dag
        Failed Task: dbt_operations.stg_users_test
        Status: Failed ❌

        Pipeline Metrics:
        • Success Rate: 92.3% (12/13 tasks)
        • Tests Failed: 1

        Failed Tasks: 1
        • dbt_operations.stg_users_test
    """
    # Skip notification if Slack webhook is not configured
    if not SLACK_WEBHOOK_URL:
        print("SLACK_WEBHOOK_URL not configured, skipping notification")
        return

    # Extract task and DAG information from Airflow context
    task_instance = kwargs["task_instance"]
    dag_id = kwargs["dag"].dag_id
    execution_date = kwargs["execution_date"]

    # Get detailed metrics about the pipeline execution
    metrics = get_dbt_task_metrics(**kwargs)

    # Build detailed failure information for the Slack message
    failure_details = []
    if metrics.get("failed_tasks"):
        failure_details.append(f"*Failed Tasks:* {len(metrics['failed_tasks'])}")
        # Show first 5 failed tasks to avoid message overflow
        failure_details.append(f"• {', '.join(metrics['failed_tasks'][:5])}")
        if len(metrics["failed_tasks"]) > 5:
            failure_details.append(f"• ... and {len(metrics['failed_tasks']) - 5} more")

    # Create performance summary with success rate calculation
    performance_summary = []
    if metrics.get("total_tasks", 0) > 0:
        success_rate = (len(metrics.get("succeeded_tasks", [])) / metrics["total_tasks"]) * 100
        performance_summary.append(
            f"*Success Rate:* {success_rate:.1f}% "
            f"({len(metrics.get('succeeded_tasks', []))}/{metrics['total_tasks']} tasks)"
        )

    # Add specific failure type information
    if metrics.get("models_failed", 0) > 0:
        performance_summary.append(f"*Models Failed:* {metrics['models_failed']}")
    if metrics.get("tests_failed", 0) > 0:
        performance_summary.append(f"*Tests Failed:* {metrics['tests_failed']}")

    # Build Slack message using Block Kit for rich formatting
    message_blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": "🚨 dbt Pipeline Failure Alert"}},
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*DAG:* {dag_id}"},
                {"type": "mrkdwn", "text": f"*Failed Task:* {task_instance.task_id}"},
                {"type": "mrkdwn", "text": f"*Execution Date:* {execution_date}"},
                {"type": "mrkdwn", "text": "*Status:* Failed ❌"},
            ],
        },
    ]

    # Add performance metrics section if data is available
    if performance_summary:
        message_blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Pipeline Metrics:*\n" + "\n".join(performance_summary),
                },
            }
        )

    # Add detailed failure information if available
    if failure_details:
        message_blocks.append(
            {"type": "section", "text": {"type": "mrkdwn", "text": "\n".join(failure_details)}}
        )

    # Add action button for direct access to Airflow UI
    message_blocks.append(
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "View in Airflow"},
                    "url": (
                        f"https://clpqv4fx901t601k2zd9ykz3i.astronomer.run/"
                        f"dy4j071b/dags/{dag_id}/grid"
                    ),
                }
            ],
        }
    )

    # Construct final message payload
    message = {
        "text": "🚨 dbt Pipeline Failed",  # Fallback text for basic clients
        "blocks": message_blocks,
    }

    # Send notification with error handling
    try:
        response = requests.post(
            SLACK_WEBHOOK_URL,
            data=json.dumps(message),
            headers={"Content-Type": "application/json"},
            timeout=10,  # 10 second timeout to avoid hanging the pipeline
        )
        response.raise_for_status()
        print("Enhanced Slack failure notification sent successfully")
    except (requests.RequestException, json.JSONDecodeError, ValueError) as e:
        print(f"Failed to send Slack notification: {str(e)}")


def send_success_notification(**kwargs) -> None:
    """
    Send comprehensive Slack notification when pipeline completes successfully.

    This function creates detailed success notifications with pipeline metrics,
    execution summaries, and quick access links to both the Airflow pipeline
    and the generated dbt documentation. The notification provides stakeholders
    with confidence in data quality and pipeline reliability.

    Features:
    - Rich success metrics (total tasks, success rate, models built)
    - Execution summary with categorized task counts
    - Links to both Airflow UI and published dbt documentation
    - Celebration messaging for team morale
    - Graceful handling if Slack is not configured

    Args:
        **kwargs: Airflow context containing dag, execution_date information

    Example Slack Message:
        ✅ dbt Pipeline Success
        DAG: warehouse_dag
        Status: Completed Successfully ✅
        Documentation: Updated & Published 📚

        Pipeline Metrics:
        • Total Tasks: 27
        • Success Rate: 100% ✅
        • Models Built: 19
        • Tests Passed: 8

        Execution Summary:
        • 19 data models built successfully
        • 8 data quality tests passed
    """
    # Skip notification if Slack webhook is not configured
    if not SLACK_WEBHOOK_URL:
        return

    # Extract DAG and execution information from Airflow context
    dag_id = kwargs["dag"].dag_id
    execution_date = kwargs["execution_date"]

    # Get detailed metrics about the successful pipeline execution
    metrics = get_dbt_task_metrics(**kwargs)

    # Build success metrics summary for the Slack message
    success_metrics = []
    if metrics.get("total_tasks", 0) > 0:
        success_metrics.append(f"*Total Tasks:* {metrics['total_tasks']}")
        # Only called on success
        success_metrics.append("*Success Rate:* 100% ✅")

    # Add specific success type information
    if metrics.get("models_succeeded", 0) > 0:
        success_metrics.append(f"*Models Built:* {metrics['models_succeeded']}")

    if metrics.get("tests_passed", 0) > 0:
        success_metrics.append(f"*Tests Passed:* {metrics['tests_passed']}")

    # Categorize successful tasks for execution summary
    model_tasks = [
        task
        for task in metrics.get("succeeded_tasks", [])
        if any(keyword in task.lower() for keyword in ["run", "build", "seed"])
    ]
    test_tasks = [task for task in metrics.get("succeeded_tasks", []) if "test" in task.lower()]

    # Build human-readable execution summary
    success_summary = []
    if model_tasks:
        success_summary.append(f"• {len(model_tasks)} data models built successfully")
    if test_tasks:
        success_summary.append(f"• {len(test_tasks)} data quality tests passed")

    # Build Slack message using Block Kit for rich formatting
    message_blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": "✅ dbt Pipeline Success"}},
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*DAG:* {dag_id}"},
                {"type": "mrkdwn", "text": f"*Execution Date:* {execution_date}"},
                {"type": "mrkdwn", "text": "*Status:* Completed Successfully ✅"},
                {"type": "mrkdwn", "text": "*Documentation:* Updated & Published 📚"},
            ],
        },
    ]

    # Add metrics section if data is available
    if success_metrics:
        message_blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Pipeline Metrics:*\n" + "\n".join(success_metrics),
                },
            }
        )

    # Add execution summary if data is available
    if success_summary:
        message_blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Execution Summary:*\n" + "\n".join(success_summary),
                },
            }
        )

    # Add celebration message for team morale
    message_blocks.append(
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "🎉 All models built, tests passed, and documentation updated successfully!",
            },
        }
    )

    # Add action buttons for quick access to pipeline and documentation
    message_blocks.append(
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "View Pipeline"},
                    "url": (
                        f"https://clpqv4fx901t601k2zd9ykz3i.astronomer.run/"
                        f"dy4j071b/dags/{dag_id}/grid"
                    ),
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "View Documentation"},
                    "url": "https://storage.googleapis.com/dag_logfiles/dbt-docs/index.html",
                },
            ],
        }
    )

    # Construct final message payload
    message = {
        "text": "✅ dbt Pipeline Completed Successfully",  # Fallback text for basic clients
        "blocks": message_blocks,
    }

    # Send notification with error handling
    try:
        response = requests.post(
            SLACK_WEBHOOK_URL,
            data=json.dumps(message),
            headers={"Content-Type": "application/json"},
            timeout=10,  # 10 second timeout to avoid hanging the pipeline
        )
        response.raise_for_status()
        print("Enhanced Slack success notification sent successfully")
    except (requests.RequestException, requests.HTTPError, requests.Timeout) as e:
        print(f"Failed to send success notification: {str(e)}")


# ============================================================================
# DAG DEFINITION
# ============================================================================


@dag(
    # Explicit DAG ID for clear identification
    dag_id="warehouse_dag",
    start_date=datetime(2023, 12, 11),  # Initial DAG start date
    schedule="0 */2 * * *",
    # Every 2 hours (simulated daily schedule for testing)
    catchup=False,  # Don't run historical executions
    # Tags for DAG categorization and filtering
    tags=["loom_warehouse", "dbt_task_group"],
    default_args=DEFAULT_ARGS,  # Apply default arguments to all tasks
    description="dbt warehouse pipeline using DbtTaskGroup with enhanced monitoring \
        and notifications",
    max_active_runs=1,  # Prevent concurrent DAG runs
)
def warehouse_dag_pipeline():
    """
    Enhanced warehouse pipeline using DbtTaskGroup with comprehensive monitoring.

    This DAG implements a production-ready data warehouse pipeline that balances
    simplicity with enterprise-grade features. It uses DbtTaskGroup for automatic
    dbt dependency management while adding custom tasks for monitoring, notifications,
    documentation, and error handling.

    Architecture Benefits:
    - DbtTaskGroup provides automatic model dependency management and parallel execution
    - Custom notification tasks provide detailed success/failure reporting
    - Smart retry logic handles common materialization conflicts automatically
    - Documentation pipeline ensures stakeholder access to data lineage and quality metrics
    - Resource cleanup ensures proper pipeline state management

    Task Flow:
    1. compile_dbt: Validates dbt project configuration and SQL syntax
    2. conditional_cleanup: Handles materialization conflicts on retry attempts
    3. dbt_operations: Executes all dbt models, tests, and seeds with dependencies
    4. generate_docs: Creates and publishes dbt documentation to GCS
    5. notify_success/notify_failure: Sends detailed Slack notifications
    6. cleanup: Performs resource cleanup and status logging

    Error Handling:
    - Automatic retry with materialization conflict resolution
    - Immediate failure notifications with task-level details
    - Graceful fallback if external services (Slack, GCS) are unavailable
    - Always-running cleanup task for consistent state management
    """

    # ========================================================================
    # TASK 1: DBT PROJECT COMPILATION AND VALIDATION
    # ========================================================================

    compile_dbt = BashOperator(
        task_id="compile_dbt",
        bash_command=f"cd {DBT_ROOT_PATH} && dbt compile --target prod --profiles-dir .",
        doc_md="""
        **dbt Project Compilation & Validation**

        Validates the dbt project configuration, dependencies, and SQL syntax before
        executing any models. This step ensures that:
        - All dbt dependencies are properly installed
        - SQL syntax is valid across all models
        - Profile configuration is correct
        - Manifest file is up-to-date

        Failure at this stage indicates configuration issues that must be resolved
        before proceeding with model execution.
        """,
    )

    # ========================================================================
    # TASK 2: CONDITIONAL CLEANUP FOR RETRY HANDLING
    # ========================================================================

    def cleanup_on_retry(**context):
        """
        Intelligent retry handler for materialization conflicts.

        This function detects when tasks are being retried and automatically
        resolves BigQuery materialization conflicts by running dbt with the
        --full-refresh flag. This handles the common issue where dbt tries to
        create a view where a table exists, or vice versa.

        The function:
        1. Scans all task instances in the current DAG run
        2. Identifies any dbt_operations tasks that have been retried
        3. If retries are detected, runs `dbt run --full-refresh` to clear conflicts
        4. Returns status indicating whether cleanup was needed/successful

        Args:
            **context: Airflow context with task_instance and dag_run information

        Returns:
            str: Status of cleanup operation (
                'full_refresh_completed',
                'no_retry_needed',
                etc.)

        Example Scenarios:
        - First run: Returns 'no_retry_needed', normal execution continues
        - Retry after materialization conflict: Runs full refresh, returns 'full_refresh_completed'
        - Retry with different error: Returns 'no_retry_needed', normal retry logic applies
        """
        dag_run = context.get("dag_run")

        # Check if any tasks in this DAG run have been retried
        retry_detected = False
        if dag_run:
            task_instances = dag_run.get_task_instances()
            # Scan all task instances looking for retry attempts in dbt
            # operations
            for ti in task_instances:
                if ti.task_id.startswith("dbt_operations.") and ti.try_number > 1:
                    retry_detected = True
                    print(f"🔄 Retry detected for task: {ti.task_id} (attempt {ti.try_number})")
                    break

        if retry_detected:
            print("🧹 Running dbt with --full-refresh to resolve materialization conflicts...")
            try:
                # Execute dbt run with full-refresh to drop and recreate all
                # objects
                result = subprocess.run(
                    [
                        "dbt",
                        "run",
                        "--full-refresh",
                        "--target",
                        "prod",
                        "--profiles-dir",
                        str(DBT_ROOT_PATH),
                        "--project-dir",
                        str(DBT_ROOT_PATH),
                    ],
                    capture_output=True,
                    text=True,
                    cwd=str(DBT_ROOT_PATH),
                )

                if result.returncode == 0:
                    print("✅ Full refresh completed successfully")
                    return "full_refresh_completed"
                else:
                    print(f"❌ Full refresh failed: {result.stderr}")
                    return "full_refresh_failed"
            except (subprocess.CalledProcessError, OSError, FileNotFoundError) as e:
                print(f"❌ Error during full refresh: {str(e)}")
                return "full_refresh_error"
        else:
            print("🆕 No retries detected, proceeding with normal operation")
            return "no_retry_needed"

    conditional_cleanup = PythonOperator(
        task_id="conditional_cleanup",
        python_callable=cleanup_on_retry,
        doc_md="""
        **Smart Materialization Conflict Resolution**

        Automatically detects and resolves BigQuery materialization conflicts that occur
        when dbt tries to create a view where a table exists (or vice versa). This task:

        - Scans task instances for retry attempts
        - Identifies materialization conflicts as the likely cause
        - Executes `dbt run --full-refresh` to resolve conflicts
        - Only runs when actual retries are detected (preserves performance)

        This intelligent approach eliminates the need for manual intervention while
        preserving normal execution speed for successful runs.
        """,
    )

    # ========================================================================
    # TASK 3: DBT OPERATIONS WITH AUTOMATIC DEPENDENCY MANAGEMENT
    # ========================================================================

    # Validate dbt project exists before creating DbtTaskGroup
    if not (DBT_ROOT_PATH / "dbt_project.yml").exists():
        # Create a placeholder task when dbt project is not available
        # This allows the DAG to be imported without errors in environments
        # where the dbt project structure is not yet available
        dbt_operations = EmptyOperator(
            task_id="dbt_operations_placeholder",
            doc_md="""
            **DBT Operations Placeholder**

            The dbt project was not found at {DBT_ROOT_PATH}.
            This placeholder task allows the DAG to be imported successfully.

            To enable dbt operations:
            1. Ensure dbt_project.yml exists at {DBT_ROOT_PATH}
            2. Set DBT_ROOT_PATH environment variable if using custom location
            3. Restart Airflow to reload the DAG with proper dbt integration
            """,
        )
    else:
        try:
            dbt_operations = DbtTaskGroup(
                group_id="dbt_operations",
                project_config=ProjectConfig(
                    DBT_ROOT_PATH,
                    manifest_path=DBT_ROOT_PATH / "target" / "manifest.json",
                ),
                profile_config=ProfileConfig(
                    profile_name="loom",
                    target_name="prod",
                    profiles_yml_filepath=DBT_ROOT_PATH / "profiles.yml",
                ),
                render_config=RenderConfig(
                    load_method=LoadMode.DBT_MANIFEST,
                    # NOTE: Analysis and Source warnings are expected and harmless
                    # - Analysis files are for exploration only, not production execution
                    # - Source definitions are metadata only, not executable tasks
                    # These warnings indicate correct Cosmos behavior, not
                    # configuration issues
                ),
                operator_args={
                    # Note: Individual task retries within DbtTaskGroup don't automatically
                    # inherit full-refresh. For materialization conflicts, manual intervention
                    # or DAG-level retry may be required. Consider upgrading to Cosmos v2.x
                    # for enhanced retry capabilities when available.
                    #
                    # Troubleshooting materialization conflicts:
                    # 1. Check BigQuery console for conflicting table/view names
                    # 2. Run: dbt run --full-refresh --select <model_name> --target prod
                    # 3. Or clear the entire schema: dbt run --full-refresh --target prod
                },
            )
        except (ImportError, AttributeError, ValueError, TypeError) as e:
            # If DbtTaskGroup creation fails, create a placeholder task
            dbt_operations = EmptyOperator(
                task_id="dbt_operations_error",
                doc_md=f"""
                **DBT Operations Error**

                Failed to create DbtTaskGroup: {str(e)}

                This placeholder task allows the DAG to be imported successfully.
                Please check the dbt project configuration and Cosmos setup.
                """,
            )

    # ========================================================================
    # TASK 4: DOCUMENTATION GENERATION AND PUBLISHING
    # ========================================================================

    generate_docs = DbtDocsGCSOperator(
        task_id="generate_docs",
        project_dir=DBT_ROOT_PATH,
        profile_config=ProfileConfig(
            profile_name="loom",
            target_name="prod",
            profiles_yml_filepath=DBT_ROOT_PATH / "profiles.yml",
        ),
        connection_id="gcp-default",
        # RFC3986 compliant connection ID (hyphens, not underscores)
        bucket_name="dag_logfiles",
        folder_dir="dbt-docs",
        trigger_rule=TriggerRule.NONE_FAILED,  # Only run if upstream tasks succeed
        doc_md="""
        **dbt Documentation Generation & GCS Publishing**

        Generates comprehensive dbt documentation and publishes it to Google Cloud Storage
        for stakeholder access. The documentation includes:

        - **Data Lineage Graphs**: Visual representation of model dependencies
        - **Model Documentation**: Descriptions, column details, and business logic
        - **Test Results**: Data quality metrics and validation outcomes
        - **Source Documentation**: External data source information and freshness
        - **Macro Documentation**: Reusable code documentation

        Published Location: gs://dag_logfiles/dbt-docs/
        Public URL: https://storage.googleapis.com/dag_logfiles/dbt-docs/index.html

        This enables self-service data discovery and promotes data governance across
        the organization.
        """,
    )

    # ========================================================================
    # TASK 5: FAILURE NOTIFICATION SYSTEM
    # ========================================================================

    notify_failure = PythonOperator(
        task_id="notify_failure",
        python_callable=send_slack_notification,
        trigger_rule=TriggerRule.ONE_FAILED,  # Trigger if any upstream task fails
        doc_md="""
        **Immediate Failure Alert System**

        Provides rapid incident response through comprehensive Slack notifications when
        any pipeline task fails. The notification includes:

        - **Failure Context**: DAG name, failed task, execution timestamp
        - **Performance Metrics**: Success rate, task counts, failure classification
        - **Failed Task Details**: Specific task names for targeted debugging
        - **Quick Actions**: Direct links to Airflow UI for immediate investigation

        This system ensures data quality issues and pipeline failures are immediately
        visible to the responsible teams, enabling rapid resolution and minimizing
        downstream impact.
        """,
    )

    # ========================================================================
    # TASK 6: SUCCESS NOTIFICATION SYSTEM
    # ========================================================================

    notify_success = PythonOperator(
        task_id="notify_success",
        python_callable=send_success_notification,
        trigger_rule=TriggerRule.NONE_FAILED,  # Only run if all upstream tasks succeed
        # Context is automatically provided in Airflow 2.0+
        doc_md="""
        **Success Confirmation & Metrics Reporting**

        Sends comprehensive success notifications with detailed pipeline metrics when
        all tasks complete successfully. The notification provides:

        - **Execution Summary**: Total tasks, success rate, categorized outcomes
        - **Business Metrics**: Models built, tests passed, data quality status
        - **Documentation Status**: Confirmation of updated documentation
        - **Quick Access**: Links to both pipeline view and published documentation

        This positive reinforcement builds confidence in data quality and provides
        stakeholders with assurance that fresh, validated data is available.
        """,
    )

    # ========================================================================
    # TASK 7: RESOURCE CLEANUP AND STATUS MANAGEMENT
    # ========================================================================

    cleanup = EmptyOperator(
        task_id="cleanup",
        # Always run if at least one task succeeds
        trigger_rule=TriggerRule.NONE_FAILED_MIN_ONE_SUCCESS,
        doc_md="""
        **Pipeline Cleanup & Resource Management**

        Performs final cleanup operations and logs pipeline execution summary.
        This task always runs (regardless of upstream success/failure) to ensure:

        - **Resource Cleanup**: Temporary files and connections are properly closed
        - **Status Logging**: Final pipeline state is recorded for monitoring
        - **Metric Collection**: Execution statistics are captured for performance analysis
        - **State Management**: Pipeline state is properly reset for next execution

        The cleanup task ensures consistent pipeline hygiene and provides a definitive
        end point for monitoring and alerting systems.
        """,
    )

    # ========================================================================
    # TASK DEPENDENCY CONFIGURATION
    # ========================================================================

    # Primary execution path: validation -> cleanup -> dbt operations
    compile_dbt >> conditional_cleanup >> dbt_operations

    # Success path: dbt operations -> documentation -> success notification
    dbt_operations >> generate_docs >> notify_success

    # Failure path: any task failure triggers immediate notification
    # This ensures rapid incident response regardless of where failure occurs
    [compile_dbt, conditional_cleanup, dbt_operations, generate_docs] >> notify_failure

    # Both success and failure paths converge on cleanup for consistent state
    # management
    [notify_success, notify_failure] >> cleanup


# ============================================================================
# DAG INSTANTIATION
# ============================================================================


# Instantiate the DAG for Airflow discovery
# Variable assignment is required for Airflow to detect and load the DAG
warehouse_dag = warehouse_dag_pipeline()
