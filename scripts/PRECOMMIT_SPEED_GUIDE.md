# Pre-commit Speed Optimization Guide

## 🎯 Quick Solutions for GitHub Desktop

### Option 1: Ultra-Fast Setup (Recommended)
```bash
bash scripts/setup_fast_github_desktop.sh
```
**Result**: ~0.3 seconds (10-15x faster)

### Option 2: Balanced Fast Setup
```bash
pre-commit install --config .pre-commit-config-fast.yaml
```
**Result**: ~0.7 seconds (4-5x faster)

## 📊 Performance Comparison

| Configuration | Time | Hooks | Use Case |
|---------------|------|-------|----------|
| Ultra-Fast    | 0.3s | 5 critical | GitHub Desktop commits |
| Fast          | 0.7s | 10 essential | Regular development |
| Full          | 3.3s | 25+ complete | Pre-push validation |

## 🚀 Speed Optimization Techniques Used

### 1. **File Pattern Filtering**
```yaml
files: '^(app|violentutf_api|scripts)/'  # Only main code
exclude: '__pycache__|\.mypy_cache|tests/'  # Skip generated files
```

### 2. **Hook Selection Strategy**
- **Ultra-Fast**: Only critical safety checks
- **Fast**: Essential quality + safety
- **Full**: Complete validation

### 3. **Directory Exclusions**
```yaml
exclude: "node_modules|\.git|\.mypy_cache|__pycache__|\.vitutf"
```

### 4. **Type-Specific Processing**
```yaml
types: [python]          # Only Python files
types_or: [yaml]         # YAML files only
```

## 🛠️ Manual Speed Optimizations

### For Existing Hooks:
```bash
# Test specific files only
pre-commit run --files app/core/auth.py

# Skip expensive hooks
pre-commit run --hook-stage manual mypy

# Run on staged files only (fastest)
pre-commit run
```

### Performance Monitoring:
```bash
# Benchmark configurations
python3 scripts/optimize_precommit_performance.py

# Time individual hooks
time pre-commit run black --all-files
```

## 🎭 Configuration Switching

### Switch to Ultra-Fast:
```bash
bash scripts/setup_fast_github_desktop.sh
```

### Switch to Full:
```bash
pre-commit install  # Uses .pre-commit-config.yaml
```

### Temporary Full Check:
```bash
pre-commit run --all-files --config .pre-commit-config.yaml
```

## 🔍 What Each Configuration Checks

### Ultra-Fast (0.3s)
- ✅ Python syntax errors (critical)
- ✅ Large files >5MB (prevents repo bloat)
- ✅ JSON syntax (prevents breakage)
- ✅ Trailing whitespace (auto-fix)
- ✅ Hardcoded secrets in main code

### Fast (0.7s)
- ✅ All Ultra-Fast checks
- ✅ YAML validation
- ✅ File permissions (shebangs)
- ✅ Black code formatting
- ✅ Comprehensive secret detection

### Full (3.3s)
- ✅ All Fast checks
- ✅ MyPy type checking
- ✅ Pylint static analysis
- ✅ Bandit security scanning
- ✅ Test structure validation
- ✅ Documentation linting
- ✅ License header insertion

## 💡 Best Practices

### Development Workflow:
1. **Daily commits**: Use Ultra-Fast (0.3s)
2. **Feature completion**: Use Fast (0.7s)
3. **Before push/PR**: Use Full (3.3s)

### Team Setup:
```bash
# For the team lead
pre-commit install  # Full validation

# For frequent committers
bash scripts/setup_fast_github_desktop.sh  # Ultra-fast
```

### CI/CD Integration:
- Local: Ultra-Fast or Fast
- CI Pipeline: Always Full
- Pre-merge: Full with --all-files

## 🚨 Troubleshooting

### If Ultra-Fast is Still Slow:
1. Check for large untracked files
2. Verify exclusion patterns working
3. Run: `pre-commit clean` to clear cache

### To Restore Original Config:
```bash
cp .git/hooks/pre-commit.backup .git/hooks/pre-commit
# OR
pre-commit install  # Reset to default
```

### Performance Debugging:
```bash
# See what files are being processed
pre-commit run check-ast --verbose --all-files

# Time individual components
time pre-commit run --config .pre-commit-config-ultrafast.yaml
```

## 📈 Expected Results

After implementing ultra-fast configuration:

- **10-15x faster** GitHub Desktop commits
- **Same safety** for critical issues (syntax, secrets, large files)
- **Maintains code quality** for main application code
- **Full validation** still available when needed

The ultra-fast configuration focuses on **preventing broken commits** while **maximizing development velocity**.
