# Intelligent Custom Query Suggestion System - Complete Guide

## Overview

The Intelligent Query Suggestion system automatically generates meaningful business validation queries based on your actual database schema. Instead of manually writing complex SQL queries, the system analyzes your metadata, table mappings, and relationships to suggest ready-to-use validation queries.

## How It Works

The system analyzes:
- **Metadata**: Table structures, columns, data types
- **Mappings**: SQL Server to Snowflake table/column mappings
- **Relationships**: Foreign key relationships between fact and dimension tables

Then automatically generates:
1. **Record Count Validations** - For all discovered tables
2. **Metric Aggregations** - Sum/avg for numeric columns in fact tables
3. **Join Validations** - Fact + dimension joins with aggregations
4. **Time-Based Analytics** - Monthly trends using date dimensions
5. **Top N Queries** - Top 5 records by dimension
6. **Complex Multi-Dimension Joins** - Advanced multi-table queries

## Complete Workflow

### Step 1: Extract Metadata

First, extract metadata from your databases:

```bash
curl -X POST http://localhost:8000/metadata/extract \
  -H "Content-Type: application/json" \
  -d '{
    "sql_database": "SampleDW",
    "sql_schemas": ["DIM", "FACT"],
    "snowflake_database": "SAMPLEDW",
    "snowflake_schemas": ["DIM", "FACT"]
  }'
```

This discovers:
- All tables in your schemas
- Column names and data types
- Primary keys and constraints
- Numeric columns (for aggregations)

### Step 2: Generate Table Mappings

Generate automatic mappings between SQL Server and Snowflake:

```bash
curl -X POST http://localhost:8000/mapping/suggest
```

This creates intelligent mappings using:
- Fuzzy name matching
- Prefix normalization (removes "dbo.", "fact_", etc.)
- Type compatibility checking
- Confidence scoring

### Step 3: Define Relationships (Optional but Recommended)

Create a relationships file to help the system understand joins:

**File: `/Users/aravind/sourcecode/projects/data-migration-validator/ombudsman_core/src/ombudsman/config/relationships.yaml`**

```yaml
# Fact -> Date Dimension
sales_date:
  fact_table: fact_sales
  dim_table: dim_date
  fact_key: DateKey
  dim_key: DateKey

# Fact -> Customer Dimension
sales_customer:
  fact_table: fact_sales
  dim_table: dim_customer
  fact_key: CustomerKey
  dim_key: CustomerKey

# Fact -> Product Dimension
sales_product:
  fact_table: fact_sales
  dim_table: dim_product
  fact_key: ProductKey
  dim_key: ProductKey
```

### Step 4: Generate Intelligent Suggestions

Now generate intelligent query suggestions:

```bash
curl -X POST http://localhost:8000/custom-queries/intelligent-suggest \
  | python3 -m json.tool
```

**Example Response:**

```json
{
  "status": "success",
  "total_suggestions": 15,
  "suggestions_by_category": {
    "Basic Validation": [
      {
        "name": "Record Count - fact_sales",
        "priority": "HIGH",
        "sql_query": "SELECT COUNT(*) as count FROM dbo.fact_sales",
        "snow_query": "SELECT COUNT(*) as count FROM SAMPLEDW.DIM.FACT_SALES"
      }
    ],
    "Metric Validation": [
      {
        "name": "Total SalesAmount - fact_sales",
        "priority": "HIGH",
        "tolerance": 0.01,
        "sql_query": "SELECT SUM(SalesAmount) as total, AVG(SalesAmount) as avg FROM dbo.fact_sales",
        "snow_query": "SELECT SUM(SalesAmount) as total, AVG(SalesAmount) as avg FROM SAMPLEDW.DIM.FACT_SALES"
      }
    ],
    "Join Validation": [
      {
        "name": "fact_sales by dim_customer",
        "priority": "MEDIUM",
        "limit": 20,
        "sql_query": "SELECT c.CustomerName, SUM(SalesAmount) as total FROM dbo.fact_sales f INNER JOIN dbo.dim_customer c ON f.CustomerKey = c.CustomerKey GROUP BY c.CustomerName ORDER BY total DESC",
        "snow_query": "SELECT c.CustomerName, SUM(SalesAmount) as total FROM SAMPLEDW.FACT.FACT_SALES f INNER JOIN SAMPLEDW.DIM.DIM_CUSTOMER c ON f.CustomerKey = c.CustomerKey GROUP BY c.CustomerName ORDER BY total DESC"
      }
    ],
    "Time-Based Validation": [
      {
        "name": "Monthly Trend - fact_sales",
        "priority": "HIGH",
        "limit": 12,
        "sql_query": "SELECT d.Year, d.Month, SUM(SalesAmount) as total FROM dbo.fact_sales f INNER JOIN dbo.dim_date d ON f.DateKey = d.DateKey GROUP BY d.Year, d.Month ORDER BY d.Year, d.Month",
        "snow_query": "SELECT d.Year, d.Month, SUM(SalesAmount) as total FROM SAMPLEDW.FACT.FACT_SALES f INNER JOIN SAMPLEDW.DIM.DIM_DATE d ON f.DateKey = d.DateKey GROUP BY d.Year, d.Month ORDER BY d.Year, d.Month"
      }
    ],
    "Top N Validation": [
      {
        "name": "Top 5 Customer",
        "priority": "MEDIUM",
        "limit": 5,
        "sql_query": "SELECT TOP 5 c.CustomerName, SUM(SalesAmount) as total FROM dbo.fact_sales f INNER JOIN dbo.dim_customer c ON f.CustomerKey = c.CustomerKey GROUP BY c.CustomerName ORDER BY total DESC",
        "snow_query": "SELECT c.CustomerName, SUM(SalesAmount) as total FROM SAMPLEDW.FACT.FACT_SALES f INNER JOIN SAMPLEDW.DIM.DIM_CUSTOMER c ON f.CustomerKey = c.CustomerKey GROUP BY c.CustomerName ORDER BY total DESC LIMIT 5"
      }
    ]
  },
  "message": "Generated 15 intelligent query suggestions based on your schema!",
  "next_steps": [
    "1. Review the suggestions below",
    "2. Copy the ones you want to custom_queries.yaml",
    "3. Or use /custom-queries/save-suggestions to auto-save them",
    "4. Run /custom-queries/validate-user-queries to test"
  ]
}
```

### Step 5: Save Suggestions (Auto-Save)

Automatically save suggestions to your config file:

```bash
curl -X POST http://localhost:8000/custom-queries/save-suggestions
```

This saves all suggestions to:
`/Users/aravind/sourcecode/projects/data-migration-validator/ombudsman_core/src/ombudsman/config/custom_queries.yaml`

**Response:**
```json
{
  "status": "success",
  "saved_count": 15,
  "saved_to": ".../custom_queries.yaml",
  "message": "Saved 15 intelligent query suggestions to custom_queries.yaml!",
  "next_steps": [
    "1. View them: GET /custom-queries/user-queries",
    "2. Validate them: POST /custom-queries/validate-user-queries"
  ]
}
```

### Step 6: Review User Queries

View the saved queries:

```bash
curl -X GET http://localhost:8000/custom-queries/user-queries \
  | python3 -m json.tool
```

### Step 7: Validate Custom Queries

Run validation on all saved queries:

```bash
curl -X POST http://localhost:8000/custom-queries/validate-user-queries \
  | python3 -m json.tool
```

**Example Result:**

```json
{
  "status": "success",
  "queries_validated": 15,
  "validation_result": {
    "summary": {
      "total_queries": 15,
      "passed": 14,
      "failed": 1
    },
    "results": [
      {
        "query": "Record Count - fact_sales",
        "status": "PASS",
        "explain": {
          "sql_result": {"count": 50000},
          "snow_result": {"count": 50000},
          "interpretation": "Record counts match: 50000 records in both databases",
          "execution_time_sql": 0.15,
          "execution_time_snow": 0.12
        }
      },
      {
        "query": "Total SalesAmount - fact_sales",
        "status": "PASS",
        "explain": {
          "sql_result": {"total": 5250000.50, "avg": 105.00},
          "snow_result": {"total": 5250000.50, "avg": 105.00},
          "interpretation": "Aggregations match within tolerance (0.01)",
          "execution_time_sql": 0.23,
          "execution_time_snow": 0.18
        }
      },
      {
        "query": "Monthly Trend - fact_sales",
        "status": "PASS",
        "explain": {
          "sql_sample": [
            {"Year": 2023, "Month": 1, "total": 450000},
            {"Year": 2023, "Month": 2, "total": 420000},
            {"Year": 2023, "Month": 3, "total": 480000}
          ],
          "snow_sample": [
            {"Year": 2023, "Month": 1, "total": 450000},
            {"Year": 2023, "Month": 2, "total": 420000},
            {"Year": 2023, "Month": 3, "total": 480000}
          ],
          "interpretation": "All 12 monthly aggregations match",
          "rows_compared": 12
        }
      }
    ]
  }
}
```

## What Gets Generated

### 1. Basic Validation (HIGH Priority)
```yaml
- name: "Record Count - fact_sales"
  comparison_type: "count"
  sql_query: "SELECT COUNT(*) as count FROM dbo.fact_sales"
  snow_query: "SELECT COUNT(*) as count FROM SAMPLEDW.FACT.FACT_SALES"
```

### 2. Metric Validation (HIGH Priority)
```yaml
- name: "Total SalesAmount - fact_sales"
  comparison_type: "aggregation"
  tolerance: 0.01
  sql_query: |
    SELECT
      SUM(SalesAmount) as total_salesamount,
      AVG(SalesAmount) as avg_salesamount,
      COUNT(*) as row_count
    FROM dbo.fact_sales
  snow_query: |
    SELECT
      SUM(SalesAmount) as total_salesamount,
      AVG(SalesAmount) as avg_salesamount,
      COUNT(*) as row_count
    FROM SAMPLEDW.FACT.FACT_SALES
```

### 3. Join Validation (MEDIUM Priority)
```yaml
- name: "fact_sales by dim_customer"
  comparison_type: "rowset"
  tolerance: 0.01
  limit: 20
  sql_query: |
    SELECT
      c.CustomerName,
      SUM(SalesAmount) as total_metric,
      COUNT(*) as record_count
    FROM dbo.fact_sales f
    INNER JOIN dbo.dim_customer c ON f.CustomerKey = c.CustomerKey
    GROUP BY c.CustomerName
    ORDER BY total_metric DESC
  snow_query: |
    SELECT
      c.CustomerName,
      SUM(SalesAmount) as total_metric,
      COUNT(*) as record_count
    FROM SAMPLEDW.FACT.FACT_SALES f
    INNER JOIN SAMPLEDW.DIM.DIM_CUSTOMER c ON f.CustomerKey = c.CustomerKey
    GROUP BY c.CustomerName
    ORDER BY total_metric DESC
```

### 4. Time-Based Validation (HIGH Priority)
```yaml
- name: "Monthly Trend - fact_sales"
  comparison_type: "rowset"
  tolerance: 0.01
  limit: 12
  sql_query: |
    SELECT
      d.Year,
      d.Month,
      SUM(SalesAmount) as total_metric,
      COUNT(*) as record_count
    FROM dbo.fact_sales f
    INNER JOIN dbo.dim_date d ON f.DateKey = d.DateKey
    GROUP BY d.Year, d.Month
    ORDER BY d.Year, d.Month
  snow_query: |
    SELECT
      d.Year,
      d.Month,
      SUM(SalesAmount) as total_metric,
      COUNT(*) as record_count
    FROM SAMPLEDW.FACT.FACT_SALES f
    INNER JOIN SAMPLEDW.DIM.DIM_DATE d ON f.DateKey = d.DateKey
    GROUP BY d.Year, d.Month
    ORDER BY d.Year, d.Month
```

### 5. Top N Validation (MEDIUM Priority)
```yaml
- name: "Top 5 Customer"
  comparison_type: "rowset"
  tolerance: 0.01
  limit: 5
  sql_query: |
    SELECT TOP 5
      c.CustomerName,
      SUM(SalesAmount) as total_metric,
      COUNT(*) as record_count
    FROM dbo.fact_sales f
    INNER JOIN dbo.dim_customer c ON f.CustomerKey = c.CustomerKey
    GROUP BY c.CustomerName
    ORDER BY total_metric DESC
  snow_query: |
    SELECT
      c.CustomerName,
      SUM(SalesAmount) as total_metric,
      COUNT(*) as record_count
    FROM SAMPLEDW.FACT.FACT_SALES f
    INNER JOIN SAMPLEDW.DIM.DIM_CUSTOMER c ON f.CustomerKey = c.CustomerKey
    GROUP BY c.CustomerName
    ORDER BY total_metric DESC
    LIMIT 5
```

### 6. Complex Multi-Dimension Joins (LOW Priority)
```yaml
- name: "fact_sales by Customer and Product"
  comparison_type: "rowset"
  tolerance: 0.01
  limit: 50
  sql_query: |
    SELECT
      c.CustomerName,
      p.ProductName,
      SUM(SalesAmount) as total_metric,
      COUNT(*) as record_count
    FROM dbo.fact_sales f
    INNER JOIN dbo.dim_customer c ON f.CustomerKey = c.CustomerKey
    INNER JOIN dbo.dim_product p ON f.ProductKey = p.ProductKey
    GROUP BY c.CustomerName, p.ProductName
    ORDER BY total_metric DESC
  snow_query: |
    SELECT
      c.CustomerName,
      p.ProductName,
      SUM(SalesAmount) as total_metric,
      COUNT(*) as record_count
    FROM SAMPLEDW.FACT.FACT_SALES f
    INNER JOIN SAMPLEDW.DIM.DIM_CUSTOMER c ON f.CustomerKey = c.CustomerKey
    INNER JOIN SAMPLEDW.DIM.DIM_PRODUCT p ON f.ProductKey = p.ProductKey
    GROUP BY c.CustomerName, p.ProductName
    ORDER BY total_metric DESC
```

## Customizing Suggestions

After auto-generating suggestions, you can customize them:

1. **Edit the YAML file**:
```bash
nano /Users/aravind/sourcecode/projects/data-migration-validator/ombudsman_core/src/ombudsman/config/custom_queries.yaml
```

2. **Modify parameters**:
- Change `tolerance` for different precision levels
- Adjust `limit` for more/fewer rows
- Modify SQL to add WHERE clauses
- Add custom calculations

3. **Add your own queries**:
```yaml
- name: "My Custom Validation"
  comparison_type: "aggregation"
  tolerance: 0.001
  sql_query: |
    SELECT
      SUM(Amount) as total,
      COUNT(DISTINCT CustomerID) as unique_customers
    FROM dbo.fact_sales
    WHERE Year = 2023
  snow_query: |
    SELECT
      SUM(Amount) as total,
      COUNT(DISTINCT CustomerID) as unique_customers
    FROM SAMPLEDW.FACT.FACT_SALES
    WHERE Year = 2023
```

## Integration into Pipeline Creation

The intelligent suggestion system is designed to be used during pipeline creation:

**Workflow:**
1. User extracts metadata → Discovers schema
2. User generates mappings → Understands table relationships
3. System auto-suggests queries → Based on actual schema
4. User reviews/customizes → Adds business-specific logic
5. System validates → Compares SQL Server vs Snowflake
6. Pipeline executes → Automated validation

## API Endpoints Summary

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/metadata/extract` | POST | Extract database metadata |
| `/mapping/suggest` | POST | Generate table/column mappings |
| `/custom-queries/intelligent-suggest` | POST | Generate intelligent query suggestions |
| `/custom-queries/save-suggestions` | POST | Auto-save suggestions to YAML |
| `/custom-queries/user-queries` | GET | View saved queries |
| `/custom-queries/validate-user-queries` | POST | Validate all saved queries |
| `/custom-queries/examples` | GET | Browse 12 example templates |
| `/custom-queries/config-location` | GET | Get file paths |

## Benefits

**Before (Manual):**
- Write 20+ complex SQL queries by hand
- Figure out table relationships manually
- Test each query individually
- Maintain separate SQL Server and Snowflake versions

**After (Intelligent):**
- Click one button to generate all queries
- System discovers relationships automatically
- All queries tested together
- Both versions generated automatically

## Example: Complete End-to-End

```bash
# 1. Extract metadata
curl -X POST http://localhost:8000/metadata/extract \
  -H "Content-Type: application/json" \
  -d '{"sql_database": "SampleDW", "sql_schemas": ["DIM", "FACT"], "snowflake_database": "SAMPLEDW", "snowflake_schemas": ["DIM", "FACT"]}'

# 2. Generate mappings
curl -X POST http://localhost:8000/mapping/suggest

# 3. Auto-save intelligent suggestions
curl -X POST http://localhost:8000/custom-queries/save-suggestions

# 4. Validate all queries
curl -X POST http://localhost:8000/custom-queries/validate-user-queries | python3 -m json.tool

# Done! You now have 15+ validated business queries ready to use
```

## Troubleshooting

**No suggestions generated?**
- Ensure metadata was extracted: Check `/metadata/extract` ran successfully
- Ensure mapping exists: Check `/mapping/suggest` ran successfully
- Check table naming: System looks for "fact" and "dim" prefixes

**Suggestions don't include joins?**
- Create a `relationships.yaml` file defining your foreign keys
- System will then generate join queries automatically

**Want different SQL?**
- Manually edit `custom_queries.yaml` after auto-generation
- You have full control to customize any generated query

## Files Created/Modified

1. **Metadata**: `ombudsman_core/data/metadata.json` (auto-generated)
2. **Mapping**: `ombudsman_core/data/mapping.json` (auto-generated)
3. **Relationships**: `ombudsman_core/src/ombudsman/config/relationships.yaml` (manual)
4. **Queries**: `ombudsman_core/src/ombudsman/config/custom_queries.yaml` (auto-generated, customizable)

## Next Steps

1. Extract your metadata
2. Generate mappings
3. Define relationships (optional)
4. Auto-generate suggestions
5. Review and customize
6. Validate!

The intelligent suggestion system eliminates the manual work of writing complex SQL queries, making data migration validation faster, more comprehensive, and less error-prone.
