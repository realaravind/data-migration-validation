# Code Review Action Items

**Review Date:** 2026-01-18
**Reviewer:** Amelia (Dev Agent)
**Commit:** 6d36609

---

## Completed (Committed)

- [x] Fix undefined `db` variable in `auth/router.py:447, 481` - Runtime crash
- [x] Remove hardcoded password defaults in `pipelines/execute.py:461, 488`
- [x] Fix CORS wildcard in `main.py` - Now uses `CORS_ORIGINS` env var
- [x] Fix bare except clauses in `validate_custom_sql.py:149, 445`

---

## Remaining Action Items

### HIGH Priority

#### 1. Frontend Hardcoded API URL
**Files:** `ombudsman-validation-studio/frontend/src/App.tsx:181, 214, 241, 265`

**Problem:**
```typescript
const response = await fetch('http://localhost:8000/projects/list');
```

**Solution:**
1. Create `.env` file with `VITE_API_URL=http://localhost:8000`
2. Update fetch calls to use: `${import.meta.env.VITE_API_URL}/projects/list`
3. Update `vite.config.ts` to include env variable handling

**Affected Files:**
- `App.tsx`
- Any other components with hardcoded API URLs

---

### MEDIUM Priority

#### 2. Remove Debug Print Statements
**Files:** Multiple

| File | Lines to Review |
|------|-----------------|
| `validate_custom_sql.py` | 291-296, 500-501 |
| `pipelines/execute.py` | 292, 348, 361, 367, 510-515 |
| `workload/api.py` | 328-356, 384 |

**Solution:**
- Remove debug prints OR
- Convert to proper logging: `logger.debug(f"...")`

---

#### 3. Hardcoded sys.path Manipulation
**File:** `ombudsman-validation-studio/backend/connections/test.py:72`

**Problem:**
```python
sys.path.insert(0, "/core/src")
```

**Solution:**
- Use relative imports
- Or proper package installation with `pip install -e .`

---

#### 4. Missing Authentication on Workload Endpoints
**File:** `ombudsman-validation-studio/backend/workload/api.py`

**Endpoints without auth:**
- `POST /upload` (line 37)
- `GET /list/{project_id}` (line 82)
- `DELETE /{project_id}/{workload_id}` (line 454)
- Multiple other endpoints

**Solution:**
Add authentication dependency:
```python
from auth.dependencies import require_user_or_admin, optional_authentication
from auth.models import UserInDB

@router.post("/upload")
async def upload_workload(
    file: UploadFile = File(...),
    project_id: str = Body(...),
    current_user: UserInDB = Depends(require_user_or_admin)  # Add this
):
```

---

#### 5. Global Mutable State in Intelligent Router
**File:** `ombudsman-validation-studio/backend/mapping/intelligent_router.py:283`

**Problem:**
```python
global intelligent_mapper
intelligent_mapper = IntelligentMapper()
```

**Solution:**
Use dependency injection or thread-safe singleton:
```python
from functools import lru_cache

@lru_cache()
def get_intelligent_mapper():
    return IntelligentMapper()
```

---

## Testing Checklist

After implementing fixes, verify:

- [ ] Auth endpoints work (login, logout, password change)
- [ ] CORS works from frontend (check browser console)
- [ ] Pipeline execution succeeds with env-based credentials
- [ ] No debug prints in production logs
- [ ] Workload endpoints require authentication

---

## Notes

- The `CORS_ORIGINS` env var defaults to `http://localhost:3000,http://localhost:5173`
- For production, set `CORS_ORIGINS` to your actual frontend domain(s)
- Password env vars (`MSSQL_PASSWORD`, `SNOWFLAKE_PASSWORD`) now required
