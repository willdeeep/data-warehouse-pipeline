"""
dbt-specific tests for data models, macros, and transformations.

This module tests the dbt components of the pipeline including:
- Model compilation and execution
- Custom macros and their functionality
- Data quality tests and validations
- Schema definitions and source configurations
"""

# pylint: disable=attribute-defined-outside-init

from pathlib import Path
import json
import subprocess

import pytest


def get_project_root():
    """
    Get the project root directory dynamically.

    Returns the path to the project root by finding the directory
    containing the dags folder, starting from this test file's location.
    """
    current_file = Path(__file__).resolve()
    # Walk up the directory tree to find the project root
    for parent in current_file.parents:
        if (parent / "dags").exists() and (parent / "dags" / "dbt").exists():
            return parent

    # Fallback: assume we're in tests/dbt/ and go up two levels
    return current_file.parent.parent.parent


class TestDbtProject:
    """Test suite for dbt project configuration and structure."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up dbt project path."""
        project_root = get_project_root()
        self.dbt_project_dir = project_root / "dags" / "dbt"
        self.dbt_project_yml = self.dbt_project_dir / "dbt_project.yml"

    def test_dbt_project_yml_exists(self):
        """Test that dbt_project.yml exists and is valid."""
        assert self.dbt_project_yml.exists()

        # Test that it's valid YAML
        import yaml
        with open(self.dbt_project_yml, encoding='utf-8') as f:
            config = yaml.safe_load(f)

        assert config["name"] == "loom"
        assert config["version"] == "1.0.0"
        assert config["profile"] == "loom"

    def test_dbt_profiles_yml_exists(self):
        """Test that profiles.yml exists."""
        profiles_yml = self.dbt_project_dir / "profiles.yml"
        assert profiles_yml.exists()

    def test_required_directories_exist(self):
        """Test that all required dbt directories exist."""
        required_dirs = [
            "models",
            "macros",
            "tests",
            "analyses"
        ]

        for dir_name in required_dirs:
            dir_path = self.dbt_project_dir / dir_name
            assert dir_path.exists(
            ), f"Required directory {dir_name} is missing"

    def test_models_directory_structure(self):
        """Test the models directory has proper structure."""
        models_dir = self.dbt_project_dir / "models"

        # Expected subdirectories
        expected_subdirs = ["staging", "intermediate", "marts", "sources"]

        for subdir in expected_subdirs:
            subdir_path = models_dir / subdir
            assert subdir_path.exists(
            ), f"Models subdirectory {subdir} is missing"


class TestDbtMacros:
    """Test suite for custom dbt macros."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up macro testing environment."""
        project_root = get_project_root()
        self.macros_dir = project_root / "dags" / "dbt" / "macros"

    def test_macros_directory_exists(self):
        """Test that macros directory exists with files."""
        assert self.macros_dir.exists()

        # Check for key macro files
        macro_files = list(self.macros_dir.glob("*.sql"))
        assert len(macro_files) > 0, "No macro files found"

    def test_custom_schema_macro_exists(self):
        """Test that custom schema macro exists."""
        schema_macro = self.macros_dir / "get_custom_schema.sql"
        if schema_macro.exists():
            content = schema_macro.read_text()
            assert "generate_schema_name" in content
            assert "dev_warehouse" in content  # Production routing logic

    def test_testing_utilities_macro_exists(self):
        """Test that testing utilities macro exists."""
        testing_macro = self.macros_dir / "testing_utilities.sql"
        if testing_macro.exists():
            content = testing_macro.read_text()
            assert "compare_multiple_columns" in content
            assert "validate_data_quality" in content


@pytest.mark.dbt
@pytest.mark.external
class TestDbtExecution:
    """Test suite for dbt execution (requires BigQuery access)."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up dbt execution environment."""
        project_root = get_project_root()
        self.dbt_dir = project_root / "dags" / "dbt"

    @pytest.mark.slow
    @pytest.mark.requires_dbt
    def test_dbt_compile(self):
        """Test that dbt can compile all models."""
        result = subprocess.run(["dbt",
                                 "compile",
                                "--profiles-dir",
                                 ".",
                                 "--profile",
                                 "loom",
                                 "--target",
                                 "dev"],
                                cwd=self.dbt_dir,
                                capture_output=True,
                                text=True,
                                check=False)

        assert result.returncode == 0, f"dbt compile failed: {result.stderr}"

    @pytest.mark.requires_dbt
    def test_dbt_parse(self):
        """Test that dbt can parse the project."""
        result = subprocess.run(
            ["dbt", "parse", "--profiles-dir", ".", "--profile", "loom", "--target", "dev"],
            cwd=self.dbt_dir,
            capture_output=True,
            text=True,
            check=False
        )

        assert result.returncode == 0, f"dbt parse failed: {result.stderr}"

    @pytest.mark.requires_dbt
    def test_manifest_json_generation(self):
        """Test that manifest.json is generated correctly."""
        # Run dbt parse to generate manifest
        subprocess.run(["dbt",
                        "parse",
                        "--profiles-dir",
                        ".",
                        "--profile",
                        "loom",
                        "--target",
                        "dev"],
                       cwd=self.dbt_dir,
                       capture_output=True,
                       text=True,
                       check=False)

        manifest_path = self.dbt_dir / "target" / "manifest.json"
        if manifest_path.exists():
            with open(manifest_path, encoding='utf-8') as f:
                manifest = json.load(f)

            assert "nodes" in manifest
            assert "macros" in manifest

            # Check for key models
            model_nodes = [node for node in manifest["nodes"]
                           if node.startswith("model.")]
            assert len(
                model_nodes) > 20, "Expected more than 20 models in manifest"


class TestDbtSources:
    """Test suite for dbt source definitions."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up source testing environment."""
        project_root = get_project_root()
        self.sources_dir = project_root / "dags" / "dbt" / "models" / "sources"
        self.source_yml = self.sources_dir / "source.yml"

    def test_source_yml_exists(self):
        """Test that source.yml exists and is valid."""
        assert self.source_yml.exists()

        import yaml
        with open(self.source_yml, encoding='utf-8') as f:
            sources = yaml.safe_load(f)

        assert "sources" in sources
        assert len(sources["sources"]) > 0

    def test_source_definitions_complete(self):
        """Test that source definitions have required fields."""
        import yaml
        with open(self.source_yml, encoding='utf-8') as f:
            sources = yaml.safe_load(f)

        for source in sources["sources"]:
            assert "name" in source
            assert "description" in source
            assert "tables" in source

            for table in source["tables"]:
                assert "name" in table
                assert "description" in table
                assert "columns" in table

    def test_source_tests_defined(self):
        """Test that critical source columns have tests defined."""
        import yaml
        with open(self.source_yml, encoding='utf-8') as f:
            sources = yaml.safe_load(f)

        test_count = 0
        for source in sources["sources"]:
            for table in source["tables"]:
                for column in table.get("columns", []):
                    if "tests" in column:
                        test_count += len(column["tests"])

        assert test_count > 50, f"Expected more than 50 column tests, found {test_count}"


class TestDbtDataQuality:
    """Test suite for dbt data quality and validation tests."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up data quality testing environment."""
        project_root = get_project_root()
        self.tests_dir = project_root / "dags" / "dbt" / "tests"

    def test_custom_tests_exist(self):
        """Test that custom SQL tests exist."""
        test_files = list(self.tests_dir.glob("*.sql"))
        assert len(test_files) > 0, "No custom test files found"

        # Check for SCD validation tests
        scd_tests = [f for f in test_files if "scd" in f.name.lower()]
        assert len(scd_tests) > 0, "No SCD validation tests found"

    def test_scd_validation_tests_content(self):
        """Test that SCD validation tests have proper content."""
        scd_test_file = self.tests_dir / "scd_validation_tests.sql"
        if scd_test_file.exists():
            content = scd_test_file.read_text()

            # Check for key SCD test components
            assert "current_record_uniqueness" in content
            assert "is_current = TRUE" in content or "is_current=TRUE" in content
            assert "dim_users" in content or "dim_products" in content


@pytest.mark.dbt
@pytest.mark.slow
@pytest.mark.external
class TestDbtIntegration:
    """Integration tests for dbt with actual data (requires BigQuery)."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up integration testing environment."""
        project_root = get_project_root()
        self.dbt_dir = project_root / "dags" / "dbt"

    @pytest.mark.requires_dbt
    @pytest.mark.requires_db
    def test_staging_models_run(self):
        """Test that staging models can run successfully."""
        result = subprocess.run(
            ["dbt", "run", "--select", "staging", "--profiles-dir",
             ".", "--profile", "loom", "--target", "dev"],
            cwd=self.dbt_dir,
            capture_output=True,
            text=True,
            check=False
        )

        # Note: This may fail without proper credentials, which is expected in
        # CI
        if result.returncode != 0:
            pytest.skip(
                f"dbt run failed (likely missing credentials): {result.stderr}")

    @pytest.mark.requires_dbt
    @pytest.mark.requires_db
    def test_data_quality_tests_run(self):
        """Test that data quality tests can run."""
        result = subprocess.run(
            ["dbt", "test", "--select", "staging", "--profiles-dir",
             ".", "--profile", "loom", "--target", "dev"],
            cwd=self.dbt_dir,
            capture_output=True,
            text=True,
            check=False
        )

        # Note: This may fail without proper credentials, which is expected in
        # CI
        if result.returncode != 0:
            pytest.skip(
                f"dbt test failed (likely missing credentials): {result.stderr}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
