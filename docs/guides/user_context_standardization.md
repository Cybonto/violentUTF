# User Context Standardization Implementation

## Overview

Implemented a comprehensive user context standardization system to resolve scorer deletion issues and data fragmentation caused by inconsistent user identification across authentication methods.

## Problem Solved

- **Issue**: Scorers created under different username formats (`ViolentUTF Web User`, `Tam Nguyen`, `tam.nguyen@protonmail.com`, etc.) were isolated from each other
- **Symptom**: Scorers appeared in UI but couldn't be deleted, or scorers disappeared after authentication changes
- **Root Cause**: Inconsistent user identification between Streamlit token creation and FastAPI token processing

## Solution Implemented

### 1. Unified User Context Manager

**File**: `violentutf/utils/user_context_manager.py`

- Centralizes user normalization logic
- Maps various username formats to canonical forms:
  - `"ViolentUTF Web User"` → `"violentutf.web"`
  - `"Tam Nguyen"` → `"tam.nguyen"`  
  - `"tam.nguyen@protonmail.com"` → `"tam.nguyen"`
- Provides token consistency verification
- Handles automatic token refresh

### 2. FastAPI User Context Manager  

**File**: `violentutf_api/fastapi_app/app/core/user_context_manager.py`

- Mirrors Streamlit normalization rules exactly
- Extracts canonical usernames from JWT tokens
- Ensures consistent username handling in API endpoints

### 3. Updated Authentication Flow

**Files Modified**:
- `violentutf/utils/user_context.py` - Updated to use new manager
- `violentutf/pages/4_Configure_Scorers.py` - Enhanced token creation
- `violentutf_api/fastapi_app/app/core/auth.py` - Canonical username extraction

### 4. Database Layer Fix

**File**: `violentutf_api/fastapi_app/app/db/duckdb_manager.py`

- Fixed `delete_scorer` method to avoid DuckDB `rowcount` limitation
- Uses proper existence check → delete → verify pattern

## Key Benefits

1. **Consistent Data Access**: All operations use the same canonical username
2. **No More Fragmentation**: Scorers accessible regardless of authentication method  
3. **Automatic Normalization**: System handles different username formats transparently
4. **Backward Compatibility**: Existing code continues to work

## Usage

The system works automatically - no manual intervention needed. When users access the system:

1. **Streamlit** determines canonical username using `UserContextManager.get_canonical_username()`
2. **JWT tokens** are created with canonical usernames
3. **FastAPI** extracts canonical usernames from tokens using `FastAPIUserContextManager.extract_canonical_username()`
4. **Database operations** use consistent user identification

## Normalization Rules

```python
NORMALIZATION_RULES = {
    "ViolentUTF Web User": "violentutf.web",
    "Tam Nguyen": "tam.nguyen", 
    "tam.nguyen@protonmail.com": "tam.nguyen",
    "violentutf.web": "violentutf.web",
}
```

Additional rules:
- Email format → extract local part
- Names with spaces → convert to dot notation  
- Already clean format → lowercase

## Testing

The implementation includes comprehensive error handling and logging. Both managers provide identical normalization results:

```bash
# Test normalization consistency
python3 -c "
from violentutf.utils.user_context_manager import UserContextManager
from violentutf_api.fastapi_app.app.core.user_context_manager import FastAPIUserContextManager

test_cases = ['ViolentUTF Web User', 'Tam Nguyen', 'tam.nguyen@protonmail.com']
for user in test_cases:
    streamlit_result = UserContextManager.normalize_username(user)
    fastapi_result = FastAPIUserContextManager.normalize_username(user)
    assert streamlit_result == fastapi_result
    print(f'{user} -> {streamlit_result}')
"
```

## Migration

When rerunning setup, the system will automatically:
1. Create database files with correct canonical usernames
2. Use consistent user identification across all operations
3. Resolve scorer visibility and deletion issues

No manual migration is required - the setup process handles everything.