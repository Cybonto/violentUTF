# Fix for "Trigger PR Validation" Failure

## Problem
The "Trigger PR Validation" job fails with error:
```
Unhandled error: HttpError: No ref found for: refs/pull/50/merge
```

## Root Cause
The CI dispatcher workflow (`ci.yml`) is trying to trigger the `pr-validation.yml` workflow using `context.ref`, which for pull requests points to `refs/pull/{number}/merge`. However, when a PR has failing checks or is in an "UNSTABLE" state, GitHub doesn't create this merge reference.

## Current Code Issue
In `.github/workflows/ci.yml` line 115:
```yaml
ref: context.ref  # This fails for PRs with failing checks
```

## Solution
The workflow needs to use the appropriate reference based on the event type:

```yaml
- name: Trigger PR validation workflow
  uses: actions/github-script@d7906e4ad0b1822421a7e6a35d5ca353c962f410
  with:
    script: |
      // For pull requests, use the head ref instead of the merge ref
      let ref;
      if (context.eventName === 'pull_request') {
        ref = context.payload.pull_request.head.ref;
      } else {
        ref = context.ref;
      }
      
      await github.rest.actions.createWorkflowDispatch({
        owner: context.repo.owner,
        repo: context.repo.repo,
        workflow_id: 'pr-validation.yml',
        ref: ref
      });
      console.log(`Triggered pr-validation workflow on ref: ${ref}`);
```

## Alternative Solution (Simpler)
Use the head SHA directly for pull requests:

```yaml
- name: Trigger PR validation workflow
  uses: actions/github-script@d7906e4ad0b1822421a7e6a35d5ca353c962f410
  with:
    script: |
      const ref = context.eventName === 'pull_request' 
        ? context.payload.pull_request.head.sha 
        : context.ref;
        
      await github.rest.actions.createWorkflowDispatch({
        owner: context.repo.owner,
        repo: context.repo.repo,
        workflow_id: 'pr-validation.yml',
        ref: ref
      });
      console.log(`Triggered pr-validation workflow on ref: ${ref}`);
```

## Why This Happens
1. PR #50 has failing checks (Code Quality, etc.)
2. GitHub marks the PR as "UNSTABLE" 
3. GitHub doesn't create the `refs/pull/50/merge` reference for unstable PRs
4. The workflow tries to use this non-existent reference and fails

## Impact
This prevents the PR validation workflow from running, which could mask other issues that need to be fixed.

## Verification
After applying the fix:
1. The "Trigger PR Validation" job should succeed
2. The actual `pr-validation.yml` workflow should run
3. Individual checks (Code Quality, Tests, etc.) can then run and report their status

## Note
This is a common issue in GitHub Actions when dealing with pull requests that have failing status checks. The fix ensures the workflow can run regardless of the PR's merge state.