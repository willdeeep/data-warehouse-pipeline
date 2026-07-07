#!/usr/bin/env python3
"""Final cleanup script to fix remaining flake8 issues."""

import os
import re
import subprocess
import sys
from pathlib import Path


def fix_line_length_issues(content: str) -> str:
    """Fix line length issues by breaking long lines."""
    lines = content.split('\n')
    fixed_lines = []
    
    for line in lines:
        if len(line) <= 79:
            fixed_lines.append(line)
            continue
            
        # Don't break lines that are just strings or comments
        stripped = line.strip()
        if stripped.startswith('#') or stripped.startswith('"""') or stripped.startswith("'''"):
            fixed_lines.append(line)
            continue
            
        # Try to break at logical points
        if ' and ' in line and len(line) > 79:
            # Break at 'and' keyword
            parts = line.split(' and ')
            if len(parts) == 2:
                indent = len(line) - len(line.lstrip())
                first_part = parts[0] + ' and'
                second_part = ' ' * (indent + 4) + parts[1]
                if len(first_part) <= 79 and len(second_part) <= 79:
                    fixed_lines.extend([first_part, second_part])
                    continue
        
        if ', ' in line and len(line) > 79:
            # Try to break at comma
            parts = line.split(', ')
            if len(parts) > 1:
                indent = len(line) - len(line.lstrip())
                current_line = parts[0]
                
                for i, part in enumerate(parts[1:], 1):
                    if len(current_line + ', ' + part) <= 79:
                        current_line += ', ' + part
                    else:
                        fixed_lines.append(current_line + ',')
                        current_line = ' ' * (indent + 4) + part
                
                fixed_lines.append(current_line)
                continue
        
        # If we can't break it nicely, just keep it as is
        fixed_lines.append(line)
    
    return '\n'.join(fixed_lines)


def fix_spacing_issues(content: str) -> str:
    """Fix spacing issues around equals signs and other operators."""
    # Fix E251: unexpected spaces around keyword / parameter equals
    content = re.sub(r'(\w+)\s*=\s*([^=])', r'\1=\2', content)
    
    # Fix E204: whitespace after decorator '@'
    content = re.sub(r'@\s+', '@', content)
    
    # Fix E502: the backslash is redundant between brackets
    lines = content.split('\n')
    fixed_lines = []
    for line in lines:
        if line.strip().endswith('\\') and ('(' in line or '[' in line):
            # Remove redundant backslash
            line = line.rstrip('\\').rstrip()
        fixed_lines.append(line)
    
    return '\n'.join(fixed_lines)


def fix_indentation_issues(content: str) -> str:
    """Fix indentation issues."""
    lines = content.split('\n')
    fixed_lines = []
    
    for i, line in enumerate(lines):
        # Fix E131: continuation line unaligned for hanging indent
        if i > 0 and line.strip() and not line.startswith('    '):
            prev_line = lines[i-1]
            if (prev_line.strip().endswith(',') or prev_line.strip().endswith('(') or 
                prev_line.strip().endswith('[') or prev_line.strip().endswith('=')):
                # This might be a continuation line that needs proper indentation
                if line.lstrip() == line.strip():  # No indentation
                    prev_indent = len(prev_line) - len(prev_line.lstrip())
                    line = ' ' * (prev_indent + 4) + line.strip()
        
        fixed_lines.append(line)
    
    return '\n'.join(fixed_lines)


def should_skip_file(file_path: Path) -> bool:
    """Check if file should be skipped."""
    skip_patterns = [
        '__pycache__',
        '.pyc',
        'dbt_packages',  # Third-party dbt packages
        '.venv',
        '.git'
    ]
    
    return any(pattern in str(file_path) for pattern in skip_patterns)


def process_python_file(file_path: Path) -> bool:
    """Process a single Python file to fix linting issues."""
    if should_skip_file(file_path):
        return False
        
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Apply fixes
        content = fix_spacing_issues(content)
        content = fix_indentation_issues(content)
        # Note: Skipping line length fixes as they can be complex and break code
        
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Fixed: {file_path}")
            return True
            
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        
    return False


def main():
    """Main function to clean up linting issues."""
    base_dir = Path(__file__).parent.parent
    
    # Process DAGs and tests
    dirs_to_process = [
        base_dir / 'dags',
        base_dir / 'tests'
    ]
    
    total_fixed = 0
    
    for directory in dirs_to_process:
        if directory.exists():
            print(f"Processing {directory}...")
            
            for file_path in directory.rglob('*.py'):
                if process_python_file(file_path):
                    total_fixed += 1
    
    print(f"\nFixed {total_fixed} files")
    
    # Run flake8 to check remaining issues
    print("\nChecking remaining issues...")
    try:
        result = subprocess.run([
            'flake8', '--count', '--statistics', 
            str(base_dir / 'dags'), 
            str(base_dir / 'tests')
        ], capture_output=True, text=True, cwd=base_dir)
        
        if result.returncode == 0:
            print("✅ No flake8 issues remaining!")
        else:
            lines = result.stdout.strip().split('\n')
            if lines:
                count_line = lines[-1]
                print(f"Remaining issues: {count_line}")
    
    except FileNotFoundError:
        print("flake8 not found - please install with: pip install flake8")


if __name__ == '__main__':
    main()
