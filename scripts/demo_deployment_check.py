#!/usr/bin/env python3
"""
Demonstration script showing how deployment checks work.
This simulates the pre-deployment validation logic.
"""
import subprocess
import sys
import os


def run_syntax_check():
    """Check for syntax errors that would block deployment."""
    print("🔍 Checking for syntax errors (blocking)...")
    
    try:
        # Find all Python files
        python_files = []
        for root, dirs, files in os.walk("dags"):
            for file in files:
                if file.endswith(".py"):
                    python_files.append(os.path.join(root, file))
        
        for root, dirs, files in os.walk("tests"):
            for file in files:
                if file.endswith(".py"):
                    python_files.append(os.path.join(root, file))
        
        # Compile each file
        for py_file in python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    compile(f.read(), py_file, 'exec')
            except SyntaxError as e:
                print(f"❌ SYNTAX ERROR in {py_file}: {e}")
                return False
        
        print("✅ No syntax errors found!")
        return True
    
    except Exception as e:
        print(f"❌ Error during syntax check: {e}")
        return False


def run_style_check():
    """Check for style issues that will be documented but not block."""
    print("\n🎨 Checking code style (non-blocking)...")
    
    try:
        # Run flake8 for style issues
        result = subprocess.run(
            ["flake8", "dags/", "tests/", "--max-line-length=100", 
             "--ignore=E203,W503", "--count"],
            capture_output=True,
            text=True
        )
        
        issue_count = int(result.stdout.strip()) if result.stdout.strip().isdigit() else 0
        
        if issue_count > 0:
            print(f"⚠️ Found {issue_count} style issues (documented, not blocking)")
            return True, issue_count
        else:
            print("✅ No style issues found!")
            return True, 0
    
    except Exception as e:
        print(f"⚠️ Style check failed: {e} (non-blocking)")
        return True, 0


def main():
    """Simulate the deployment check process."""
    print("🚀 Simulating Deployment Pre-Check\n")
    print("=" * 50)
    
    # Step 1: Critical checks (blocking)
    syntax_ok = run_syntax_check()
    
    # Step 2: Style checks (non-blocking)
    style_ok, style_issues = run_style_check()
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 DEPLOYMENT DECISION:")
    
    if syntax_ok:
        print("✅ DEPLOYMENT APPROVED")
        print("   → No syntax errors found")
        if style_issues > 0:
            print(f"   → {style_issues} style issues documented for future cleanup")
        else:
            print("   → Code follows style guidelines")
        print("\n🚀 Proceeding with deployment...")
        return 0
    else:
        print("❌ DEPLOYMENT BLOCKED")
        print("   → Syntax errors must be fixed first")
        print("\n🛑 Fix syntax errors before deploying")
        return 1


if __name__ == "__main__":
    sys.exit(main())
