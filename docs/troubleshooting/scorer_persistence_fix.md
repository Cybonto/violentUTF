# Scorer Persistence Fix

## Issue Description
Users reported that previously configured scorers were not showing up after refreshing the Configure_Scorers page. The scorers were successfully saved to the database but wouldn't appear in the UI without manual intervention.

## Root Cause
The Configure_Scorers page was missing an auto-load mechanism for scorers. While generators had an `auto_load_generators()` function that was called during page initialization, there was no equivalent for scorers. This meant that `st.session_state.api_scorers` was empty on page load, even though scorers existed in the database.

## Solution
Added an `auto_load_scorers()` function that:
1. Automatically loads existing scorers from the API/database when the page loads
2. Populates the `st.session_state.api_scorers` dictionary
3. Ensures scorers are displayed immediately without requiring manual refresh

## Code Changes

### Added Function
```python
def auto_load_scorers():
    """
    Automatically load existing scorers on page load

    This ensures that previously configured scorers are displayed
    without requiring manual refresh.
    """
    # Always load scorers on page load to ensure we have the latest data
    with st.spinner("Loading existing scorers..."):
        data = load_scorers_from_api()
        if data:
            logger.info(f"Auto-loaded {len(st.session_state.api_scorers)} scorers")
        else:
            logger.info("No scorers found during auto-load")
```

### Updated main() Function
```python
def main():
    # ... authentication code ...

    # Auto-load generators (like Configure Datasets page)
    auto_load_generators()

    # Auto-load scorers to ensure they're displayed on page refresh
    auto_load_scorers()  # <-- NEW LINE ADDED

    # Main content
    render_main_content()
```

## Testing
To verify the fix:

1. Navigate to the Configure Scorers page
2. Create a new scorer configuration
3. Refresh the page (F5 or browser refresh)
4. The previously configured scorer should appear immediately in the "Scorer Management" section

## Technical Details
- Scorers are stored in DuckDB with user isolation
- The API endpoint `/api/v1/scorers` returns all scorers for the authenticated user
- The `load_scorers_from_api()` function fetches scorers and stores them in `st.session_state.api_scorers`
- This follows the same pattern used for generators in the Configure Datasets page

## Related Files
- `/violentutf/pages/4_Configure_Scorers.py` - Main page file with the fix
- `/violentutf_api/fastapi_app/app/api/endpoints/scorers.py` - API endpoint for scorer management
- `/violentutf_api/fastapi_app/app/db/duckdb_manager.py` - Database manager for scorer persistence
