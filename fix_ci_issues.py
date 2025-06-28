#!/usr/bin/env python3
"""
Script to fix common CI linting issues in ViolentUTF project
"""

import os
import re
from pathlib import Path

def fix_missing_imports():
    """Fix missing imports in test files"""
    
    fixes = {
        "tests/unit/mcp/test_server.py": {
            "imports": ["import json"],
            "after_line": "import"
        },
        "tests/unit/services/test_keycloak_verification.py": {
            "imports": ["from fastapi import HTTPException"],
            "after_line": "from fastapi"
        },
        "violentutf_api/fastapi_app/app/mcp/tools/introspection.py": {
            "imports": ["from typing import Union"],
            "after_line": "from typing import"
        }
    }
    
    for file_path, fix_info in fixes.items():
        if os.path.exists(file_path):
            print(f"Fixing imports in {file_path}")
            with open(file_path, 'r') as f:
                lines = f.readlines()
            
            # Find where to insert imports
            insert_idx = 0
            for i, line in enumerate(lines):
                if fix_info["after_line"] in line:
                    insert_idx = i + 1
                    break
            
            # Insert missing imports
            for imp in fix_info["imports"]:
                if not any(imp in line for line in lines):
                    lines.insert(insert_idx, f"{imp}\n")
                    insert_idx += 1
            
            # Write back
            with open(file_path, 'w') as f:
                f.writelines(lines)
            print(f"  ✓ Fixed {file_path}")

def fix_unused_globals():
    """Remove or comment out unused global declarations"""
    
    files_with_unused_globals = [
        "violentutf/generators/generator_config.py",
        "tests/test_all_endpoints.py"
    ]
    
    for file_path in files_with_unused_globals:
        if os.path.exists(file_path):
            print(f"Fixing unused globals in {file_path}")
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Comment out unused global declarations
            content = re.sub(
                r'^(\s*global\s+\w+\s*)$',
                r'# \1  # TODO: Remove or use this global',
                content,
                flags=re.MULTILINE
            )
            
            with open(file_path, 'w') as f:
                f.write(content)
            print(f"  ✓ Fixed {file_path}")

def add_conditional_imports():
    """Add conditional imports for optional dependencies"""
    
    file_path = "violentutf/pages/Simple_Chat.py"
    if os.path.exists(file_path):
        print(f"Adding conditional import to {file_path}")
        with open(file_path, 'r') as f:
            lines = f.readlines()
        
        # Find import section
        import_section_end = 0
        for i, line in enumerate(lines):
            if line.strip() and not line.startswith(('import', 'from', '#', 'try:', 'except')):
                import_section_end = i
                break
        
        # Add conditional import if not already present
        vertexai_import = """
try:
    import vertexai
except ImportError:
    vertexai = None
    print("Warning: vertexai not installed. Google Cloud AI features will be disabled.")

"""
        
        if not any('vertexai' in line and 'import' in line for line in lines):
            lines.insert(import_section_end, vertexai_import)
            
            with open(file_path, 'w') as f:
                f.writelines(lines)
            print(f"  ✓ Fixed {file_path}")

def main():
    """Run all fixes"""
    print("Fixing CI linting issues...")
    print("=" * 50)
    
    fix_missing_imports()
    fix_unused_globals()
    add_conditional_imports()
    
    print("\n" + "=" * 50)
    print("Fixes applied! Now run:")
    print("  1. flake8 violentutf/ violentutf_api/ tests/ --count --select=E9,F63,F7,F82")
    print("  2. black violentutf/ violentutf_api/ tests/")
    print("  3. isort violentutf/ violentutf_api/ tests/")
    print("\nThen commit and push to test CI workflow.")

if __name__ == "__main__":
    main()