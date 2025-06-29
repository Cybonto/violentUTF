#!/usr/bin/env python3
"""
Fix GitHub Actions YAML files with multi-line Python string issues.
"""
import re
import os
import sys

def fix_python_multiline_strings(content):
    """Fix multi-line Python strings in YAML files."""
    
    # Pattern to find python -c with double quotes
    pattern = r'(\s+)python -c "([^"]*(?:\n[^"]*)*)"'
    
    def replace_python_block(match):
        indent = match.group(1)
        code = match.group(2)
        
        # If the code contains both single and double quotes, use heredoc
        if "'" in code and '"' in code:
            # Use heredoc approach
            return f'{indent}cat > temp_script.py << \'EOF\'\n{code}\n{indent}EOF\n{indent}python temp_script.py\n{indent}rm temp_script.py'
        elif '"' in code:
            # Use single quotes
            return f"{indent}python -c '{code}'"
        else:
            # Keep double quotes (no issue)
            return match.group(0)
    
    # Apply the fix
    fixed_content = re.sub(pattern, replace_python_block, content, flags=re.MULTILINE | re.DOTALL)
    
    return fixed_content

def fix_trailing_spaces(content):
    """Remove trailing spaces from each line."""
    lines = content.split('\n')
    fixed_lines = [line.rstrip() for line in lines]
    return '\n'.join(fixed_lines)

def ensure_final_newline(content):
    """Ensure file ends with a newline."""
    if not content.endswith('\n'):
        content += '\n'
    return content

def fix_workflow_file(filepath):
    """Fix a single workflow file."""
    print(f"Processing {filepath}...")
    
    try:
        with open(filepath, 'r') as f:
            content = f.read()
        
        original_content = content
        
        # Apply fixes
        content = fix_python_multiline_strings(content)
        content = fix_trailing_spaces(content)
        content = ensure_final_newline(content)
        
        if content != original_content:
            with open(filepath, 'w') as f:
                f.write(content)
            print(f"  ✓ Fixed {filepath}")
            return True
        else:
            print(f"  - No changes needed for {filepath}")
            return False
            
    except Exception as e:
        print(f"  ✗ Error processing {filepath}: {e}")
        return False

def main():
    """Main function to fix all workflow files."""
    workflow_dir = '.github/workflows'
    
    if not os.path.exists(workflow_dir):
        print(f"Error: {workflow_dir} directory not found!")
        print("Please run this script from the repository root.")
        sys.exit(1)
    
    print("GitHub Actions YAML Fixer")
    print("=" * 50)
    
    fixed_count = 0
    error_count = 0
    
    for filename in sorted(os.listdir(workflow_dir)):
        if filename.endswith('.yml') or filename.endswith('.yaml'):
            filepath = os.path.join(workflow_dir, filename)
            if fix_workflow_file(filepath):
                fixed_count += 1
            else:
                error_count += 1
    
    print("\n" + "=" * 50)
    print(f"Summary: {fixed_count} files fixed, {error_count} files with errors or no changes")
    
    if fixed_count > 0:
        print("\nPlease review the changes and run yamllint to verify:")
        print("  yamllint -d relaxed .github/workflows/*.yml")

if __name__ == "__main__":
    main()