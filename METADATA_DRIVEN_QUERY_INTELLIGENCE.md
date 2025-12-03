# Metadata-Driven Intelligent Query Generation

## Overview

The system now generates intelligent validation queries by analyzing **actual table metadata and relationships**, not just query workload patterns. It thinks like a data analyst to suggest meaningful multi-dimensional queries based on star schema intelligence.

## Key Improvement

**Before:** Suggestions were based only on Query Store workload patterns
- Limited to queries that were actually executed
- Missed important validation scenarios
- Required representative workload

**After:** Suggestions are based on database metadata and star schema analysis
- Works even without Query Store data
- Generates comprehensive validations automatically
- Understands data warehouse structure

## How It Works

### 1. Metadata Analysis

The system loads from `/core/src/ombudsman/config/tables.yaml`:

```yaml
snow:
  FACT.FACT_SALES:
    SALES_KEY: NUMBER
    DIM_CUSTOMER_KEY: NUMBER      # Foreign key
    DIM_PRODUCT_KEY: NUMBER        # Foreign key
    DIM_DATE_KEY: NUMBER           # Foreign key
    DIM_STORE_KEY: NUMBER          # Foreign key
    SALES_AMOUNT: NUMBER           # Measure
    QUANTITY: NUMBER               # Measure
    DISCOUNT_AMOUNT: NUMBER        # Measure

  DIM.DIM_PRODUCT:
    PRODUCT_KEY: NUMBER            # Primary key
    PRODUCT_NAME: VARCHAR
    CATEGORY: VARCHAR              # Categorical
    SUBCATEGORY: VARCHAR           # Categorical
    UNIT_PRICE: NUMBER
```

### 2. Intelligent Column Classification

**Identifiers (Foreign/Primary Keys):**
- Patterns: `*_key`, `*_id`, `*_pk`, `*_sk`
- Examples: `DIM_CUSTOMER_KEY`, `PRODUCT_KEY`
- **Not aggregated** - used for JOINs only

**Measures (Business Metrics):**
- Numeric columns with keywords: `amount`, `quantity`, `price`, `cost`, `total`
- Examples: `SALES_AMOUNT`, `QUANTITY`, `DISCOUNT_AMOUNT`
- **Should be aggregated** - SUM, AVG, COUNT

**Categorical Attributes (Grouping Dimensions):**
- String columns with keywords: `category`, `region`, `segment`, `type`, `status`
- Examples: `CATEGORY`, `REGION`, `SEGMENT`
- **Used in GROUP BY** clauses

### 3. Foreign Key Inference

Automatically detects relationships from naming patterns:

```
fact_sales.dim_customer_key → dim_customer.customer_key
fact_sales.dim_product_key  → dim_product.product_key
fact_sales.dim_date_key     → dim_date.date_key
fact_sales.dim_store_key    → dim_store.store_key
```

### 4. Query Pattern Generation

## Generated Query Patterns

### Pattern 1: Single Dimension Aggregation

**Example: Total Sales by Product Category**

```sql
-- SQL Server
SELECT
    d.CATEGORY,
    SUM(f.SALES_AMOUNT) as total_sales_amount,
    COUNT(*) as record_count
FROM fact.fact_sales f
INNER JOIN dim.dim_product d
    ON f.dim_product_key = d.product_key
GROUP BY d.CATEGORY
ORDER BY total_sales_amount DESC

-- Snowflake (auto-generated)
SELECT
    d.CATEGORY,
    SUM(f.SALES_AMOUNT) as TOTAL_SALES_AMOUNT,
    COUNT(*) as RECORD_COUNT
FROM FACT.FACT_SALES f
INNER JOIN DIM.DIM_PRODUCT d
    ON f.DIM_PRODUCT_KEY = d.PRODUCT_KEY
GROUP BY d.CATEGORY
ORDER BY TOTAL_SALES_AMOUNT DESC
```

**Why This Query?**
- Analyst Question: "What are my sales by product category?"
- Validates aggregation logic across systems
- Tests JOIN integrity
- Compares business metrics

### Pattern 2: Multi-Dimensional Aggregation

**Example: Total Sales by Product Category AND Customer Region**

```sql
-- SQL Server
SELECT
    d1.CATEGORY,
    d2.REGION,
    SUM(f.SALES_AMOUNT) as total_sales_amount,
    COUNT(*) as record_count
FROM fact.fact_sales f
INNER JOIN dim.dim_product d1
    ON f.dim_product_key = d1.product_key
INNER JOIN dim.dim_customer d2
    ON f.dim_customer_key = d2.customer_key
GROUP BY d1.CATEGORY, d2.REGION
ORDER BY total_sales_amount DESC
```

**Why This Query?**
- Analyst Question: "Which product categories sell best in each region?"
- Tests complex JOIN logic
- Validates multi-dimensional aggregations
- Reflects real analytical queries

### Pattern 3: Fact-Dimension Conformance

**Example: Check for Orphaned Product Keys**

```sql
-- SQL Server
SELECT COUNT(*) as orphaned_count
FROM fact.fact_sales f
LEFT JOIN dim.dim_product d
    ON f.dim_product_key = d.product_key
WHERE d.product_key IS NULL

-- Snowflake
SELECT COUNT(*) as ORPHANED_COUNT
FROM FACT.FACT_SALES f
LEFT JOIN DIM.DIM_PRODUCT d
    ON f.DIM_PRODUCT_KEY = d.PRODUCT_KEY
WHERE d.PRODUCT_KEY IS NULL
```

**Why This Query?**
- Data Quality: "Do all sales reference valid products?"
- Validates referential integrity
- Identifies data migration issues
- **Critical for data warehouse consistency**

## API Usage

### Endpoint

```
POST /custom-queries/intelligent-suggest
Content-Type: application/json
{}
```

### Response Structure

```json
{
  "status": "success",
  "total_suggestions": 10,
  "suggestions_by_category": {
    "Single Dimension Analysis": [
      {
        "name": "Total SALES_AMOUNT by CATEGORY",
        "description": "Aggregate SALES_AMOUNT from FACT_SALES grouped by DIM_PRODUCT.CATEGORY",
        "sql_server_query": "...",
        "snowflake_query": "...",
        "complexity": "simple",
        "analytical_value": "high",
        "fact_table": "FACT.FACT_SALES",
        "dimension_tables": ["DIM.DIM_PRODUCT"],
        "measures": ["SALES_AMOUNT"],
        "group_by": ["CATEGORY"]
      }
    ],
    "Multi-Dimensional Analysis": [
      {
        "name": "Total SALES_AMOUNT by CATEGORY and REGION",
        "description": "Multi-dimensional analysis of SALES_AMOUNT across 2 dimensions",
        "sql_server_query": "...",
        "snowflake_query": "...",
        "complexity": "medium",
        "analytical_value": "very_high",
        "fact_table": "FACT.FACT_SALES",
        "dimension_tables": ["DIM.DIM_PRODUCT", "DIM.DIM_CUSTOMER"],
        "measures": ["SALES_AMOUNT"],
        "group_by": ["CATEGORY", "REGION"]
      }
    ],
    "Referential Integrity Checks": [
      {
        "name": "Conformance: FACT_SALES → DIM_PRODUCT",
        "description": "Check referential integrity: DIM_PRODUCT_KEY must exist in DIM_PRODUCT.PRODUCT_KEY",
        "sql_server_query": "...",
        "snowflake_query": "...",
        "complexity": "simple",
        "analytical_value": "critical"
      }
    ]
  },
  "intelligence_applied": [
    "✓ Detected fact and dimension tables",
    "✓ Inferred foreign key relationships",
    "✓ Identified measures vs identifiers",
    "✓ Generated multi-dimensional JOINs",
    "✓ Created conformance checks",
    "✓ Suggested analytical aggregations"
  ]
}
```

## Real-World Example: Retail Data Warehouse

### Schema

**Fact Table: FACT_SALES**
- SALES_KEY (PK)
- DIM_CUSTOMER_KEY (FK)
- DIM_PRODUCT_KEY (FK)
- DIM_STORE_KEY (FK)
- DIM_DATE_KEY (FK)
- SALES_AMOUNT (Measure)
- QUANTITY (Measure)
- DISCOUNT_AMOUNT (Measure)

**Dimension Tables:**
- DIM_CUSTOMER (CUSTOMER_KEY, NAME, REGION, SEGMENT)
- DIM_PRODUCT (PRODUCT_KEY, NAME, CATEGORY, SUBCATEGORY)
- DIM_STORE (STORE_KEY, NAME, CITY, STATE)
- DIM_DATE (DATE_KEY, DATE, MONTH, YEAR, QUARTER)

### Generated Validations

**1. Sales by Product Category (3 queries)**
- Total SALES_AMOUNT by CATEGORY
- Total QUANTITY by CATEGORY
- Total DISCOUNT_AMOUNT by CATEGORY

**2. Sales by Customer Segment (3 queries)**
- Total SALES_AMOUNT by SEGMENT
- Total QUANTITY by SEGMENT
- Total DISCOUNT_AMOUNT by SEGMENT

**3. Multi-Dimensional Analysis (6 queries)**
- Sales by CATEGORY and REGION
- Sales by CATEGORY and SEGMENT
- Sales by SEGMENT and CITY
- etc.

**4. Conformance Checks (4 queries)**
- Check CUSTOMER_KEY integrity
- Check PRODUCT_KEY integrity
- Check STORE_KEY integrity
- Check DATE_KEY integrity

**Total: ~16 intelligent queries automatically generated!**

## User Workflow

### 1. Extract Metadata
Navigate to **Database Mapping** page and extract metadata:
- Connects to SQL Server and Snowflake
- Extracts all table and column information
- Saves to `tables.yaml`

### 2. Generate Intelligent Queries
In **Pipeline Builder**, click **"Suggest Custom Queries with Joins"**:
- System analyzes metadata
- Infers relationships automatically
- Generates queries grouped by pattern
- Shows SQL for both systems side-by-side

### 3. Review and Select
Review the suggestions:
- **Single Dimension**: Simple analytical queries
- **Multi-Dimensional**: Complex analytical queries
- **Conformance**: Data quality checks

### 4. Execute Validations
Copy queries to pipeline and execute:
- System runs queries on both databases
- Compares results
- Reports differences
- Shows side-by-side comparison

## Technical Implementation

### Files Created/Modified

**1. `pipelines/intelligent_query_generator.py` (NEW)**
- 500+ lines of intelligent query generation logic
- Column classification algorithms
- Foreign key inference
- Query pattern templates

**2. `queries/custom.py` (MODIFIED)**
- Updated `/intelligent-suggest` endpoint
- Integrated new generator
- Enhanced response formatting

### Key Classes and Methods

```python
class IntelligentQueryGenerator:
    def __init__(self, metadata_path="/core/src/ombudsman/config")

    def generate_intelligent_queries(database="snow") -> List[Dict]

    def _is_identifier_column(col_name, table_name) -> bool

    def _is_measure_column(col_name, col_type) -> bool

    def _is_categorical(col_name, col_type) -> bool

    def _infer_foreign_keys(fact_table, fact_columns) -> List[Tuple]

    def _build_single_dim_query(...) -> Dict

    def _build_multi_dim_query(...) -> Dict

    def _build_conformance_check(...) -> Dict
```

## Benefits

### 1. No Workload Required
- Works immediately after metadata extraction
- Don't need representative Query Store data
- Covers scenarios not in workload

### 2. Data Warehouse Intelligence
- Understands star schema patterns
- Recognizes fact vs dimension tables
- Infers relationships automatically

### 3. Analyst-Like Thinking
- Generates queries analysts would write
- Focuses on business metrics
- Tests real analytical scenarios

### 4. Comprehensive Coverage
- Single and multi-dimensional aggregations
- Referential integrity checks
- All major foreign key relationships

### 5. Ready to Use
- Both SQL Server and Snowflake versions generated
- Proper JOINs and GROUP BY clauses
- Correct casing for each system

## Comparison with Workload-Based Suggestions

| Feature | Workload-Based | Metadata-Based |
|---------|---------------|----------------|
| **Requires Query Store** | ✅ Yes | ❌ No |
| **Coverage** | Only executed queries | All possible patterns |
| **Conformance Checks** | Only if JOINs in workload | All FK relationships |
| **Multi-Dimensional** | Limited | Comprehensive |
| **Setup Time** | Weeks (collect workload) | Minutes (extract metadata) |
| **Intelligence** | Pattern matching | Semantic understanding |

## Future Enhancements

1. **Time-Based Analysis**: Detect date dimensions and generate time-series queries
2. **Top N Queries**: Generate "Top 10 Products" style queries
3. **User Customization**: Allow users to define custom patterns
4. **ML-Based Optimization**: Learn which queries are most valuable
5. **Cross-Fact Analysis**: Generate queries joining multiple fact tables

## Summary

The Metadata-Driven Intelligent Query Generation feature:
- 🧠 **Analyzes actual database structure**
- 🔍 **Infers relationships automatically**
- 📊 **Generates analytical queries** like a data analyst would write
- ✅ **Validates referential integrity** across all foreign keys
- 🎯 **Requires no Query Store** - works with metadata alone
- 🚀 **Generates comprehensive validations** in seconds

This makes the system truly intelligent about data warehouses and capable of suggesting meaningful validations without any workload data!
