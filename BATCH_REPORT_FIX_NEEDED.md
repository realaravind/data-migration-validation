# Batch Report Issues - Comprehensive Fix Required

## Date: 2026-01-01

## Critical Issues Found

### 1. Custom SQL Validations ALL FAILING
**Location**: FACT_SALES table
**Error**: "Parameter mismatch for validator 'custom_sql': object of type 'NoneType' has no len()"
**Status**: ERROR (not FAIL)
**Impact**: All 10+ custom_sql validations in FACT_SALES pipeline show ERROR status
**Root Cause**: The custom_sql validator is receiving None for a parameter that expects a list/string

### 2. Batch Report Generator Missing Validation Details
**Location**: `backend/batch/report_generator.py`
**Issue**: The `generate_batch_report()` creates:
- `executive_summary` ✓ (working)
- `aggregate_metrics` ✓ (working)
- `table_summary` ✓ (working)
- `pipeline_details` ✗ (EMPTY - no validation details!)

**Individual pipeline files have**:
```json
{
  "results": [
    {
      "name": "validate_schema_columns",
      "status": "FAIL",
      "details": {
        "sql_columns": [...],
        "mismatches": [...]
      }
    }
  ]
}
```

**But report generator creates**:
```json
{
  "pipeline_details": [
    {
      "pipeline_id": null,
      "table_name": null,
      "validations": [
        {
          "name": "validate_schema_columns",
          "status": "FAIL",
          "details": {}  // ← EMPTY!
        }
      ]
    }
  ]
}
```

### 3. Frontend Rendering "[object Object]"
**Cause**: Frontend expects validation details with:
- `mismatches` array for failed validations
- `debugging_query` for SQL to investigate
- Proper object structures

**Getting**: Empty `details: {}` objects, which React renders as "[object Object]"

## Individual File Analysis

**Individual Pipeline Result** (`run_20260101_212731.json`):
- ✓ Complete validation details
- ✓ Mismatches arrays populated
- ✓ Details objects with all keys

**Consolidated Batch File** (`batch_13d3c629...json`):
- ✓ Summary stats (passed, failed counts)
- ✗ NO validation details
- ✗ NO mismatches arrays
- ✗ Just table-level summaries

**Batch Report API Response**:
- ✓ Pulls from consolidated file
- ✗ Doesn't pull detailed validations from individual pipeline files
- ✗ Creates empty `pipeline_details` entries

## Fixes Needed

### Fix 1: Custom SQL Parameter Issue
**File**: Likely in `ombudsman_core/src/ombudsman/validation/` custom_sql validator
**Action**: Find where `len()` is called on a None value and add null check

### Fix 2: Report Generator Enhancement
**File**: `backend/batch/report_generator.py`
**Action**: Modify `generate_batch_report()` to:
1. Load individual pipeline result files (run_20260101_*.json)
2. Extract full validation details from each
3. Include in `pipeline_details` section
4. Add `debugging_queries` section with SQL for failed validations

### Fix 3: Frontend Rendering
**File**: Likely `frontend/src/pages/RunComparison.tsx` or similar
**Action**: Handle mismatches/details rendering properly:
- Render mismatch arrays as tables
- Show "View Comparison" buttons for failures
- Display debugging queries in expandable sections

## Testing Plan

1. Fix custom_sql validator parameter issue
2. Re-run batch execution to get clean results
3. Fix report generator to include detailed validation data
4. Test frontend rendering with complete data
5. Verify all [object Object] issues resolved
6. Confirm debugging queries and comparison buttons appear

## Files Modified

- TBD: custom_sql validator
- `backend/batch/report_generator.py`
- Frontend component for batch results display

## Status

**Investigation**: COMPLETE
**Fixes Applied**: PENDING
**Testing**: PENDING
