# GitHub Actions Version Upgrade Analysis

## Summary

This document analyzes the usage of outdated GitHub Actions in the ViolentUTF repository and identifies required changes for upgrading to newer versions.

## Actions Analyzed

1. **aquasecurity/trivy-action**: 0.12.0 → 0.32.0
2. **actions/download-artifact**: 3.0.2 → 4.3.0
3. **softprops/action-gh-release**: 1 → 2
4. **docker/setup-qemu-action**: 3.0.0 → 3.6.0
5. **github/codeql-action**: 2 → 3

## Current Usage Analysis

### 1. aquasecurity/trivy-action

**Current Usage:**
- **File**: `.github/workflows/ci-pr.yml` (line 169)
- **Version**: 0.14.0 (already partially updated)
- **Context**: Used for security scanning in PR quick checks

**Status**: ✅ Already using a newer version (0.14.0), though not the latest (0.32.0)

### 2. actions/download-artifact

**Current Usage:**
- **File**: `.github/workflows/nightly.yml` (line 378)
- **Version**: 3.0.2
- **Context**: Used to download all artifacts in nightly report generation

**Status**: ⚠️ Needs update from v3 to v4

### 3. softprops/action-gh-release

**Current Usage:**
- **File**: `.github/workflows/release.yml` (line 182)
- **Version**: v1
- **Context**: Used to create GitHub releases

**Status**: ⚠️ Needs update from v1 to v2

### 4. docker/setup-qemu-action

**Current Usage:**
- **File**: `.github/workflows/release.yml` (line 118)
- **Version**: 3.0.0
- **Context**: Used for multi-platform Docker builds

**Status**: ✅ Already using v3 (3.0.0), just needs minor version bump to 3.6.0

### 5. github/codeql-action

**Current Usage:**
- **File**: `.github/workflows/ci-pr.yml` (line 178) - v3.29.1 (upload-sarif)
- **File**: `.github/workflows/ci-nightly.yml` (line 125) - v3.29.1 (upload-sarif)
- **File**: `.github/workflows/full-ci.yml` (lines 150, 253) - v2 (upload-sarif)

**Status**: ⚠️ Mixed versions - some files use v3, but full-ci.yml still uses v2

## Breaking Changes and Required Updates

### 1. actions/download-artifact v3 → v4

**Breaking Changes:**
- v4 requires Node.js 20 (workflow runner must support it)
- Default behavior change: artifacts are now downloaded to separate directories by default
- The `name` parameter behavior has changed when downloading multiple artifacts

**Required Changes in `nightly.yml`:**
```yaml
# Old (line 378)
- uses: actions/download-artifact@9bc31d5ccc31df68ecc42ccf4149144866c47d8a # v3.0.2
  with:
    path: nightly-artifacts

# New
- uses: actions/download-artifact@c850b930e6ba138125429b7e5c93fc707a7f8427 # v4.1.4
  with:
    path: nightly-artifacts
    merge-multiple: true  # Add this to maintain v3 behavior
```

### 2. softprops/action-gh-release v1 → v2

**Breaking Changes:**
- v2 requires Node.js 20
- Some parameter names have changed
- Better error handling and validation

**Required Changes in `release.yml`:**
```yaml
# Old (line 182)
- uses: softprops/action-gh-release@de2c0eb89ae2a093876385947365aca7b0e5f844 # v1

# New
- uses: softprops/action-gh-release@c062e08bd532815e2082a85e87e3ef29c3e6d191 # v2.0.8
```

**Note**: The current usage appears compatible with v2, no parameter changes needed.

### 3. docker/setup-qemu-action v3.0.0 → v3.6.0

**No Breaking Changes**: This is a minor version update within v3.

**Required Changes in `release.yml`:**
```yaml
# Old (line 118)
- uses: docker/setup-qemu-action@68827325e0b33c7199eb31dd4e31fbe9023e06e3 # v3.0.0

# New
- uses: docker/setup-qemu-action@49b3bc8e6bdd4a60e6116a5414239cba5943d3cf # v3.2.0
```

### 4. github/codeql-action v2 → v3

**Breaking Changes:**
- v3 requires Node.js 20
- Some deprecated parameters have been removed
- Better SARIF validation

**Required Changes in `full-ci.yml`:**
```yaml
# Old (lines 150, 253)
- uses: github/codeql-action/upload-sarif@v2

# New
- uses: github/codeql-action/upload-sarif@39edc492dbe16b1465b0cafca41432d857bdb31a # v3.29.1
```

### 5. aquasecurity/trivy-action (Optional Update)

While already using a newer version (0.14.0), consider updating to the latest:

**No Breaking Changes** between 0.14.0 and 0.32.0 that affect current usage.

**Optional Update in `ci-pr.yml`:**
```yaml
# Current (line 169)
- uses: aquasecurity/trivy-action@fbd16365eb88e12433951383f5e99bd901fc618f # v0.14.0

# Latest
- uses: aquasecurity/trivy-action@a20de5420d57c4102486cdd9578b45609c99d7eb # v0.32.0
```

## Recommended Update Order

1. **High Priority** (Breaking changes in full-ci.yml):
   - Update `github/codeql-action` from v2 to v3 in `full-ci.yml`

2. **Medium Priority** (Version consistency):
   - Update `actions/download-artifact` from v3 to v4 in `nightly.yml`
   - Update `softprops/action-gh-release` from v1 to v2 in `release.yml`

3. **Low Priority** (Minor updates):
   - Update `docker/setup-qemu-action` from v3.0.0 to v3.6.0
   - Update `aquasecurity/trivy-action` from v0.14.0 to v0.32.0

## Testing Recommendations

1. Test the changes in a feature branch first
2. Run the workflows manually using `workflow_dispatch` where available
3. Pay special attention to:
   - Artifact download behavior in nightly reports
   - Release creation process
   - SARIF upload functionality
4. Ensure all runners support Node.js 20 (Ubuntu 22.04 runners do)

## Additional Notes

- All the updated actions require Node.js 20, which is supported by `ubuntu-22.04` runners
- The repository is already using commit SHA pinning for security, which is excellent
- Consider enabling Dependabot for GitHub Actions to automate future updates