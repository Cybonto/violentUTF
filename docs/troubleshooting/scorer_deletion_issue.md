# Scorer Deletion Endpoint Troubleshooting

## Issue Description
The scorer deletion endpoint in FastAPI returns a 500 Internal Server Error despite apparently working correctly (the scorer is deleted from the database).

## Analysis Summary

### 1. **Endpoint Implementation** (`violentutf_api/fastapi_app/app/api/endpoints/scorers.py`)
- **Location**: Lines 632-661
- **Endpoint**: `DELETE /api/v1/scorers/{scorer_id}`
- **Key Steps**:
  1. Gets user_id from current_user.username
  2. Gets DuckDB manager for the user
  3. Retrieves scorer data to get name
  4. Calls `db_manager.delete_scorer(scorer_id)`
  5. Returns success response if deletion succeeds

### 2. **DuckDB Manager Implementation** (`violentutf_api/fastapi_app/app/db/duckdb_manager.py`)
- **Location**: Lines 688-721
- **Method**: `delete_scorer(self, scorer_id: str) -> bool`
- **Key Steps**:
  1. Checks if scorer exists (SELECT COUNT)
  2. Executes DELETE query
  3. Verifies deletion by checking COUNT again
  4. Returns True if count is 0 (successfully deleted)

### 3. **Potential Issues Identified**

#### Issue 1: DuckDB rowcount Property
The `delete_scorer` method in DuckDB manager doesn't use `conn.rowcount` after the DELETE operation, unlike other delete methods in the same file:
- `delete_generator` (line 385) - doesn't use rowcount
- `delete_dataset` (line 500) - uses `conn.rowcount > 0`
- `delete_converter` (line 621) - uses `conn.rowcount > 0`

This inconsistency suggests that the scorer deletion might not be properly checking if the DELETE actually affected any rows.

#### Issue 2: Transaction Handling
The method uses verification after deletion instead of relying on the DELETE operation's rowcount. This could indicate issues with:
- Transaction isolation
- Connection pooling
- Timing issues

#### Issue 3: Error Handling Chain
The error might be occurring after the successful deletion:
- The scorer is deleted successfully
- The response is being prepared
- Something in the response serialization or logging fails

### 4. **Error Manifestation**
- **Client Side** (Streamlit page): Shows "Server error while deleting scorer. Please try again."
- **Server Side**: Returns 500 but scorer is actually deleted
- **Database**: Scorer is removed successfully

## Recommendations

### 1. **Add Detailed Logging**
Add more granular logging in the delete endpoint to identify exactly where the error occurs:
```python
@router.delete("/{scorer_id}", response_model=ScorerDeleteResponse, summary="Delete scorer")
async def delete_scorer(scorer_id: str, current_user=Depends(get_current_user)):
    """Delete a scorer configuration"""
    try:
        user_id = current_user.username
        logger.info(f"Starting deletion of scorer {scorer_id} for user {user_id}")

        # Get scorer details before deletion
        db_manager = get_duckdb_manager(user_id)
        scorer_data = db_manager.get_scorer(scorer_id)
        logger.info(f"Retrieved scorer data: {scorer_data is not None}")

        if not scorer_data:
            logger.warning(f"Scorer {scorer_id} not found for deletion")
            raise HTTPException(status_code=404, detail=f"Scorer with ID '{scorer_id}' not found")

        scorer_name = scorer_data["name"]
        logger.info(f"Deleting scorer '{scorer_name}' (ID: {scorer_id})")

        # Perform deletion
        deleted = db_manager.delete_scorer(scorer_id)
        logger.info(f"Delete operation returned: {deleted}")

        if not deleted:
            logger.error(f"Delete operation failed for scorer {scorer_id}")
            raise HTTPException(status_code=500, detail=f"Failed to delete scorer with ID '{scorer_id}'")

        # Prepare response
        response = ScorerDeleteResponse(
            success=True,
            message="Scorer deleted successfully",
            deleted_scorer=scorer_name
        )
        logger.info(f"Successfully prepared delete response for scorer {scorer_id}")

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in delete_scorer endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete scorer: {str(e)}")
```

### 2. **Check Response Model**
Verify that the `ScorerDeleteResponse` model is properly defined and can be serialized. Check `app/schemas/scorers.py` for the model definition.

### 3. **Database Connection Management**
Ensure the DuckDB connection is properly closed and no lingering transactions are causing issues.

### 4. **Temporary Workaround**
As a temporary fix, the Streamlit UI could be modified to:
1. Call the delete endpoint
2. If it returns 500, verify if the scorer was actually deleted by calling the list endpoint
3. If deleted, show success message despite the 500 error

## Next Steps

1. **Enable detailed logging** in the FastAPI application
2. **Monitor the logs** during a delete operation
3. **Check the response model** serialization
4. **Test with curl/Postman** to isolate if it's a UI-specific issue
5. **Review any middleware** that might be interfering with the response

## Related Files
- `/violentutf_api/fastapi_app/app/api/endpoints/scorers.py` - API endpoint
- `/violentutf_api/fastapi_app/app/db/duckdb_manager.py` - Database operations
- `/violentutf/pages/4_Configure_Scorers.py` - Streamlit UI
- `/violentutf_api/fastapi_app/app/schemas/scorers.py` - Response models
