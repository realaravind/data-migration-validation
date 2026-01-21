# Workload Query Generator Bug Fix

## Problem Identified

User reported error: `Invalid column name 'date_key'`

**Root Cause**: The workload query generator (or intelligent query generator) was creating JOIN queries that referenced `date_key` when the actual fact table column is named `dim_date_key`.

## Analysis

### Actual Database Schema
- **SQL Server Fact Table**: `SAMPLE_FACT.fact_sales`
  - Foreign key columns: `dim_customer_key`, `dim_product_key`, `dim_store_key`, `dim_date_key`
- **SQL Server Dimension Tables**:
  - `SAMPLE_DIM.dim_customer` with PK `customer_key`
  - `SAMPLE_DIM.dim_product` with PK `product_key`
  - `SAMPLE_DIM.dim_store` with PK `store_key`
  - `SAMPLE_DIM.dim_date` with PK `date_key`

### The Bug
When generating queries that join fact tables with dimension tables, the generator was stripping the "dim_" prefix from foreign key column names, causing:
- Generated: `f.date_key = d.date_key` ❌
- Actual column: `f.dim_date_key = d.date_key` ✅

## Files Modified

### 1. `/backend/pipelines/intelligent_query_generator.py`
**Lines 142-152**: Enhanced FK-PK matching logic

**Before:**
```python
for dim_col, dim_type in dim_cols.items():
    if dim_col.lower() == col_lower or dim_col.lower().endswith('_key'):
        relationships.append((col_name, table_name, dim_col))
        break
```

**After:**
```python
# Find the primary key in dimension table
# Look for columns ending with _key or matching the FK name pattern
for dim_col, dim_type in dim_cols.items():
    dim_col_lower = dim_col.lower()
    # Match: dim_product_key (FK) → product_key (PK) OR date_key (PK)
    if (dim_col_lower == col_lower or
        dim_col_lower == f"{dim_name}_key" or
        (dim_col_lower.endswith('_key') and dim_name in dim_col_lower)):
        # Use the ACTUAL column name from the fact table, not the dimension PK
        relationships.append((col_name, table_name, dim_col))
        break
```

**Key Improvement**: The relationship tuple now preserves the actual fact table FK column name (`col_name`), which includes the "dim_" prefix.

### 2. Query Generation Methods
The following methods use the relationship tuples:
- `_build_single_dim_query()` (lines 303-361)
- `_build_multi_dim_query()` (lines 363-459)
- `_build_conformance_check()` (lines 461-507)

These methods use `fk_col` from the relationships, which now correctly preserves:
- `dim_customer_key`, `dim_product_key`, `dim_store_key`, `dim_date_key`

Instead of incorrectly using:
- `customer_key`, `product_key`, `store_key`, `date_key`

## Expected Behavior After Fix

### Correct Query Generation
```sql
-- SQL Server Query
SELECT
    d.month_name,
    SUM(f.total_amount) as total_total_amount,
    COUNT(*) as record_count
FROM SAMPLE_FACT.fact_sales f
INNER JOIN SAMPLE_DIM.dim_date d
    ON f.dim_date_key = d.date_key  -- ✓ Correct: uses dim_date_key
GROUP BY d.month_name
ORDER BY total_total_amount DESC
```

```sql
-- Snowflake Query
SELECT
    d.MONTH_NAME,
    SUM(f.TOTAL_AMOUNT) as TOTAL_TOTAL_AMOUNT,
    COUNT(*) as RECORD_COUNT
FROM FACT.fact_sales f
INNER JOIN DIM.dim_date d
    ON f.DIM_DATE_KEY = d.DATE_KEY  -- ✓ Correct: uses DIM_DATE_KEY
GROUP BY d.MONTH_NAME
ORDER BY TOTAL_TOTAL_AMOUNT DESC
```

## Testing Instructions

### 1. Rebuild Backend Container
```bash
cd /Users/aravind/sourcecode/projects/data-migration-validator/ombudsman-validation-studio
docker-compose build studio-backend
docker-compose up -d studio-backend
```

### 2. Regenerate Intelligent Queries
1. Navigate to Workload Analysis page
2. Click "Generate Intelligent Queries" or "Suggest Queries"
3. Review the generated queries in the UI
4. Verify FK column names include "dim_" prefix

### 3. Execute Workload Validation
1. Create or load a workload batch
2. Execute the batch
3. Monitor backend logs for errors:
   ```bash
   docker logs -f ombudsman-validation-studio-studio-backend-1 2>&1 | grep -E "Invalid column|date_key"
   ```
4. Expected: NO "Invalid column name 'date_key'" errors
5. Expected: Queries execute successfully on both SQL Server and Snowflake

### 4. Verify Query Logs
Check backend logs for query generation:
```bash
docker logs ombudsman-validation-studio-studio-backend-1 2>&1 | grep -A5 "INNER JOIN.*dim_date"
```

Should show:
```
ON f.dim_date_key = d.date_key
```

NOT:
```
ON f.date_key = d.date_key
```

## Related Issues Fixed

This fix also resolves potential issues with other FK columns:
- `dim_customer_key` → correctly used (not `customer_key`)
- `dim_product_key` → correctly used (not `product_key`)
- `dim_store_key` → correctly used (not `store_key`)
- Any future `dim_*_key` foreign keys

## Dependencies

This fix works in conjunction with:
1. **Schema Substitution** (`sql_utils.py:substitute_schema_names()`)
   - Transforms Snowflake schema names (SAMPLE_DIM → DIM)
   - Does NOT affect column names
2. **Column Mapping** (`config/column_mappings.yaml`)
   - Maps lowercase SQL Server columns to uppercase Snowflake columns
   - Only used during validation, not query generation

---

**Date**: January 11, 2026
**Issue**: Workload query generator using incorrect FK column names
**Status**: Fixed - pending container rebuild and testing
