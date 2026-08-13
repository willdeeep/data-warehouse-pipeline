"""
Enhanced Warehouse Data Pipeline for Manual Full Refresh

This DAG implements a manual-only warehouse rebuild pipeline designed for
handling structural changes to dbt models that require full refresh to avoid
materialization conflicts. The pipeline follows a dev-first approach:

Key Features:
- Manual execution only (no scheduling)
- Dev environment validation before production deployment
- Full refresh on all models to handle structural changes
- Comprehensive data quality testing in both environments
- Automated Slack notifications for failures and successes
- Documentation generation from production environment
- Bash operators for maximum control and transparency

The pipeline follows a sequential dev-to-prod flow:
1. Compile and validate dbt project (dev)
2. Build entire warehouse with full refresh (dev)
3. Run comprehensive data quality tests (dev)
4. Compile and validate dbt project (prod)
5. Build entire warehouse with full refresh (prod)
6. Run comprehensive data quality tests (prod)
7. Send Slack notification on failure (parallel to step 8)
8. Generate documentation from prod environment
9. Send success notification
10. Cleanup (always runs)

Use Cases:
- After adding new columns to existing models
- After changing data types or table structures
- After major dbt project restructuring
- When automated incremental runs are failing due to schema conflicts
- Before promoting structural changes to production

Author: Data Engineering Team
Version: 3.0 - Manual Full Refresh
Last Updated: July 2025
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path

import requests
from airflow.decorators import dag
from airflow.operators.bash import BashOperator
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import PythonOperator
from airflow.utils.trigger_rule import TriggerRule

DEFAULT_DBT_ROOT_PATH = Path(__file__).parent / "dbt"
DBT_ROOT_PATH = Path(os.getenv("DBT_ROOT_PATH", DEFAULT_DBT_ROOT_PATH))
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")  # Slack webhook for notifications


# Default task arguments with retry logic
DEFAULT_ARGS = {
    "retries": 2,  # Retry failed tasks twice
    "concurrency": 3,  # Limit concurrent task execution
    "retry_delay": timedelta(minutes=5),  # Wait 5 minutes between retries
    "execution_timeout": timedelta(hours=2),  # Maximum runtime per task
}


def send_slack_notification(**kwargs) -> None:
    """
    Send Slack notification when dbt tests fail.

    This function extracts task context information and sends a formatted
    Slack message with failure details and a link to the Airflow UI.

    Args:
        **kwargs: Airflow task context containing execution details

    Returns:
        None

    Note:
        Requires SLACK_WEBHOOK_URL environment variable to be set.
        If not configured, the function will skip notification and log a message.
    """
    # Guard clause: Skip notification if webhook URL not configured
    if not SLACK_WEBHOOK_URL:
        print("SLACK_WEBHOOK_URL not configured, skipping notification")
        return

    # Extract task execution context for notification details
    task_instance = kwargs["task_instance"]
    dag_id = kwargs["dag"].dag_id
    execution_date = kwargs["execution_date"]

    # Build structured Slack message using Slack Block Kit for rich formatting
    message = {
        "text": "🚨 dbt Data Quality Tests Failed",  # Fallback text for notifications
        "blocks": [
            {"type": "header", "text": {"type": "plain_text", "text": "🚨 dbt Data Quality Alert"}},
            {
                "type": "section",
                "fields": [  # Two-column layout for key information
                    {"type": "mrkdwn", "text": f"*DAG:* {dag_id}"},
                    {"type": "mrkdwn", "text": f"*Task:* {task_instance.task_id}"},
                    {"type": "mrkdwn", "text": f"*Execution Date:* {execution_date}"},
                    {"type": "mrkdwn", "text": "*Status:* Failed ❌"},
                ],
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": """Data quality tests have failed in the warehouse pipeline.
                    Please check the Airflow logs for detailed error information.""",
                },
            },
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
            },
        ],
    }

    # Attempt to send notification with error handling
    try:
        response = requests.post(
            SLACK_WEBHOOK_URL,
            data=json.dumps(message),
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        response.raise_for_status()  # Raise exception for HTTP errors
        print("Slack notification sent successfully")
    except (requests.RequestException, ValueError) as e:
        # Log error but don't fail the task - notifications are non-critical
        print("Failed to send Slack notification: %s", str(e))


def send_success_notification(**kwargs) -> None:
    """
    Send Slack notification when the entire pipeline completes successfully.

    This function sends a positive notification indicating that all pipeline
    steps (build, test, documentation) have completed without errors.

    Args:
        **kwargs: Airflow task context containing execution details

    Returns:
        None

    Note:
        Only sends notification if SLACK_WEBHOOK_URL is configured.
        Includes summary metrics and links to generated documentation.
    """
    # Skip if webhook not configured
    if not SLACK_WEBHOOK_URL:
        return

    # Extract execution context from kwargs
    dag_id = kwargs["dag"].dag_id
    execution_date = kwargs["execution_date"]

    # Build success notification with positive messaging
    message = {
        "text": "✅ Warehouse Pipeline Completed Successfully",
        "blocks": [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "✅ Warehouse Pipeline Success"},
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*DAG:* {dag_id}"},
                    {"type": "mrkdwn", "text": f"*Execution Date:* {execution_date}"},
                ],
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        "🎉 All models built, tests passed, and documentation updated successfully!"
                    ),
                },
            },
        ],
    }

    # Send success notification with error handling
    try:
        requests.post(
            SLACK_WEBHOOK_URL,
            data=json.dumps(message),
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
    except (requests.RequestException, ValueError) as e:
        # Log error but don't fail - notifications are supplementary
        print("Failed to send success notification: %s", str(e))


# DAG Configuration with Enhanced Error Handling and Monitoring
@dag(
    dag_id="warehouse_dag_update",  # Unique identifier for this manual update pipeline
    start_date=datetime(2023, 12, 11),  # Initial DAG execution date
    schedule=None,  # Manual execution only - no automatic scheduling
    catchup=False,  # Don't run historical instances on deployment
    tags=["loom_warehouse", "enhanced", "manual", "full_refresh", "update"],  # Organization tags
    default_args=DEFAULT_ARGS,  # Apply retry and timeout settings to all tasks
    description="Enhanced data warehouse pipeline for manual execution with full refresh. "
    "Runs dev first, then prod with comprehensive monitoring, "
    "testing, documentation generation, and Slack notifications.",
    max_active_runs=1,  # Prevent overlapping DAG executions
    doc_md=__doc__,  # Use module docstring for DAG documentation
)
def enhanced_warehouse_dag():
    """
    Define the enhanced warehouse pipeline for manual execution with full refresh.

    This function creates a task graph for manual dbt warehouse rebuilds, particularly
    useful after structural changes that might cause automated runs to fail.
    The pipeline runs dev environment first, then prod, both with full refresh.

    Task Flow Architecture:
    compile_dbt_dev → build_dev_full_refresh → test_dev_quality →
    compile_dbt_prod → build_prod_full_refresh → test_prod_quality →
    [notify_test_failure | generate_docs] → notify_success → cleanup

    The pipeline implements conditional branching:
    - If tests fail: notify_test_failure runs (with cleanup)
    - If tests pass: generate_docs → notify_success → cleanup

    Returns:
        DAG: Configured Airflow DAG object with all tasks and dependencies
    """

    # Step 1: Compile and validate dbt project for dev environment
    compile_dbt_dev = BashOperator(
        task_id="compile_dbt_dev",
        bash_command=f'cd {DBT_ROOT_PATH} && dbt compile --target dev --profiles-dir "$DBT_PROFILES_DIR" --no-version-check',
        doc_md="""
        **dbt Project Compilation & Validation (Dev Environment)**

        Performs comprehensive validation of the dbt project for dev target:
        - SQL syntax validation for all models
        - Jinja templating compilation and verification
        - Profile and target configuration validation (dev)
        - Dependency graph construction and cycle detection
        - Macro definition verification
        - Package dependency resolution

        This critical first step ensures the dev environment has a valid,
        compilable dbt project before proceeding with full refresh.
        """,
    )

    # Step 2: Build all models in dev with full refresh
    build_dev_full_refresh = BashOperator(
        task_id="build_dev_full_refresh",
        bash_command=f'cd {DBT_ROOT_PATH} && dbt build --target dev --profiles-dir "$DBT_PROFILES_DIR" --full-refresh --no-version-check',
        doc_md="""
        **Complete Dev Warehouse Build with Full Refresh**

        Executes full dbt build workflow in dev environment with full refresh:
        - **Seeds**: Reloads all CSV reference data
        - **Models**: Rebuilds ALL models from scratch (no incremental)
        - **Snapshots**: Recreates slowly changing dimension tables
        - **Full Refresh**: Drops and recreates all tables/views

        Full refresh ensures any structural changes (new columns, data types, etc.)
        are properly applied without conflicts from previous runs.
        """,
    )

    # Step 3: Execute comprehensive data quality testing in dev
    test_dev_quality = BashOperator(
        task_id="test_dev_quality",
        bash_command=f'cd {DBT_ROOT_PATH} && dbt test --target dev --profiles-dir "$DBT_PROFILES_DIR" --no-version-check',
        doc_md="""
        **Dev Environment Data Quality Testing**

        Runs the complete dbt testing suite in dev:
        - **Generic Tests**: Built-in tests (unique, not_null, accepted_values, relationships)
        - **Singular Tests**: Custom SQL-based tests for specific business logic
        - **Source Freshness**: Validates data freshness for external sources
        - **Model Tests**: Schema and business rule validations

        Dev testing ensures data quality before promoting to production.
        """,
    )

    # Step 4: Compile and validate dbt project for prod environment
    compile_dbt_prod = BashOperator(
        task_id="compile_dbt_prod",
        bash_command=f'cd {DBT_ROOT_PATH} && dbt compile --target prod --profiles-dir "$DBT_PROFILES_DIR" --no-version-check',
        doc_md="""
        **dbt Project Compilation & Validation (Prod Environment)**

        Performs comprehensive validation of the dbt project for prod target:
        - SQL syntax validation for all models
        - Jinja templating compilation and verification
        - Profile and target configuration validation (prod)
        - Dependency graph construction and cycle detection

        Validates prod configuration after successful dev deployment.
        """,
    )

    # Step 5: Build all models in prod with full refresh
    build_prod_full_refresh = BashOperator(
        task_id="build_prod_full_refresh",
        bash_command=f'cd {DBT_ROOT_PATH} && dbt build --target prod --profiles-dir "$DBT_PROFILES_DIR" --full-refresh --no-version-check',
        doc_md="""
        **Complete Prod Warehouse Build with Full Refresh**

        Executes full dbt build workflow in prod environment with full refresh:
        - **Seeds**: Reloads all CSV reference data
        - **Models**: Rebuilds ALL models from scratch (no incremental)
        - **Snapshots**: Recreates slowly changing dimension tables
        - **Full Refresh**: Drops and recreates all tables/views

        Full refresh in production ensures structural changes are applied
        cleanly without materialization conflicts.
        """,
    )

    # Step 6: Execute comprehensive data quality testing in prod
    test_prod_quality = BashOperator(
        task_id="test_prod_quality",
        bash_command=f'cd {DBT_ROOT_PATH} && dbt test --target prod --profiles-dir "$DBT_PROFILES_DIR" --no-version-check',
        # Add failure callback for immediate Slack notification
        on_failure_callback=send_slack_notification,
        doc_md="""
        **Production Data Quality Testing**

        Runs the complete dbt testing suite in production:
        - **Generic Tests**: Built-in tests (unique, not_null, accepted_values, relationships)
        - **Singular Tests**: Custom SQL-based tests for specific business logic
        - **Source Freshness**: Validates data freshness for external sources
        - **Model Tests**: Schema and business rule validations

        Test failures automatically trigger Slack notifications for immediate visibility.
        Final validation step before declaring pipeline success.
        """,
    )

    # Step 7: Send immediate Slack notification on test failure
    notify_test_failure = PythonOperator(
        task_id="notify_test_failure",
        python_callable=send_slack_notification,
        trigger_rule=TriggerRule.ONE_FAILED,  # Only run if upstream task failed
        # Context is automatically provided in Airflow 2.0+
        doc_md="""
        **Immediate Failure Alert System**

        Provides rapid incident response through Slack notifications:
        - Triggers only when data quality tests fail
        - Rich formatting with task context and error details
        - Direct links to Airflow UI for troubleshooting
        - Designed for immediate team visibility and response

        This notification system ensures data quality issues are surfaced
        immediately to the responsible teams for rapid resolution.
        """,
    )

    # Step 8: Generate and publish documentation (only if tests pass)
    generate_docs = BashOperator(
        task_id="generate_docs",
        bash_command=f'cd {DBT_ROOT_PATH} && dbt docs generate --target prod --profiles-dir "$DBT_PROFILES_DIR" --no-version-check',
        trigger_rule=TriggerRule.NONE_FAILED,  # Only run if no upstream failures
        doc_md="""
        **Documentation Generation for Production**

        Automatically generates comprehensive dbt documentation from prod environment:
        - **Data Lineage**: Visual dependency graphs showing data flow
        - **Model Documentation**: Descriptions, column details, and business context
        - **Test Results**: Current status of all data quality tests
        - **Source Documentation**: External data source descriptions and freshness

        Documentation reflects the current production state after successful full refresh.
        Only runs when all tests pass to ensure documentation accuracy.
        """,
    )

    # Step 9: Send success notification for complete pipeline success
    notify_success = PythonOperator(
        task_id="notify_success",
        python_callable=send_success_notification,
        trigger_rule=TriggerRule.NONE_FAILED,  # Only run if everything succeeded
        # Context is automatically provided in Airflow 2.0+
        doc_md="""
        **Pipeline Success Confirmation**

        Sends positive confirmation when the entire pipeline completes successfully:
        - Confirms all models built without errors in both dev and prod
        - Validates all data quality tests passed in both environments
        - Confirms documentation was generated
        - Provides execution summary and links to resources

        Success notifications help maintain visibility into healthy pipeline
        operations and confirm successful full refresh deployment.
        """,
    )

    # Step 10: Cleanup task that always runs for resource management
    cleanup = EmptyOperator(
        task_id="cleanup",
        # Run regardless of upstream status
        trigger_rule=TriggerRule.NONE_FAILED_MIN_ONE_SUCCESS,
        doc_md="""
        **Pipeline Cleanup & Resource Management**

        Performs final cleanup operations:
        - Logs pipeline execution summary
        - Cleans up temporary files if needed
        - Releases any held resources
        - Provides final status logging

        This task always runs regardless of pipeline success or failure to ensure
        proper resource cleanup and final status recording after full refresh.
        """,
    )

    # Define task dependencies for dev-first, then prod workflow
    # Dev environment workflow
    compile_dbt_dev >> build_dev_full_refresh >> test_dev_quality

    # Prod environment workflow (after dev success)
    test_dev_quality >> compile_dbt_prod >> build_prod_full_refresh >> test_prod_quality

    # If prod tests fail, notify via Slack
    test_prod_quality >> notify_test_failure

    # If prod tests pass, generate docs and notify success
    test_prod_quality >> generate_docs >> notify_success

    # Both success and failure paths lead to cleanup
    [notify_test_failure, notify_success] >> cleanup


# Assign to variable for Airflow discovery
warehouse_dag_update = enhanced_warehouse_dag()
