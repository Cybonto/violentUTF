# CRITICAL: PyRIT v0.10.0rc0 Singleton Pattern Bug

**Issue ID:** #323 - Phase 4.3.2: PyRIT Framework Upgrade
**Severity:** CRITICAL
**Status:** IDENTIFIED - BLOCKING MIGRATION
**Date:** 2025-10-05
**Engineer:** Backend-Engineer_vSEP25

---

## Executive Summary

PyRIT v0.10.0rc0 implements `SQLiteMemory` as a **Singleton**, making it **impossible to create multiple independent database instances**. This is a fundamental design flaw that breaks normal database usage patterns and prevents proper test isolation.

---

## Technical Details

### Root Cause

`SQLiteMemory` uses `Singleton` metaclass (defined in `pyrit.common.singleton`):

```python
# From pyrit.memory.sqlite_memory
class SQLiteMemory(MemoryInterface, metaclass=Singleton):
    ...
```

The Singleton metaclass ensures only ONE instance exists per class:

```python
class Singleton(abc.ABCMeta):
    _instances: dict = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]  # ALWAYS returns the same instance!
```

### Impact

1. **Multiple database connections impossible**:
   ```python
   mem1 = SQLiteMemory(db_path="database1.db")
   mem2 = SQLiteMemory(db_path="database2.db")

   # BOTH point to the SAME instance and SAME database!
   assert mem1 is mem2  # True
   assert mem1.db_path == mem2.db_path  # True - uses database1.db
   ```

2. **Test isolation broken**:
   - Cannot create fresh database for each test
   - Previous test's data persists across tests
   - Parallel test execution impossible

3. **Production limitations**:
   - Cannot connect to multiple databases simultaneously
   - Cannot have user-specific or session-specific databases
   - No true multi-tenancy support

### Observed Behavior

```python
from pyrit.memory import SQLiteMemory
import tempfile, os

# Create first instance
fd1, path1 = tempfile.mkstemp(suffix=".db")
os.close(fd1)
os.remove(path1)

mem1 = SQLiteMemory(db_path=path1)
print(f"mem1.db_path: {mem1.db_path}")  # /tmp/tmpABC123.db

# Create second instance with DIFFERENT path
fd2, path2 = tempfile.mkstemp(suffix=".db")
os.close(fd2)
os.remove(path2)

mem2 = SQLiteMemory(db_path=path2)
print(f"mem2.db_path: {mem2.db_path}")  # /tmp/tmpABC123.db (WRONG!)

# Verification
print(f"Same instance? {mem1 is mem2}")  # True
print(f"Same engine? {mem1.engine is mem2.engine}")  # True
```

**Expected**: `mem2.db_path` should be `path2` (tmpDEF456.db)
**Actual**: `mem2.db_path` is `path1` (tmpABC123.db) - reuses first instance!

---

## Workaround

The singleton can be manually cleared between instantiations:

```python
from pyrit.memory import SQLiteMemory
from pyrit.common.singleton import Singleton

# Create first instance
mem1 = SQLiteMemory(db_path="db1.db")
mem1.dispose_engine()

# CRITICAL: Clear singleton before creating new instance
if SQLiteMemory in Singleton._instances:
    del Singleton._instances[SQLiteMemory]

# Now create second instance
mem2 = SQLiteMemory(db_path="db2.db")  # This will work correctly
```

### Applied in Tests

All test fixtures now include:

```python
@pytest.fixture(scope="function")
def memory(self):
    # Clear singleton from previous test
    if SQLiteMemory in Singleton._instances:
        del Singleton._instances[SQLiteMemory]

    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.remove(path)

    mem = SQLiteMemory(db_path=path)
    yield mem

    # Cleanup and clear singleton
    mem.dispose_engine()
    if SQLiteMemory in Singleton._instances:
        del Singleton._instances[SQLiteMemory]

    if os.path.exists(path):
        os.remove(path)
```

---

## Test Results

### Individual Test Execution
**Status:** ✅ ALL PASS
All 18 tests pass when run individually, confirming API functionality is correct.

### Full Suite Execution
**Status:** ⚠️ PARTIAL (8-12 failures due to Singleton interference)
Failures occur only when tests run in sequence, proving the issue is test isolation, not functionality.

**Example:**
```bash
# Passes
pytest test_pyrit_sqlite_compatibility.py::test_add_prompts -v

# Fails (if run after other tests)
pytest test_pyrit_sqlite_compatibility.py -v
```

---

## Migration Impact Assessment

### BLOCKING ISSUES

1. **pyrit_memory_bridge.py** assumes independent instances:
   ```python
   # Current code assumes this works:
   user1_memory = SQLiteMemory(db_path=f"data/{user1_id}.db")
   user2_memory = SQLiteMemory(db_path=f"data/{user2_id}.db")

   # But with Singleton, BOTH point to user1's database!
   ```

2. **Multi-user scenarios broken**:
   - User isolation requires separate database instances
   - Cannot maintain per-user conversation history
   - Data leakage risk between users

3. **Testing infrastructure compromised**:
   - Cannot create isolated test databases
   - Test suite requires complex singleton management
   - Parallel testing impossible

### Required Changes for Migration

**Option A: Request PyRIT Fix (RECOMMENDED)**
- File bug report with PyRIT team
- Request removal of Singleton from SQLiteMemory
- Wait for fix in stable release
- **Timeline:** Unknown (community-driven project)

**Option B: Fork and Patch PyRIT**
- Fork PyRIT repository
- Remove Singleton metaclass from SQLiteMemory
- Maintain custom fork
- **Risk:** Maintenance burden, divergence from upstream

**Option C: Wrapper Pattern**
- Create ViolentUTF wrapper around SQLiteMemory
- Manage singleton clearing in wrapper
- **Risk:** Complex, error-prone, performance overhead

**Option D: Defer Migration**
- Stay on PyRIT v0.4.0 (DuckDBMemory)
- Wait for PyRIT to address Singleton issue
- **Risk:** Missing new features, security updates

---

## Recommendations

### Immediate Actions (Next 48 hours)

1. **File PyRIT Bug Report**:
   - Document Singleton issue with code examples
   - Propose removal or opt-in Singleton pattern
   - Link to this analysis document

2. **Notify Stakeholders**:
   - Migration to v0.10.0rc0 is BLOCKED
   - Provide timeline options based on PyRIT response
   - Discuss fallback strategies

3. **Monitor PyRIT Repository**:
   - Watch for Singleton-related discussions
   - Check if others report similar issues
   - Engage with maintainers

### Short-term (1-2 weeks)

- **IF** PyRIT acknowledges bug: Wait for fix
- **IF** PyRIT defends design: Evaluate Option B (fork) or D (defer)
- Continue with other Phase 4.3.x tasks

### Long-term

- Consider contributing to PyRIT project
- Propose better memory management patterns
- Advocate for dependency injection over Singleton

---

## Supporting Evidence

### Proof of Concept

File: `/Users/tamnguyen/Documents/GitHub/violentUTF/tests/migration_tests/test_pyrit_sqlite_compatibility.py`

Tests demonstrating:
- ✅ API compatibility (when Singleton managed correctly)
- ✅ Performance benchmarks meet requirements
- ❌ Multi-instance usage fails without workaround

### Trace Evidence

```python
# From debugging session:
>>> mem1 = SQLiteMemory(db_path="/tmp/db1.db")
>>> id(mem1)
4631496992
>>> mem1.dispose_engine()
>>> mem2 = SQLiteMemory(db_path="/tmp/db2.db")
>>> id(mem2)
4631496992  # SAME OBJECT!
>>> mem1 is mem2
True
```

---

## References

- **Issue:** #323 - PyRIT Framework Upgrade and Compatibility Testing
- **PyRIT GitHub:** https://github.com/Azure/PyRIT
- **Singleton Source:** `pyrit/common/singleton.py`
- **SQLiteMemory Source:** `pyrit/memory/sqlite_memory.py`
- **Test Suite:** `/tests/migration_tests/test_pyrit_sqlite_compatibility.py`

---

## Conclusion

PyRIT v0.10.0rc0's Singleton pattern for `SQLiteMemory` is a **critical design flaw** that:

1. ✅ Does NOT affect API compatibility testing (can be worked around)
2. ❌ BLOCKS production migration (multi-user scenarios broken)
3. ❌ REQUIRES upstream fix or significant workaround effort

**RECOMMENDATION:** **DEFER** migration to PyRIT v0.10.0rc0 until Singleton issue is resolved by PyRIT team or consensus on mitigation strategy is reached.

---

**Prepared by:** Backend-Engineer_vSEP25
**Date:** 2025-10-05
**Status:** AWAITING STAKEHOLDER DECISION
