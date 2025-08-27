#!/bin/bash
# Setup ultra-fast pre-commit for GitHub Desktop

echo "🚀 Setting up ultra-fast pre-commit for GitHub Desktop..."
echo ""

# Backup current configuration
if [ -f .git/hooks/pre-commit ]; then
    cp .git/hooks/pre-commit .git/hooks/pre-commit.backup
    echo "💾 Backed up current pre-commit hook"
fi

# Install ultra-fast configuration
echo "⚡ Installing ultra-fast configuration..."
pre-commit install --config .pre-commit-config-ultrafast.yaml

echo ""
echo "✅ Ultra-fast pre-commit configured!"
echo ""
echo "📊 Performance comparison:"
echo "  Before: ~3-5 seconds (25+ hooks)"
echo "  After:  ~0.3 seconds (5 critical hooks)"
echo "  Speedup: 10-15x faster!"
echo ""
echo "🔍 What's still checked:"
echo "  ✅ Python syntax errors (check-ast)"
echo "  ✅ Large file prevention (>5MB)"
echo "  ✅ JSON validation"
echo "  ✅ Trailing whitespace (auto-fix)"
echo "  ✅ Critical hardcoded secrets"
echo ""
echo "⚠️  What's skipped (for speed):"
echo "  • MyPy type checking"
echo "  • Pylint analysis"
echo "  • Full bandit security scan"
echo "  • Test file validation"
echo "  • Documentation linting"
echo ""
echo "💡 To run full checks before pushing:"
echo "  pre-commit run --all-files --config .pre-commit-config.yaml"
echo ""
echo "🔄 To restore full pre-commit:"
echo "  pre-commit install  # (uses default config)"
