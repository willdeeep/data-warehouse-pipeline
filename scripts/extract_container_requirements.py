#!/usr/bin/env python3
"""
Extract and compare package versions between requirements files and container reality.
This ensures our requirements files match the exact versions installed in the containerized environment.
"""

import subprocess
import re
from typing import Dict, Set, List, Tuple

def get_container_packages() -> Dict[str, str]:
    """Get all packages and versions from the Docker container."""
    try:
        result = subprocess.run([
            'docker', 'run', '--rm', 'astro-package-check', 'pip', 'freeze'
        ], capture_output=True, text=True, check=True)
        
        packages = {}
        for line in result.stdout.splitlines():
            line = line.strip()
            if line and not line.startswith('#') and not line.startswith('Astro Runtime'):
                # Handle different pip freeze formats
                if '==' in line:
                    name, version = line.split('==', 1)
                    packages[name.lower()] = line  # Store the full line for exact format
                elif ' @ ' in line:
                    # Handle packages installed from URLs (like astronomer packages)
                    parts = line.split(' @ ')
                    name = parts[0]
                    packages[name.lower()] = line
        
        return packages
    except subprocess.CalledProcessError as e:
        print(f"Error getting container packages: {e}")
        return {}

def parse_requirements_file(filepath: str) -> Dict[str, str]:
    """Parse a requirements file and return package->line mapping."""
    packages = {}
    try:
        with open(filepath, 'r') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if line and not line.startswith('#') and not line.startswith('-'):
                    # Extract package name from various formats
                    if '==' in line:
                        name = line.split('==')[0].split('[')[0].strip()
                        packages[name.lower()] = (line, line_num)
                    elif '>=' in line:
                        name = line.split('>=')[0].split('[')[0].strip()
                        packages[name.lower()] = (line, line_num)
                    elif '~=' in line:
                        name = line.split('~=')[0].split('[')[0].strip()
                        packages[name.lower()] = (line, line_num)
                    elif line and not any(op in line for op in ['>', '<', '!', '=']):
                        # Just package name
                        name = line.split()[0].strip()
                        packages[name.lower()] = (line, line_num)
    except FileNotFoundError:
        print(f"File {filepath} not found")
    
    return packages

def normalize_package_name(name: str) -> str:
    """Normalize package names for comparison (handle dashes vs underscores)."""
    return re.sub(r'[-_.]+', '-', name.lower())

def main():
    print("🐳 Extracting package versions from containerized environment...")
    
    # Get container packages
    container_packages = get_container_packages()
    if not container_packages:
        print("❌ Failed to get container packages")
        return
    
    print(f"📦 Found {len(container_packages)} packages in container")
    
    # Parse current requirements files
    requirements_packages = parse_requirements_file('requirements.txt')
    test_requirements_packages = parse_requirements_file('test-requirements.txt')
    
    print(f"📋 Current requirements.txt has {len(requirements_packages)} packages")
    print(f"📋 Current test-requirements.txt has {len(test_requirements_packages)} packages")
    
    # Find packages in requirements that are installed in container with different versions
    container_normalized = {normalize_package_name(k): v for k, v in container_packages.items()}
    
    print("\n🔍 Analyzing requirements.txt against container...")
    requirements_updates = []
    requirements_missing = []
    requirements_matched = []
    
    for pkg_name, (req_line, line_num) in requirements_packages.items():
        normalized_name = normalize_package_name(pkg_name)
        
        if normalized_name in container_normalized:
            container_line = container_normalized[normalized_name]
            if '==' in req_line and req_line != container_line:
                requirements_updates.append((pkg_name, req_line, container_line, line_num))
            else:
                requirements_matched.append((pkg_name, req_line))
        else:
            requirements_missing.append((pkg_name, req_line, line_num))
    
    print("\n🔍 Analyzing test-requirements.txt against container...")
    test_requirements_updates = []
    test_requirements_missing = []
    test_requirements_matched = []
    
    for pkg_name, (req_line, line_num) in test_requirements_packages.items():
        normalized_name = normalize_package_name(pkg_name)
        
        if normalized_name in container_normalized:
            container_line = container_normalized[normalized_name]
            if '==' in req_line and req_line != container_line:
                test_requirements_updates.append((pkg_name, req_line, container_line, line_num))
            else:
                test_requirements_matched.append((pkg_name, req_line))
        else:
            test_requirements_missing.append((pkg_name, req_line, line_num))
    
    # Report findings
    print(f"\n📊 ANALYSIS RESULTS:")
    print(f"   requirements.txt: {len(requirements_matched)} matched, {len(requirements_updates)} need updates, {len(requirements_missing)} missing from container")
    print(f"   test-requirements.txt: {len(test_requirements_matched)} matched, {len(test_requirements_updates)} need updates, {len(test_requirements_missing)} missing from container")
    
    if requirements_updates:
        print(f"\n⚠️  Version mismatches in requirements.txt:")
        for pkg_name, req_line, container_line, line_num in requirements_updates:
            print(f"   Line {line_num}: {req_line} -> {container_line}")
    
    if test_requirements_updates:
        print(f"\n⚠️  Version mismatches in test-requirements.txt:")
        for pkg_name, req_line, container_line, line_num in test_requirements_updates:
            print(f"   Line {line_num}: {req_line} -> {container_line}")
    
    if requirements_missing:
        print(f"\n❌ Packages in requirements.txt but NOT in container:")
        for pkg_name, req_line, line_num in requirements_missing:
            print(f"   Line {line_num}: {req_line}")
    
    if test_requirements_missing:
        print(f"\n❌ Packages in test-requirements.txt but NOT in container:")
        for pkg_name, req_line, line_num in test_requirements_missing:
            print(f"   Line {line_num}: {req_line}")
    
    # Show key container packages that might be relevant
    print(f"\n🔑 Key packages in container (Airflow/dbt/Google):")
    for pkg_name, line in container_packages.items():
        if any(keyword in pkg_name for keyword in ['airflow', 'dbt', 'google', 'apache', 'astronomer']):
            print(f"   {line}")
    
    print(f"\n✅ Analysis complete! Container uses:")
    print(f"   - Astro Runtime: 11.8.0")
    print(f"   - Apache Airflow: 2.9.3+astro.2") 
    print(f"   - Python: 3.11.9")

if __name__ == "__main__":
    main()
