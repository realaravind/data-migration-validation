# Intelligent Pipeline Generation & Natural Language Support

## Overview

The Ombudsman Validation Studio now includes **intelligent pipeline generation** that analyzes fact tables and automatically suggests appropriate validations. It also supports **natural language** pipeline creation.

---

## 1. Auto-Generate Fact-Specific Validations

### Example: SalesFact Table

**Table Structure:**
```sql
CREATE TABLE SalesFact (
    SaleID INT PRIMARY KEY,
    OrderDate DATE,
    ProductID INT,          -- FK to DimProduct
    CustomerID INT,         -- FK to DimCustomer
    StoreID INT,            -- FK to DimStore
    Quantity INT,
    UnitPrice DECIMAL(10,2),
    TotalAmount DECIMAL(10,2),
    DiscountAmount DECIMAL(10,2),
    TaxAmount DECIMAL(10,2),
    NetAmount DECIMAL(10,2)
)
```

### API Call

**Endpoint:** `POST /pipelines/suggest-for-fact`

**Request:**
```json
{
  "fact_table": "SalesFact",
  "fact_schema": "fact",
  "database_type": "sql",
  "columns": [
    {"name": "SaleID", "type": "INT"},
    {"name": "OrderDate", "type": "DATE"},
    {"name": "ProductID", "type": "INT"},
    {"name": "CustomerID", "type": "INT"},
    {"name": "StoreID", "type": "INT"},
    {"name": "Quantity", "type": "INT"},
    {"name": "UnitPrice", "type": "DECIMAL"},
    {"name": "TotalAmount", "type": "DECIMAL"},
    {"name": "DiscountAmount", "type": "DECIMAL"},
    {"name": "TaxAmount", "type": "DECIMAL"},
    {"name": "NetAmount", "type": "DECIMAL"}
  ],
  "relationships": [
    {"fact_table": "SalesFact", "fk_column": "ProductID", "dim_table": "DimProduct"},
    {"fact_table": "SalesFact", "fk_column": "CustomerID", "dim_table": "DimCustomer"},
    {"fact_table": "SalesFact", "fk_column": "StoreID", "dim_table": "DimStore"}
  ]
}
```

### Response - Intelligent Suggestions

```json
{
  "status": "success",
  "fact_table": "SalesFact",
  "analysis": {
    "total_columns": 11,
    "numeric_columns": 6,
    "date_columns": 1,
    "fk_columns": 3,
    "relationships": 3
  },
  "suggested_checks": [
    {
      "category": "Schema Validation",
      "pipeline_type": "schema",
      "checks": [
        "validate_schema_columns",
        "validate_schema_datatypes",
        "validate_schema_nullability"
      ],
      "reason": "Ensures table structure matches between SQL Server and Snowflake",
      "priority": "CRITICAL"
    },
    {
      "category": "Data Quality",
      "pipeline_type": "dq",
      "checks": [
        "validate_record_counts",
        "validate_nulls"
      ],
      "reason": "Validates row counts match and NULL patterns are consistent",
      "priority": "CRITICAL"
    },
    {
      "category": "Business Metrics",
      "pipeline_type": "business",
      "checks": [
        "validate_metric_sums",
        "validate_metric_averages",
        "validate_ratios"
      ],
      "applicable_columns": {
        "sum_columns": ["Quantity", "TotalAmount", "DiscountAmount", "TaxAmount", "NetAmount"],
        "avg_columns": ["Quantity", "UnitPrice", "TotalAmount", "DiscountAmount", "TaxAmount", "NetAmount"],
        "ratio_columns": []
      },
      "reason": "Validates business calculations for 6 numeric columns",
      "priority": "HIGH",
      "examples": [
        "SUM(TotalAmount) matches between systems",
        "SUM(Quantity) matches between systems",
        "SUM(TaxAmount) matches between systems"
      ]
    },
    {
      "category": "Statistical Analysis",
      "pipeline_type": "dq",
      "checks": [
        "validate_statistics",
        "validate_distribution",
        "validate_outliers"
      ],
      "applicable_columns": ["Quantity", "UnitPrice", "TotalAmount", "DiscountAmount", "TaxAmount", "NetAmount"],
      "reason": "Ensures statistical properties match (mean, stddev, distribution)",
      "priority": "MEDIUM"
    },
    {
      "category": "Referential Integrity",
      "pipeline_type": "ri",
      "checks": [
        "validate_foreign_keys",
        "validate_cross_system_fk_alignment"
      ],
      "applicable_columns": ["ProductID", "CustomerID", "StoreID"],
      "related_dimensions": ["DimProduct", "DimCustomer", "DimStore"],
      "reason": "Validates FK integrity to 3 dimension tables",
      "priority": "HIGH"
    },
    {
      "category": "Fact-Dimension Conformance",
      "pipeline_type": "business",
      "checks": [
        "validate_fact_dim_conformance",
        "validate_late_arriving_facts"
      ],
      "related_dimensions": ["DimProduct", "DimCustomer", "DimStore"],
      "reason": "Ensures all fact records have valid dimension references",
      "priority": "HIGH"
    },
    {
      "category": "Time-Series Analysis",
      "pipeline_type": "timeseries",
      "checks": [
        "validate_ts_continuity",
        "validate_ts_duplicates",
        "validate_period_over_period"
      ],
      "applicable_columns": ["OrderDate"],
      "primary_date_column": "OrderDate",
      "reason": "Validates temporal continuity and detects duplicates using OrderDate",
      "priority": "MEDIUM"
    }
  ],
  "pipeline_yaml": "<Full YAML pipeline with all steps>",
  "total_validations": 21
}
```

### What the System Detects

#### For SalesFact, the system automatically identifies:

1. **Sum Validations** (Critical Business Metrics):
   - `SUM(TotalAmount)` - Total revenue must match
   - `SUM(Quantity)` - Total items sold must match
   - `SUM(TaxAmount)` - Total tax collected must match
   - `SUM(NetAmount)` - Net revenue must match
   - `SUM(DiscountAmount)` - Total discounts must match

2. **Average Validations**:
   - `AVG(UnitPrice)` - Average selling price
   - `AVG(TotalAmount)` - Average transaction size
   - `AVG(Quantity)` - Average items per sale

3. **Ratio Validations**:
   - Discount/Sales ratio
   - Tax/Sales ratio
   - Net/Gross ratio

4. **Foreign Key Validations**:
   - ProductID → DimProduct
   - CustomerID → DimCustomer
   - StoreID → DimStore
   - Detects orphaned sales records

5. **Time-Series Validations**:
   - No missing dates in OrderDate
   - No duplicate sales on same date+customer
   - Period-over-period comparisons

6. **Statistical Validations**:
   - Distribution of sales amounts matches
   - Outlier detection (e.g., $999,999 sale)
   - Standard deviation matches

---

## 2. Natural Language Pipeline Creation

### Endpoint: `POST /pipelines/create-from-nl`

### Examples

#### Example 1: Basic Sum Validation
**Input:**
```json
{
  "description": "Validate that total sales amount matches between SQL and Snowflake",
  "context": {
    "table": "SalesFact",
    "sql_schema": "fact",
    "snow_schema": "FACT"
  }
}
```

**Output:**
```json
{
  "status": "success",
  "description": "Validate that total sales amount matches between SQL and Snowflake",
  "detected_intent": {
    "checks": [
      {
        "type": "business",
        "check": "validate_metric_sums",
        "reason": "User requested sum/total validation"
      }
    ],
    "count": 1
  },
  "pipeline_yaml": "<Generated YAML>",
  "next_steps": "Review and execute this pipeline"
}
```

#### Example 2: Orphaned Records
**Input:**
```json
{
  "description": "Check for orphaned product IDs in the sales fact table"
}
```

**Detected Intent:**
- `validate_foreign_keys`
- `validate_fact_dim_conformance`

#### Example 3: Date Gaps
**Input:**
```json
{
  "description": "Ensure no gaps in daily sales data for 2024"
}
```

**Detected Intent:**
- `validate_ts_continuity`

#### Example 4: Complex Multi-Check
**Input:**
```json
{
  "description": "Validate sales fact: check row counts, total amounts, and ensure all product IDs are valid"
}
```

**Detected Intent:**
- `validate_record_counts` (row counts)
- `validate_metric_sums` (total amounts)
- `validate_foreign_keys` (product IDs valid)

---

## 3. UI Design Concept

### Page: "Pipeline Builder" (`/pipeline-builder`)

#### Layout:

```
┌─────────────────────────────────────────────────────────────────┐
│  Pipeline Builder                                    [Save] [Run]│
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  [Tab: Quick Build] [Tab: Natural Language] [Tab: Advanced]      │
│                                                                   │
│  ┌────────────── Quick Build ────────────────────┐              │
│  │                                                 │              │
│  │  Select Fact Table: [SalesFact        ▼]       │              │
│  │                                                 │              │
│  │  [Analyze Table]  ← Click to auto-suggest      │              │
│  │                                                 │              │
│  │  Suggested Validations:                        │              │
│  │                                                 │              │
│  │  ☑ Schema Validation (CRITICAL)                │              │
│  │     ✓ validate_schema_columns                  │              │
│  │     ✓ validate_schema_datatypes                │              │
│  │                                                 │              │
│  │  ☑ Business Metrics (HIGH)                     │              │
│  │     ✓ validate_metric_sums                     │              │
│  │       Columns: TotalAmount, Quantity, TaxA...  │              │
│  │     ✓ validate_metric_averages                 │              │
│  │                                                 │              │
│  │  ☑ Referential Integrity (HIGH)                │              │
│  │     ✓ validate_foreign_keys                    │              │
│  │       Dimensions: DimProduct, DimCustomer...   │              │
│  │                                                 │              │
│  │  ☐ Time-Series Analysis (MEDIUM)               │              │
│  │     ○ validate_ts_continuity                   │              │
│  │     ○ validate_ts_duplicates                   │              │
│  │                                                 │              │
│  │  Total Validations: 21                         │              │
│  │                                                 │              │
│  └─────────────────────────────────────────────────┘              │
│                                                                   │
│  ┌────────────── Natural Language ───────────────┐              │
│  │                                                 │              │
│  │  Describe what you want to validate:           │              │
│  │  ┌───────────────────────────────────────────┐ │              │
│  │  │ Validate that total sales amount matches  │ │              │
│  │  │ between SQL and Snowflake, and check for  │ │              │
│  │  │ orphaned product IDs                       │ │              │
│  │  └───────────────────────────────────────────┘ │              │
│  │                                                 │              │
│  │  [Generate Pipeline]                           │              │
│  │                                                 │              │
│  │  Detected Checks:                              │              │
│  │  • validate_metric_sums (total amounts)        │              │
│  │  • validate_foreign_keys (orphaned IDs)        │              │
│  │                                                 │              │
│  └─────────────────────────────────────────────────┘              │
│                                                                   │
│  ┌────────────── Pipeline Preview ───────────────┐              │
│  │                                                 │              │
│  │  pipeline:                                      │              │
│  │    name: SalesFact Complete Validation         │              │
│  │    steps:                                       │              │
│  │      - name: validate_schema                    │              │
│  │        type: schema                             │              │
│  │        checks:                                  │              │
│  │          - validate_schema_columns              │              │
│  │          - validate_schema_datatypes            │              │
│  │      ...                                        │              │
│  │                                                 │              │
│  └─────────────────────────────────────────────────┘              │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. User-Defined Pipelines

### Saving Custom Pipelines

**Endpoint:** `POST /projects/{project_id}/pipelines/save`

**Request:**
```json
{
  "pipeline_name": "My Custom SalesFact Validation",
  "pipeline_yaml": "<YAML content>",
  "description": "Custom validation for monthly sales reconciliation",
  "category": "user_defined"
}
```

### Loading User Pipelines

**Endpoint:** `GET /projects/{project_id}/pipelines/list`

**Response:**
```json
{
  "pipelines": [
    {
      "id": "custom_1",
      "name": "My Custom SalesFact Validation",
      "type": "user_defined",
      "created_at": "2024-11-29T10:00:00",
      "last_run": "2024-11-29T14:30:00"
    },
    {
      "id": "custom_2",
      "name": "Weekly Revenue Check",
      "type": "user_defined",
      "created_at": "2024-11-25T09:00:00"
    }
  ]
}
```

---

## 5. Complete Workflow

### Option 1: Auto-Suggest (Recommended for Fact Tables)

1. User selects fact table: **SalesFact**
2. System analyzes structure: columns, types, relationships
3. System suggests 21 validations across 7 categories
4. User reviews and customizes (check/uncheck)
5. User saves pipeline to project
6. User executes pipeline
7. Results displayed with pass/fail status

### Option 2: Natural Language

1. User types: *"Validate total sales and tax amounts match, check for orphaned customers"*
2. System parses intent
3. System generates pipeline with:
   - `validate_metric_sums` (TotalAmount, TaxAmount)
   - `validate_foreign_keys` (CustomerID)
4. User reviews YAML
5. User executes

### Option 3: Manual/Advanced

1. User selects default pipeline: **Business Rules**
2. User customizes YAML directly
3. User adds custom SQL checks
4. User saves and executes

---

## 6. Real-World SalesFact Validations (Expert Recommendations)

As a Data Warehouse Engineer, here are the **critical validations** I would run on SalesFact:

### Critical (Must Pass)
1. ✅ **Row Count Match** - `validate_record_counts`
2. ✅ **Total Revenue Match** - `SUM(TotalAmount)` must be identical
3. ✅ **Total Tax Match** - `SUM(TaxAmount)` for compliance
4. ✅ **FK Integrity** - All ProductID, CustomerID, StoreID exist in dimensions
5. ✅ **No Orphaned Facts** - Every sale has valid customer and product

### High Priority
6. ✅ **Date Continuity** - No missing days in OrderDate
7. ✅ **Quantity Sum** - `SUM(Quantity)` matches
8. ✅ **Schema Match** - All columns and types identical
9. ✅ **Null Patterns** - NULL counts per column match

### Medium Priority
10. ✅ **Average Transaction Size** - `AVG(TotalAmount)` similar
11. ✅ **Statistical Distribution** - Sales amounts follow same distribution
12. ✅ **Discount Ratio** - Discount/Sales ratio consistent
13. ✅ **Late Arriving Facts** - Sales dated before customer creation

### Nice to Have
14. ⚪ **Outlier Detection** - Flag unusual sales amounts
15. ⚪ **Period-over-Period** - Monthly revenue trends match
16. ⚪ **Uniqueness** - No duplicate SaleID

---

## 7. API Summary

| Endpoint | Purpose |
|----------|---------|
| `POST /pipelines/suggest-for-fact` | Auto-generate fact-specific validations |
| `POST /pipelines/create-from-nl` | Create pipeline from natural language |
| `GET /pipelines/defaults` | List 7 default pipelines |
| `GET /pipelines/defaults/{id}` | Get specific default pipeline |
| `POST /pipelines/execute` | Execute a pipeline |
| `GET /pipelines/status/{run_id}` | Check execution status |

---

## Next Steps

1. **Build UI** - Create PipelineBuilder.tsx page
2. **Integrate APIs** - Wire up suggest-for-fact and create-from-nl
3. **Test with Real Data** - Run against actual SalesFact table
4. **User Testing** - Validate NL understanding accuracy
5. **Expand NL Dictionary** - Add more intent patterns
