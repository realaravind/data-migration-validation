# Schema Substitution Implementation Summary

## Overview

The environment-specific schema substitution feature has been successfully implemented to handle workload queries from SQL Server Query Store. This allows the same query to be executed against both SQL Server and Snowflake environments, even when they use different schema names.

## Problem Solved

When workload queries are captured from SQL Server Query Store, they contain schema names like `SAMPLE_DIM` and `SAMPLE_FACT`. However, in Snowflake, these schemas are mapped to `DIM` and `FACT`. The system now automatically transforms queries for each environment:

- **SQL Server**: Queries use original schema names from Query Store (e.g., `SAMPLE_DIM`, `SAMPLE_FACT`)
- **Snowflake**: Queries are transformed using schema mappings (e.g., `SAMPLE_DIM` → `DIM`, `SAMPLE_FACT` → `FACT`)

## Implementation Details

### 1. Schema Mapping Configuration

**File**: `backend/data/projects/{project_id}/config/schema_mappings.yaml`

Example for project `ps5`:
```yaml
SAMPLE_DIM: DIM
SAMPLE_FACT: FACT
```

This mapping file tells the system how to transform schema names for Snowflake.

### 2. Schema Substitution Function

**File**: `ombudsman_core/src/ombudsman/validation/sql_utils.py`

**Function**: `substitute_schema_names(sql_text, schema_mappings, target_database=None)`

**Capabilities**:
- Handles all SQL identifier formats:
  - 3-part: `database.schema.table` → `database.TARGET_SCHEMA.table`
  - 2-part: `schema.table` → `TARGET_SCHEMA.table`
  - 1-part: `FROM schema` → `FROM TARGET_SCHEMA`
- Case-insensitive matching
- Processes mappings longest-first to avoid partial replacements
- Uses regex for robust pattern matching

**Example Transformations**:
```sql
-- Input Query
SELECT * FROM SAMPLE_DIM.DIM_CUSTOMER JOIN SAMPLEDW.SAMPLE_FACT.FACT_SALES

-- After Substitution (with mappings SAMPLE_DIM→DIM, SAMPLE_FACT→FACT)
SELECT * FROM DIM.DIM_CUSTOMER JOIN SAMPLEDW.FACT.FACT_SALES
```

### 3. Workload Query Validation

**File**: `ombudsman_core/src/ombudsman/validation/business/validate_custom_queries.py`

**Changes Made**:
1. Added `metadata` parameter to function signature
2. Loads schema mappings from project configuration on startup
3. Accepts same query for both environments in query definition
4. Applies schema substitution ONLY to Snowflake queries
5. Logs all transformations with `[SCHEMA_SUBSTITUTION]` prefix

**Query Definition Format**:
```python
{
    "name": "Sales by Customer",
    "sql_query": "SELECT * FROM SAMPLE_DIM.DIM_CUSTOMER",  # Original query from Query Store
    "snow_query": None,  # Will use sql_query and transform it
    "comparison_type": "rowset",
    "tolerance": 0.01
}
```

Or simply provide one query:
```python
{
    "name": "Sales by Customer",
    "query": "SELECT * FROM SAMPLE_DIM.DIM_CUSTOMER",  # Used for both, transformed for Snowflake
    "comparison_type": "rowset"
}
```

## Testing the Implementation

### 1. Verify Schema Substitution Function

Test the function directly in the container:

```bash
docker exec ombudsman-validation-studio-studio-backend-1 python3 -c "
from ombudsman.validation.sql_utils import substitute_schema_names
test_sql = 'SELECT * FROM SAMPLE_DIM.DIM_CUSTOMER JOIN SAMPLEDW.SAMPLE_FACT.FACT_SALES'
result = substitute_schema_names(test_sql, {'SAMPLE_DIM': 'DIM', 'SAMPLE_FACT': 'FACT'})
print('Before:', test_sql)
print('After:', result)
"
```

**Expected Output**:
```
Before: SELECT * FROM SAMPLE_DIM.DIM_CUSTOMER JOIN SAMPLEDW.SAMPLE_FACT.FACT_SALES
After: SELECT * FROM DIM.DIM_CUSTOMER JOIN SAMPLEDW.FACT.FACT_SALES
```

### 2. Monitor Backend Logs During Execution

When executing a workload validation pipeline, monitor logs for schema substitution activity:

```bash
docker logs -f ombudsman-validation-studio-studio-backend-1 2>&1 | grep SCHEMA_SUBSTITUTION
```

**Expected Log Messages**:
```
[SCHEMA_SUBSTITUTION] Loaded schema mappings for project 'ps5': {'SAMPLE_DIM': 'DIM', 'SAMPLE_FACT': 'FACT'}
[SCHEMA_SUBSTITUTION] Transformed Snowflake query for 'Sales by Customer':
[SCHEMA_SUBSTITUTION] SQL Server will use: SELECT * FROM SAMPLE_DIM.DIM_CUSTOMER...
[SCHEMA_SUBSTITUTION] Snowflake BEFORE: SELECT * FROM SAMPLE_DIM.DIM_CUSTOMER...
[SCHEMA_SUBSTITUTION] Snowflake AFTER:  SELECT * FROM DIM.DIM_CUSTOMER...
```

### 3. Execute a Workload Validation

**Steps**:
1. Navigate to "Workload Analysis" in the UI (http://localhost:3002)
2. Create or load a workload batch with queries containing `SAMPLE_DIM` and `SAMPLE_FACT`
3. Execute the batch
4. Monitor backend logs (as shown above)
5. Verify results show no "Schema does not exist" errors
6. Check that SQL Server and Snowflake queries both execute successfully

### 4. Verify Error Resolution

The original error:
```
Validation failed: 002003 (02000): SQL compilation error:
Schema 'SAMPLEDW.SAMPLE_FACT' does not exist or not authorized.
```

Should no longer occur when executing workload validations, because:
- SQL Server queries keep `SAMPLE_FACT` (which exists in SQL Server)
- Snowflake queries are transformed to use `FACT` (which exists in Snowflake)

## Configuration Files

### Active Project
```bash
cat backend/data/active_project.txt
# Output: ps5
```

### Schema Mappings
```bash
cat backend/data/projects/ps5/config/schema_mappings.yaml
# Output:
# SAMPLE_DIM: DIM
# SAMPLE_FACT: FACT
```

### Environment Variables
```bash
docker exec ombudsman-validation-studio-studio-backend-1 env | grep -E "SNOWFLAKE_SCHEMA|SNOWFLAKE_DATABASE"
# Expected:
# SNOWFLAKE_SCHEMA=FACT
# SNOWFLAKE_DATABASE=SAMPLEDW
```

## Troubleshooting

### Schema Mapping Not Loading

**Symptoms**: No `[SCHEMA_SUBSTITUTION]` logs appear

**Solutions**:
1. Verify `backend/data/active_project.txt` contains correct project ID
2. Check that `backend/data/projects/{project_id}/config/schema_mappings.yaml` exists
3. Verify YAML syntax is correct (no tabs, proper indentation)

### Queries Still Using Wrong Schema

**Symptoms**: "Schema does not exist" errors persist

**Solutions**:
1. Check logs for transformation messages
2. Verify schema mappings are correct (source → target)
3. Ensure workload queries are passed through `validate_custom_queries`
4. Rebuild backend container: `docker-compose build studio-backend && docker-compose up -d`

### Partial Schema Replacement

**Symptoms**: Only some schema names are transformed

**Solutions**:
1. Check that all required schemas are in `schema_mappings.yaml`
2. Verify schema names match exactly (case-insensitive but spelling must match)
3. Add logging to see which mappings are being applied

## Current System Status

✅ **Implemented**:
- Schema substitution function with comprehensive pattern matching
- Project-specific schema mapping configuration
- Workload query validation with environment-specific transformation
- Detailed logging with `[SCHEMA_SUBSTITUTION]` prefix
- Documentation updates

✅ **Tested**:
- Schema substitution function works correctly in container
- Schema mappings load successfully for project `ps5`
- Transformation logic handles all SQL identifier formats

⏳ **Ready for Testing**:
- Execute workload validation pipeline in UI
- Verify no "Schema does not exist" errors
- Confirm both SQL Server and Snowflake queries execute successfully

## Next Steps

1. **Execute a workload validation** in the UI to test the full workflow
2. **Monitor backend logs** to verify schema substitution is working
3. **Verify results** show successful execution on both environments
4. **Create additional schema mappings** for other projects as needed

## Support

If issues persist:
1. Check backend logs for detailed error messages
2. Verify database connections are working
3. Ensure Query Store queries are formatted correctly
4. Review schema names in both SQL Server and Snowflake

---

**Implementation Date**: January 11, 2026
**Project**: Ombudsman Validation Studio
**Module**: Workload-Based Validation with Environment-Specific Schema Substitution
