#!/usr/bin/env python3
"""
DAG validation script for CI/CD pipeline.
This script validates DAG syntax, imports, and structure.
"""
import sys
import os
from pathlib import Path

# Add the dags directory to Python path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "dags"))

def validate_dags():
    """Validate all DAGs in the dags directory."""
    print("🔍 Validating DAGs...")
    
    try:
        # Set up minimal Airflow environment
        import os
        import tempfile
        temp_db = os.path.join(tempfile.gettempdir(), 'dag_validation.db')
        os.environ.setdefault('AIRFLOW__DATABASE__SQL_ALCHEMY_CONN', f'sqlite:///{temp_db}')
        os.environ.setdefault('AIRFLOW__CORE__UNIT_TEST_MODE', 'True')
        os.environ.setdefault('AIRFLOW__CORE__LOAD_EXAMPLES', 'False')
        
        from airflow.models import DagBag
        
        # Initialize DagBag with minimal settings
        dags_folder = str(PROJECT_ROOT / "dags")
        print(f"Loading DAGs from: {dags_folder}")
        
        # Use safe mode and don't try to sync to database
        dag_bag = DagBag(
            dag_folder=dags_folder, 
            include_examples=False,
            safe_mode=True  # Enable safe mode to minimize DB operations
        )
        
        # Check for import errors
        if dag_bag.import_errors:
            print("❌ DAG import errors found:")
            for filename, error in dag_bag.import_errors.items():
                print(f"  📄 {filename}")
                print(f"     💥 {error}")
            return False
        
        # Check if any DAGs were loaded
        if not dag_bag.dags:
            print("⚠️  No DAGs found in the dags directory")
            return False
        
        # Display loaded DAGs with minimal validation
        print(f"✅ Successfully validated {len(dag_bag.dags)} DAGs:")
        validated_count = 0
        
        for dag_id in sorted(dag_bag.dag_ids):
            try:
                dag = dag_bag.dags.get(dag_id)  # Direct dict access instead of get_dag()
                if dag:
                    task_count = len(dag.tasks) if hasattr(dag, 'tasks') else 0
                    print(f"  📊 {dag_id} ({task_count} tasks)")
                    validated_count += 1
                    
                    # Basic DAG structure validation
                    if hasattr(dag, 'tasks') and not dag.tasks:
                        print(f"     ⚠️  DAG {dag_id} has no tasks")
                    
                    # Very basic schedule check
                    if hasattr(dag, 'schedule_interval') and dag.schedule_interval is None:
                        print(f"     ℹ️  DAG {dag_id} has no schedule (manual only)")
                        
            except Exception as e:
                print(f"     ⚠️  Warning: Could not fully validate DAG {dag_id}: {e}")
                continue
        
        if validated_count > 0:
            print(f"\n🎉 Successfully validated {validated_count} DAGs!")
            return True
        else:
            print("\n❌ No DAGs could be validated")
            return False
        
    except ImportError as e:
        print(f"❌ Failed to import Airflow: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error during DAG validation: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main validation function."""
    print("🚀 DAG Validation Starting\n")
    print("=" * 50)
    
    success = validate_dags()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ DAG VALIDATION PASSED")
        return 0
    else:
        print("❌ DAG VALIDATION FAILED")
        return 1

if __name__ == "__main__":
    sys.exit(main())
