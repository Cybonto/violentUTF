# ViolentUTF Master TODO List

This document tracks all pending tasks, improvements, and issues that need to be addressed in the ViolentUTF platform.

## High Priority Tasks

### 1. User Space Isolation Audit
**Priority**: HIGH  
**Status**: Pending  
**Description**: Check the consistency of user space isolation across all sections of the application. Ensure user A cannot see results/data from user B.

**Areas to audit**:
- [ ] Dashboard endpoints (currently no user filtering in `/summary` and `/scores`)
- [ ] Browse endpoint (user context filtering was removed to match Dashboard behavior)
- [ ] Orchestrator executions (check `created_by` field usage)
- [ ] PyRIT memory sessions (verify isolation)
- [ ] Generated reports and templates
- [ ] MCP server responses
- [ ] File uploads and datasets

**Action items**:
- [ ] Document current state of user isolation in each component
- [ ] Identify gaps where user context is not properly filtered
- [ ] Create a consistent pattern for user context filtering
- [ ] Implement fixes with proper testing
- [ ] Add integration tests for user isolation

### 2. API Browse Endpoint Enhancement
**Priority**: HIGH  
**Status**: Pending  
**Description**: Check the API `/browse` endpoint and how scorer data fields may need to be expanded to accommodate filters by the `/browse` endpoint.

**Technical details**:
- [ ] Review current score metadata structure
- [ ] Identify missing fields needed for filtering (e.g., generator_name, dataset_name)
- [ ] Ensure score metadata is consistently populated during execution
- [ ] Update browse endpoint filters to match actual data structure
- [ ] Optimize query performance for large datasets

**Related issues**:
- Browse endpoint currently returns 0 results in Report Setup
- Mismatch between Dashboard (uses simple filters) and Report Setup (complex filters)
- Score metadata stored as JSON may need indexing for performance

## Medium Priority Tasks

### 3. Report Setup Implementation
**Priority**: MEDIUM  
**Status**: In Progress  
**Description**: Complete the Report Setup page functionality

**Completed**:
- [x] Fix data loading issues (browse endpoint returning 0 results)
- [x] Implement Data Selection tab with multi-selection
- [x] Create browse endpoint with proper filtering
- [x] Handle missing orchestrator configurations with LEFT JOIN
- [x] Fix date boundary issues

**Remaining work**:
- [ ] Implement Template Selection tab
- [ ] Implement Configuration tab
- [ ] Implement Preview tab
- [ ] Implement Generate tab
- [ ] Add report storage and retrieval
- [ ] Create report generation backend service

### 4. Database Schema Consistency
**Priority**: MEDIUM  
**Status**: Pending  
**Description**: Ensure database models are complete and consistent

**Issues identified**:
- [ ] OrchestratorExecution model missing `target_model` field
- [ ] User context field naming inconsistency (`user_context` vs `created_by`)
- [ ] Add proper indexes for JSON fields used in queries
- [ ] Document all model relationships

## Low Priority Tasks

### 5. UI/UX Improvements
**Priority**: LOW  
**Status**: Pending  
**Description**: Enhance user interface consistency

**Tasks**:
- [ ] Standardize filter components across pages
- [ ] Improve error messages and user feedback
- [ ] Add loading states for all async operations
- [ ] Implement proper pagination UI components

### 6. Documentation Updates
**Priority**: LOW  
**Status**: Ongoing  
**Description**: Keep documentation up to date

**Areas**:
- [ ] API endpoint documentation
- [ ] User guides for new features
- [ ] Developer setup guides
- [ ] Architecture decisions

## Technical Debt

### 7. Code Refactoring
**Priority**: MEDIUM  
**Status**: Pending  
**Description**: Address technical debt and code quality

**Items**:
- [ ] Consolidate duplicate API request functions
- [ ] Standardize error handling patterns
- [ ] Remove deprecated functions (e.g., `load_orchestrator_executions_with_results`)
- [ ] Improve type hints and validation

### 8. Testing Coverage
**Priority**: MEDIUM  
**Status**: Pending  
**Description**: Improve test coverage

**Areas**:
- [ ] Add unit tests for new endpoints
- [ ] Create integration tests for user workflows
- [ ] Add performance tests for data-heavy endpoints
- [ ] Implement security tests for user isolation

## Bug Fixes

### 9. Known Issues
**Priority**: HIGH  
**Status**: Pending  
**Description**: Fix identified bugs

**Resolved bugs**:
- [x] Report Setup browse endpoint returns 0 results (Fixed: LEFT JOIN + date logic)
- [x] Date range filters excluding today's executions (Fixed: extended end date)

**Current bugs**:
- [ ] Test vs Full execution tracking inconsistency across the platform
  - Dashboard and Report Setup handle test execution filtering differently
  - Test mode metadata stored in JSON makes SQL filtering complex
  - Need consistent approach for identifying and filtering test executions
  - Current workaround loads all rows for accurate counting (performance impact)
- [ ] Generator filter not properly extracting from score metadata (needs metadata enrichment)
- [ ] Session state persistence issues in Streamlit
- [ ] Missing orchestrator configurations cause JOIN failures (mitigated with LEFT JOIN)
- [ ] Timezone handling between UI and database may need alignment

## Future Features

### 10. Advanced Features Wishlist
**Priority**: LOW  
**Status**: Planning  
**Description**: Features for future consideration

**Ideas**:
- [ ] Real-time execution monitoring
- [ ] Collaborative report editing
- [ ] Advanced visualization options
- [ ] Export to multiple formats (PDF, DOCX, etc.)
- [ ] Scheduled report generation
- [ ] Custom scorer development UI

---

## Notes

- This list should be reviewed and updated regularly
- Priority levels: HIGH (security/critical), MEDIUM (functionality), LOW (nice-to-have)
- Always backup database before making schema changes
- Follow branch-specific restrictions when implementing fixes

## Contributing

When working on any item:
1. Update the status to "In Progress"
2. Create a feature branch following naming conventions
3. Update this document when completing tasks
4. Add new items as they are discovered

Last Updated: 2025-07-20