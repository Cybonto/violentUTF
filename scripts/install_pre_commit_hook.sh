#!/bin/bash
# Script to install pre-commit hook for ViolentUTF

echo "Installing ViolentUTF pre-commit hook..."

# Check if .git directory exists
if [ ! -d ".git" ]; then
    echo "Error: Not in a git repository root directory"
    exit 1
fi

# Create hooks directory if it doesn't exist
mkdir -p .git/hooks

# Create the pre-commit hook
cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
# ViolentUTF pre-commit hook

echo "Running pre-commit checks..."

# Run the pre-commit check script
if [ -f "scripts/pre_commit_check.py" ]; then
    python scripts/pre_commit_check.py
    exit_code=$?

    if [ $exit_code -ne 0 ]; then
        echo ""
        echo "❌ Pre-commit checks failed!"
        echo "Fix the issues above or run with --fix:"
        echo "  python scripts/pre_commit_check.py --fix"
        echo ""
        echo "To bypass this check (not recommended):"
        echo "  git commit --no-verify"
        exit $exit_code
    fi
else
    echo "Warning: pre_commit_check.py not found, skipping checks"
fi

exit 0
EOF

# Make the hook executable
chmod +x .git/hooks/pre-commit

echo "✅ Pre-commit hook installed successfully!"
echo ""
echo "The hook will run automatically before each commit."
echo "To run checks manually: python scripts/pre_commit_check.py"
echo "To run with auto-fix: python scripts/pre_commit_check.py --fix"
echo "To bypass (not recommended): git commit --no-verify"
