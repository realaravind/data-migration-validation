# Comparison Viewer Usage Guide

## Overview

The **Comparison Viewer** is a powerful tool for examining row-by-row differences between SQL Server and Snowflake query results. However, it's designed for specific use cases and won't be applicable to all validation steps.

## When Comparison Viewer Works ✅

The comparison viewer is available when **ALL** of the following conditions are met:

1. **Both queries return the same number of rows** (matching row counts)
2. **Multi-row results** (not single-value comparisons like COUNT)
3. **Validation has been executed** (generates comparison_details)

### Example: comparative_validation_4_query_14

**Query Type**: Category-level aggregation with LEFT JOIN
**Results**: SQL Server (4 rows) vs Snowflake (4 rows) ✅
**Status**: FAIL (data mismatch)

**Why it works**:
- Both sides have 4 rows (matching counts)
- Multi-row dataset with multiple columns
- Data differs in values (perfect for side-by-side comparison)

**View in browser**:
```
http://localhost:3000/comparison/run_20251202_162513/comparative_validation_4_query_14
```

**What you'll see**:
- Side-by-side comparison of all 4 rows
- Highlighted cells showing which values differ
- Filter to show "All Rows" or "Different Only"
- Export to CSV option
- Full details: AVGPRICE, CATEGORY, PRODUCTCOUNT, TOTALSOLD comparisons

## When Comparison Viewer Doesn't Work ❌

### Case 1: Shape Mismatch (Different Row Counts)

**Example**: comparative_validation_2_query_7

**Query Type**: Product-Sales JOIN
**Results**: SQL Server (471 rows) vs Snowflake (482 rows) ❌
**Error**: "Shape mismatch: SQL Server (471, 2), Snowflake (482, 2)"

**Why it doesn't work**:
- SQL Server has 471 rows, Snowflake has 482 rows
- Cannot do row-by-row comparison when counts don't match
- This indicates a **data integrity issue** that needs investigation

**What to do**:
1. Investigate why row counts differ
2. Check for missing data in SQL Server or extra data in Snowflake
3. Verify JOIN conditions and foreign key relationships
4. Review data migration logs for this table

### Case 2: Single Value Comparisons (COUNT Queries)

**Example**: comparative_validation_1_query_4

**Query Type**: Simple COUNT(*)
**Results**: SQL Server (500) vs Snowflake (500) ✅
**Status**: PASS

**Why it doesn't work**:
- COUNT queries return a single value, not a multi-row dataset
- The result message already shows the comparison clearly
- No need for a detailed comparison viewer

**What you'll see**:
- Result message: "Result sets match ✓ (SQL: 500, Snowflake: 500)"
- No "View Comparison" button needed

### Case 3: Old Results (Before Fixes)

**Example**: run_20251202_091249

**Why it doesn't work**:
- Results generated before comparison_details feature was added
- Missing the necessary data structure for comparison viewer

**What to do**:
- Re-run the validation pipeline
- New runs will automatically include comparison_details

## Understanding the "View Comparison" Button

The button appears when:
- Step has `comparison_details` field
- Step has both `sql_row_count` and `snow_row_count`
- Step name includes "comparative", "custom_sql", or starts with "query_"

However, clicking it may still show "No comparison details available" if:
- The validation found a shape mismatch
- The query is a single-value comparison
- The results were generated before the feature was added

## Best Practices

### ✅ DO use Comparison Viewer for:
- Multi-row queries with matching row counts
- Investigating specific value differences
- Analyzing aggregation discrepancies
- Reviewing JOIN results with data mismatches

### ❌ DON'T expect Comparison Viewer for:
- Shape mismatches (different row counts)
- COUNT queries (single values)
- Queries that return 0 rows on both sides
- Old validation runs (before comparison_details feature)

## Troubleshooting

### "No comparison details available for this step"

**Check the error message**:
- "Shape mismatch" → Row counts differ, investigate data integrity
- "Result sets match" → Passing validation, no differences to show
- No error → Old results, re-run the validation

### Missing "View Comparison" Button

**Possible reasons**:
1. Validation not yet executed
2. Step is not a comparative validation
3. Frontend not detecting the step type correctly

**Solution**:
- Ensure pipeline has been executed successfully
- Check that step name includes "comparative" or "custom_sql"
- Verify results JSON has the necessary fields

## Technical Details

### API Endpoint
```
GET /execution/results/{run_id}/step/{step_name}/comparison
```

### Expected Response Structure
```json
{
  "run_id": "run_20251202_162513",
  "step_name": "comparative_validation_4_query_14",
  "status": "FAIL",
  "difference_type": "data_mismatch",
  "summary": {
    "total_rows": 4,
    "differing_rows": 4,
    "affected_columns": ["AVGPRICE", "CATEGORY", "PRODUCTCOUNT", "TOTALSOLD"],
    "message": "✗ Data mismatch found..."
  },
  "comparison": {
    "columns": ["AVGPRICE", "CATEGORY", "PRODUCTCOUNT", "TOTALSOLD"],
    "rows": [
      {
        "row_index": 0,
        "sql_values": {...},
        "snowflake_values": {...},
        "differing_columns": [...]
      }
    ]
  }
}
```

### Error Response
```json
{
  "error": "No comparison details available for this step",
  "message": "Shape mismatch: SQL Server (471, 2), Snowflake (482, 2)"
}
```

## Summary

The Comparison Viewer is working correctly and is available for the appropriate use cases. When you see "No comparison details available", it's usually indicating:

1. **Shape mismatch** → Data integrity issue requiring investigation
2. **Single value** → Simple comparison that doesn't need detailed viewer
3. **Old results** → Re-run the validation

For validations where both sides have matching row counts but different values (like `comparative_validation_4_query_14`), the comparison viewer provides a powerful side-by-side view of all differences.
