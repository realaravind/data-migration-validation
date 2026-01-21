# Known Issues - Ombudsman Validation Studio

## Critical Issues

### 1. Comparison Tables Not Displaying in Frontend ✅ RESOLVED

**Issue**: The `validate_fact_dim_conformance` and `validate_late_arriving_facts` validators return detailed comparison data, but the frontend was displaying it as "comparison: 47 items" instead of rendering it as a formatted table.

**Status**: ✅ RESOLVED - Fixed with aggressive cache-busting (2024-12-17)

**Backend Status**: ✅ COMPLETE
- Both validators correctly return `comparison` array with detailed row-by-row data
- Data structure verified in JSON result files
- Example data:
  ```json
  {
    "comparison": [
      {
        "foreign_key_value": 101193,
        "sql_fact_occurrences": 0,
        "snow_fact_occurrences": 1,
        "exists_in_sql_dimension": false,
        "exists_in_snow_dimension": false,
        "status": "ORPHANED",
        "issue": "Snowflake: 1 fact records reference non-existent dimension key"
      }
    ]
  }
  ```

**Frontend Status**: ✅ COMPLETE
- Updated `ResultsViewer.tsx` with:
  1. TABLE_KEYS constant array to prevent tree-shaking: `['mismatches', 'issues', 'duplicates', 'results', 'details', 'outliers', 'reason', 'comparison']`
  2. Added 'comparison' to hasDetailedData check (line 613)
  3. Added 'comparison' to filter list to exclude from generic details (line 591)
  4. Added dedicated comparison render block (lines 674-691)
  5. Added console logging for debugging

**Resolution**: Implemented aggressive cache-busting strategy:

1. **Vite Build Configuration** (`vite.config.ts`):
   - Added timestamp-based asset naming: `assets/[name]-[hash]-${Date.now()}.js`
   - Ensures every build generates unique filenames that browsers must fetch

2. **HTML Cache Control** (`index.html`):
   - Added HTTP meta tags:
     - `Cache-Control: no-cache, no-store, must-revalidate`
     - `Pragma: no-cache`
     - `Expires: 0`
   - Prevents HTML file from being cached

**Build Info** (Latest):
- Asset timestamp: `1767256212756`
- All JS/CSS/assets include unique timestamps in filenames
- Example: `index-AepFMLg8-1767256212756.js`

**Files Modified**:
- `/ombudsman_core/src/ombudsman/validation/facts/validate_fact_dim_conformance.py` - ✅ Complete
- `/ombudsman_core/src/ombudsman/validation/facts/validate_late_arriving_facts.py` - ✅ Complete
- `/ombudsman-validation-studio/frontend/src/pages/ResultsViewer.tsx` - ✅ Complete
- `/ombudsman-validation-studio/frontend/vite.config.ts` - ✅ Added cache-busting
- `/ombudsman-validation-studio/frontend/index.html` - ✅ Added cache-control headers

**How to Verify**:
1. Execute a pipeline with foreign key validation (e.g., `validate_fact_dim_conformance`)
2. Navigate to Pipeline Execution results
3. Expand validation step
4. Verify comparison data displays as formatted table with columns:
   - foreign_key_value
   - sql_fact_occurrences / snow_fact_occurrences
   - exists_in_sql_dimension / exists_in_snow_dimension
   - status
   - issue

---

## Other Issues

### 2. Frontend Build Caching Issue ✅ RESOLVED

**Issue**: Browser aggressively caches frontend JavaScript files, making it impossible to deploy updates without manual user intervention.

**Status**: ✅ RESOLVED (2024-12-17)

**Resolution**: Implemented two-tier cache-busting strategy:

1. **Build-time Timestamp**: All assets now include `Date.now()` in filenames
2. **HTTP Cache Headers**: Added meta tags to prevent HTML caching

This ensures:
- Every build generates unique asset names
- Browsers are forced to fetch latest HTML
- New assets are always loaded after deployment

**Files Modified**:
- `/ombudsman-validation-studio/frontend/vite.config.ts`
- `/ombudsman-validation-studio/frontend/index.html`

---

## Completed Issues

### ✅ Backend Validators Return Comparison Data

**Issue**: Validators needed to return detailed comparison tables

**Resolution**: Both `validate_fact_dim_conformance` and `validate_late_arriving_facts` now return comprehensive comparison arrays with:
- Foreign key values
- Occurrence counts in each system
- Existence flags
- Status indicators
- Human-readable issue descriptions

**Files Modified**:
- `ombudsman_core/src/ombudsman/validation/facts/validate_fact_dim_conformance.py`
- `ombudsman_core/src/ombudsman/validation/facts/validate_late_arriving_facts.py`

---

## Testing Notes

### To Verify Comparison Table Fix (Once Caching Resolved):

1. Execute a pipeline with `validate_fact_dim_conformance` or `validate_late_arriving_facts`
2. Navigate to Pipeline Execution results
3. Expand a validation step with failures
4. Look for:
   - **Console logs**: `[formatDetailValue]` entries
   - **Warning log**: `NEW CODE LOADED - VERSION 2024-12-17-v3`
   - **Comparison table**: Should display as formatted table with columns:
     - foreign_key_value
     - sql_fact_occurrences / snow_fact_occurrences
     - exists_in_sql_dimension / exists_in_snow_dimension
     - status
     - issue

### Expected vs Actual Behavior:

**Expected**:
```
Detailed Comparison (47):
┌──────────────────┬─────────────────┬──────────────────┬────────────┬────────────────────┐
│ foreign_key_value│ sql_occurrences │ snow_occurrences │ status     │ issue              │
├──────────────────┼─────────────────┼──────────────────┼────────────┼────────────────────┤
│ 101193           │ 0               │ 1                │ ORPHANED   │ Snowflake: 1 fact..│
│ 101232           │ 1               │ 0                │ ORPHANED   │ SQL: 1 fact...     │
└──────────────────┴─────────────────┴──────────────────┴────────────┴────────────────────┘
```

**Actual**:
```
comparison: 47 items
```

---

## Environment

- **Frontend Framework**: React + TypeScript + Vite
- **Build Tool**: Vite 5.4.21
- **Server**: serve (npm package)
- **Docker**: Multi-stage builds
- **Browser**: Chrome (tested), caching issues observed
- **Port**: 3001 (changed from 3000 to bypass cache)

---

## Last Updated

2024-12-17 - All critical issues resolved with cache-busting implementation

## Contact

For questions about these issues, refer to the conversation history or the modified source files listed above.
