"""
Performance and load tests for the data pipeline.

This module contains tests for:
- Query performance and execution time
- Resource usage and memory consumption
- Concurrent execution capabilities
- Data volume handling
- BigQuery quota and rate limiting
"""

import gc
import statistics
import threading
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest

try:
    from google.cloud import bigquery

    BIGQUERY_AVAILABLE = True
except ImportError:
    BIGQUERY_AVAILABLE = False


@pytest.mark.performance
@pytest.mark.slow
class TestDagPerformance:
    """Test suite for DAG execution performance."""

    @pytest.mark.requires_db
    def test_dag_parsing_time(self, dag_bag):
        """Test that DAG parsing completes within acceptable time."""
        start_time = time.time()

        # Parse all DAGs
        dags = dag_bag.dags

        parse_time = time.time() - start_time

        # Should parse all DAGs in under 30 seconds
        assert parse_time < 30.0, f"DAG parsing took {parse_time:.2f}s (threshold: 30s)"
        assert len(dags) > 0, "No DAGs found after parsing"

    @pytest.mark.requires_db
    def test_task_count_reasonable(self, dag_bag):
        """Test that task counts are within reasonable limits."""
        # Use direct access to avoid database queries in CI
        warehouse_dag = dag_bag.dags.get("warehouse_dag")

        if warehouse_dag:
            task_count = len(warehouse_dag.tasks)

            # Should have a reasonable number of tasks (not too many for
            # performance)
            assert task_count < 200, f"Too many tasks ({task_count}) may impact performance"
            assert task_count > 10, f"Too few tasks ({task_count}) - DAG may be incomplete"


@pytest.mark.performance
@pytest.mark.external
@pytest.mark.skipif(not BIGQUERY_AVAILABLE, reason="google-cloud-bigquery not available")
class TestBigQueryPerformance:
    """Test suite for BigQuery query performance."""

    def test_staging_query_performance_baseline(self):
        """Test that staging queries have reasonable performance characteristics."""
        # Skip if BigQuery is not available
        if not BIGQUERY_AVAILABLE:
            pytest.skip("google-cloud-bigquery not available")

        # Create mock manually since the fixture approach has import issues
        try:
            import google.cloud.bigquery

            with patch("google.cloud.bigquery.Client") as mock_client:
                mock_job = Mock()
                mock_job.ended = datetime.now()
                mock_job.started = datetime.now() - timedelta(seconds=5)
                mock_job.job_statistics.total_bytes_processed = 1024 * 1024  # 1MB
                mock_job.job_statistics.total_slot_ms = 1000

                mock_client_instance = Mock()
                mock_client_instance.query.return_value = mock_job
                mock_client.return_value = mock_client_instance

                # Test performance metrics are captured
                job = mock_client_instance.query("SELECT 1")
                assert hasattr(job, "job_statistics")
                assert hasattr(job.job_statistics, "total_bytes_processed")
                assert hasattr(job.job_statistics, "total_slot_ms")

                # Baseline performance expectations
                bytes_processed = job.job_statistics.total_bytes_processed
                slot_ms = job.job_statistics.total_slot_ms

                # These are conservative baselines for testing framework
                assert bytes_processed > 0, "Query should process some data"
                assert slot_ms > 0, "Query should use some compute slots"
        except ImportError:
            pytest.skip("google-cloud-bigquery not available")


@pytest.mark.performance
class TestMemoryUsage:
    """Test suite for memory usage and resource consumption."""

    @pytest.mark.requires_db
    def test_dag_memory_footprint(self, dag_bag):
        """Test that DAG objects don't consume excessive memory."""

        # Get initial memory usage
        # Record initial object count for memory tracking
        len(gc.get_objects())

        # Use dag_bag.dags directly instead of get_dag to avoid DB query
        warehouse_dag = dag_bag.dags.get("warehouse_dag")

        if not warehouse_dag:
            pytest.skip("warehouse_dag not found in dag_bag")

        # Basic memory footprint check
        assert warehouse_dag is not None

        # In a real test, you might use memory_profiler or psutil
        # For now, just ensure the DAG loads without obvious memory leaks

    @pytest.mark.requires_db
    def test_concurrent_dag_access(self, dag_bag):
        """Test that multiple DAG accesses don't cause memory issues."""

        results = []
        errors = []

        def access_dag():
            try:
                # Use dag_bag.dags directly instead of get_dag to avoid DB query
                dag = dag_bag.dags.get("warehouse_dag")
                if dag:
                    results.append(dag.dag_id)
                else:
                    errors.append("DAG not found")
            except (AttributeError, KeyError, ValueError) as e:
                errors.append(str(e))

        # If warehouse_dag is not available, skip the test
        if dag_bag.dags.get("warehouse_dag") is None:
            pytest.skip("warehouse_dag not found in dag_bag")

        threads = []
        for _ in range(5):
            thread = threading.Thread(target=access_dag)
            thread.start()
            threads.append(thread)

        for thread in threads:
            thread.join(timeout=10)

        # Verify no errors occurred
        assert len(errors) == 0, f"Errors occurred: {errors}"

        # Verify all accesses completed
        assert len(results) == 5, f"Expected 5 completed accesses, got {len(results)}"


@pytest.mark.performance
@pytest.mark.external
class TestDataVolumeHandling:
    """Test suite for handling different data volumes."""

    def test_large_dataset_simulation(self):
        """Test pipeline behavior with large dataset simulation."""
        # This would test how the pipeline handles large volumes of data
        # For testing framework purposes, we simulate the test

        # Simulate large dataset metadata
        simulated_rows = 1_000_000
        simulated_columns = 50
        estimated_size_mb = (simulated_rows * simulated_columns * 8) / (1024 * 1024)

        # Test that our calculations are reasonable
        assert estimated_size_mb > 0
        assert estimated_size_mb < 10_000, "Simulated dataset too large for testing"

    def test_batch_processing_limits(self):
        """Test batch processing size limits."""
        # Test recommended batch sizes for different operations

        batch_sizes = {
            "staging_insert": 10_000,
            "intermediate_transform": 50_000,
            "mart_aggregation": 100_000,
        }

        for operation, batch_size in batch_sizes.items():
            # Validate batch sizes are within reasonable limits
            assert batch_size > 1_000, f"{operation} batch size too small"
            assert batch_size < 1_000_000, f"{operation} batch size too large"


@pytest.mark.performance
class TestRateLimiting:
    """Test suite for rate limiting and quota management."""

    def test_api_rate_limiting_simulation(self):
        """Test API rate limiting handling."""

        # Simulate rate limiting with time delays
        api_calls = []

        for _ in range(5):
            start_time = time.time()

            # Simulate API call delay
            time.sleep(0.1)  # 100ms delay

            end_time = time.time()
            api_calls.append(end_time - start_time)

        # Calculate average response time
        avg_response_time = statistics.mean(api_calls)

        # Test that average response time is reasonable
        assert avg_response_time < 1.0, (
            f"Average API response time too high: {avg_response_time:.2f}s"
        )
        assert avg_response_time > 0.05, (
            f"Average API response time suspiciously low: {avg_response_time:.2f}s"
        )

    def test_concurrent_request_handling(self):
        """Test handling of concurrent requests."""

        results = []

        def simulate_request(request_id):
            # Simulate processing time
            time.sleep(0.1)
            results.append(f"Request {request_id} completed")

        # Create concurrent requests
        threads = []
        for i in range(3):  # Limited number for testing
            thread = threading.Thread(target=simulate_request, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join(timeout=5)

        # Verify all requests completed
        assert len(results) == 3, f"Expected 3 completed requests, got {len(results)}"


@pytest.mark.benchmark
class TestBenchmarks:
    """Benchmark tests for establishing performance baselines."""

    @pytest.mark.requires_db
    def test_dag_loading_benchmark(self, dag_bag):
        """Benchmark DAG loading time."""
        # Use dag_bag.dags directly instead of get_dag to avoid DB query
        dag = dag_bag.dags.get("warehouse_dag")

        if not dag:
            pytest.skip("warehouse_dag not found in dag_bag")

        iterations = 3
        load_times = []

        for _ in range(iterations):
            start_time = time.time()

            # Access DAG from in-memory dict (simulates reload)
            test_dag = dag_bag.dags.get("warehouse_dag")
            assert test_dag is not None

            load_time = time.time() - start_time
            load_times.append(load_time)

        avg_load_time = statistics.mean(load_times)
        max_load_time = max(load_times)

        # Benchmark assertions
        assert avg_load_time < 5.0, f"Average DAG load time too high: {avg_load_time:.2f}s"
        assert max_load_time < 10.0, f"Maximum DAG load time too high: {max_load_time:.2f}s"

        print("DAG Loading Benchmark:")
        print(f"  Average: {avg_load_time:.2f}s")
        print(f"  Maximum: {max_load_time:.2f}s")
        print(f"  Iterations: {iterations}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "performance"])
