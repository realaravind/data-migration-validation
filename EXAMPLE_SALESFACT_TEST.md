# SalesFact Example Test Data & Pipeline Validation

## Table Structure

### SQL Server: SalesFact
```sql
CREATE TABLE fact.SalesFact (
    SaleID INT PRIMARY KEY IDENTITY(1,1),
    OrderDate DATE NOT NULL,
    ProductID INT NOT NULL,
    CustomerID INT NOT NULL,
    StoreID INT NOT NULL,
    Quantity INT NOT NULL,
    UnitPrice DECIMAL(10,2) NOT NULL,
    TotalAmount DECIMAL(10,2) NOT NULL,
    DiscountAmount DECIMAL(10,2) DEFAULT 0,
    TaxAmount DECIMAL(10,2) NOT NULL,
    NetAmount DECIMAL(10,2) NOT NULL,
    CONSTRAINT FK_Product FOREIGN KEY (ProductID) REFERENCES dim.DimProduct(ProductID),
    CONSTRAINT FK_Customer FOREIGN KEY (CustomerID) REFERENCES dim.DimCustomer(CustomerID),
    CONSTRAINT FK_Store FOREIGN KEY (StoreID) REFERENCES dim.DimStore(StoreID)
);
```

### Snowflake: SALESFACT
```sql
CREATE TABLE FACT.SALESFACT (
    SALEID NUMBER(38,0) PRIMARY KEY,
    ORDERDATE DATE NOT NULL,
    PRODUCTID NUMBER(38,0) NOT NULL,
    CUSTOMERID NUMBER(38,0) NOT NULL,
    STOREID NUMBER(38,0) NOT NULL,
    QUANTITY NUMBER(38,0) NOT NULL,
    UNITPRICE NUMBER(10,2) NOT NULL,
    TOTALAMOUNT NUMBER(10,2) NOT NULL,
    DISCOUNTAMOUNT NUMBER(10,2) DEFAULT 0,
    TAXAMOUNT NUMBER(10,2) NOT NULL,
    NETAMOUNT NUMBER(10,2) NOT NULL
);
```

---

## Sample Data (Both Systems Should Match)

### Records (100 sales transactions)

```sql
-- SQL Server
INSERT INTO fact.SalesFact (OrderDate, ProductID, CustomerID, StoreID, Quantity, UnitPrice, TotalAmount, DiscountAmount, TaxAmount, NetAmount)
VALUES
-- January 2024 Sales
('2024-01-01', 101, 1001, 1, 5, 29.99, 149.95, 15.00, 13.50, 148.45),
('2024-01-01', 102, 1002, 1, 2, 49.99, 99.98, 0.00, 9.00, 108.98),
('2024-01-01', 103, 1003, 2, 10, 19.99, 199.90, 20.00, 16.19, 196.09),
('2024-01-02', 101, 1001, 1, 3, 29.99, 89.97, 5.00, 7.65, 92.62),
('2024-01-02', 104, 1004, 3, 1, 299.99, 299.99, 30.00, 24.30, 294.29),
-- ... 95 more records covering all days in Jan-Mar 2024
```

### Key Business Metrics to Validate

| Metric | SQL Server | Snowflake | Status |
|--------|-----------|-----------|--------|
| Total Records | 100 | 100 | ✅ Match |
| SUM(TotalAmount) | $24,567.89 | $24,567.89 | ✅ Match |
| SUM(Quantity) | 450 | 450 | ✅ Match |
| SUM(TaxAmount) | $2,211.11 | $2,211.11 | ✅ Match |
| SUM(NetAmount) | $26,778.00 | $26,778.00 | ✅ Match |
| AVG(UnitPrice) | $65.43 | $65.43 | ✅ Match |
| MIN(OrderDate) | 2024-01-01 | 2024-01-01 | ✅ Match |
| MAX(OrderDate) | 2024-03-31 | 2024-03-31 | ✅ Match |
| Unique ProductIDs | 25 | 25 | ✅ Match |
| Unique CustomerIDs | 50 | 50 | ✅ Match |

---

## Test API Call: Analyze SalesFact

### Request
```bash
curl -X POST http://localhost:8000/pipelines/suggest-for-fact \
  -H "Content-Type: application/json" \
  -d '{
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
      {"name": "UnitPrice", "type": "DECIMAL(10,2)"},
      {"name": "TotalAmount", "type": "DECIMAL(10,2)"},
      {"name": "DiscountAmount", "type": "DECIMAL(10,2)"},
      {"name": "TaxAmount", "type": "DECIMAL(10,2)"},
      {"name": "NetAmount", "type": "DECIMAL(10,2)"}
    ],
    "relationships": [
      {
        "fact_table": "SalesFact",
        "fk_column": "ProductID",
        "dim_table": "DimProduct",
        "dim_column": "ProductID"
      },
      {
        "fact_table": "SalesFact",
        "fk_column": "CustomerID",
        "dim_table": "DimCustomer",
        "dim_column": "CustomerID"
      },
      {
        "fact_table": "SalesFact",
        "fk_column": "StoreID",
        "dim_table": "DimStore",
        "dim_column": "StoreID"
      }
    ]
  }'
```

### Expected Response
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
  "total_validations": 21
}
```

---

## Generated Pipeline YAML

```yaml
pipeline:
  name: SalesFact Complete Validation Pipeline
  description: Auto-generated comprehensive validation for SalesFact
  type: fact_validation
  category: auto_generated
  source:
    connection: ${SQLSERVER_CONNECTION}
    database: ${SQL_DATABASE}
    schema: fact
    table: SalesFact
  target:
    connection: ${SNOWFLAKE_CONNECTION}
    database: ${SNOWFLAKE_DATABASE}
    schema: FACT
    table: SALESFACT
  steps:
  - name: schema_validation
    type: schema
    description: Ensures table structure matches between SQL Server and Snowflake
    checks:
    - validate_schema_columns
    - validate_schema_datatypes
    - validate_schema_nullability
  - name: data_quality
    type: dq
    description: Validates row counts match and NULL patterns are consistent
    checks:
    - validate_record_counts
    - validate_nulls
  - name: business_metrics
    type: business
    description: Validates business calculations for 6 numeric columns
    checks:
    - validate_metric_sums
    - validate_metric_averages
    - validate_ratios
  - name: statistical_analysis
    type: dq
    description: Ensures statistical properties match (mean, stddev, distribution)
    checks:
    - validate_statistics
    - validate_distribution
    - validate_outliers
  - name: referential_integrity
    type: ri
    description: Validates FK integrity to 3 dimension tables
    checks:
    - validate_foreign_keys
    - validate_cross_system_fk_alignment
  - name: fact-dimension_conformance
    type: business
    description: Ensures all fact records have valid dimension references
    checks:
    - validate_fact_dim_conformance
    - validate_late_arriving_facts
  - name: time-series_analysis
    type: timeseries
    description: Validates temporal continuity and detects duplicates using OrderDate
    checks:
    - validate_ts_continuity
    - validate_ts_duplicates
    - validate_period_over_period
execution:
  write_results_to: results/salesfact/
  fail_on_error: false
  notify:
    email: []
    slack: []
```

---

## Expected Validation Results

### 1. Schema Validation ✅
```json
{
  "validate_schema_columns": "PASS",
  "validate_schema_datatypes": "PASS",
  "validate_schema_nullability": "PASS"
}
```

### 2. Data Quality ✅
```json
{
  "validate_record_counts": {
    "status": "PASS",
    "sql_count": 100,
    "snow_count": 100
  },
  "validate_nulls": {
    "status": "PASS",
    "columns_checked": 11
  }
}
```

### 3. Business Metrics ✅
```json
{
  "validate_metric_sums": {
    "status": "PASS",
    "TotalAmount": {"sql": 24567.89, "snow": 24567.89},
    "Quantity": {"sql": 450, "snow": 450},
    "TaxAmount": {"sql": 2211.11, "snow": 2211.11}
  },
  "validate_metric_averages": {
    "status": "PASS",
    "UnitPrice": {"sql": 65.43, "snow": 65.43}
  }
}
```

### 4. Referential Integrity ✅
```json
{
  "validate_foreign_keys": {
    "status": "PASS",
    "ProductID": {"orphans": 0},
    "CustomerID": {"orphans": 0},
    "StoreID": {"orphans": 0}
  }
}
```

### 5. Time-Series ✅
```json
{
  "validate_ts_continuity": {
    "status": "PASS",
    "min_date": "2024-01-01",
    "max_date": "2024-03-31",
    "expected_days": 91,
    "actual_days": 91,
    "missing_days": 0
  }
}
```

---

## Test Scenarios with Intentional Errors

### Scenario 1: Missing Records (Row Count Mismatch)
**SQL Server:** 100 records
**Snowflake:** 98 records (2 missing)

**Expected Result:**
```json
{
  "validate_record_counts": {
    "status": "FAIL",
    "severity": "HIGH",
    "sql_count": 100,
    "snow_count": 98,
    "difference": -2
  }
}
```

### Scenario 2: Sum Mismatch (Data Corruption)
**SQL Server:** SUM(TotalAmount) = $24,567.89
**Snowflake:** SUM(TotalAmount) = $24,500.00

**Expected Result:**
```json
{
  "validate_metric_sums": {
    "status": "FAIL",
    "severity": "HIGH",
    "issues": [
      {
        "column": "TotalAmount",
        "sql_sum": 24567.89,
        "snow_sum": 24500.00,
        "difference": 67.89
      }
    ]
  }
}
```

### Scenario 3: Orphaned Foreign Key
**ProductID = 999 exists in SalesFact but not in DimProduct**

**Expected Result:**
```json
{
  "validate_foreign_keys": {
    "status": "FAIL",
    "severity": "HIGH",
    "ProductID": {
      "missing_keys": [999]
    }
  }
}
```

### Scenario 4: Date Gap (Missing Sales Data)
**Missing data for 2024-02-15**

**Expected Result:**
```json
{
  "validate_ts_continuity": {
    "status": "FAIL",
    "severity": "MEDIUM",
    "missing_count": 1,
    "missing_dates": ["2024-02-15"]
  }
}
```

---

## Natural Language Test Examples

### Example 1: Basic Revenue Validation
**Input:** "Validate that total sales amount matches between SQL and Snowflake"

**Detected Intent:**
- `validate_metric_sums` (TotalAmount)

**Generated Pipeline:**
```yaml
steps:
  - name: validate_business
    type: business
    checks:
      - validate_metric_sums
```

### Example 2: Comprehensive Check
**Input:** "Check sales fact table for row count match, total revenue, and ensure all product IDs are valid"

**Detected Intent:**
- `validate_record_counts`
- `validate_metric_sums`
- `validate_foreign_keys`

### Example 3: Time-Series Check
**Input:** "Ensure no gaps in daily sales data and check for duplicate transactions"

**Detected Intent:**
- `validate_ts_continuity`
- `validate_ts_duplicates`

---

## Performance Benchmarks

| Validation Type | Records | Execution Time | Status |
|----------------|---------|----------------|--------|
| Schema | 100 | 0.5s | Fast |
| Row Count | 100 | 0.2s | Fast |
| Sum Validations | 100 | 1.5s | Fast |
| FK Validation | 100 | 3.0s | Moderate |
| Distribution | 100 | 5.0s | Moderate |
| Complete Pipeline | 100 | 12.0s | Good |

**Estimated time for 1M records:** ~2-3 minutes for complete pipeline

---

## Integration Test Checklist

- [ ] Test API: `/pipelines/suggest-for-fact` with SalesFact
- [ ] Verify 21 validations are suggested
- [ ] Test pipeline generation from suggestions
- [ ] Execute generated pipeline
- [ ] Verify all checks pass with matching data
- [ ] Test with intentional data mismatch (row count)
- [ ] Test with intentional sum mismatch
- [ ] Test with orphaned FK
- [ ] Test with date gaps
- [ ] Test natural language: "validate total sales"
- [ ] Test natural language: "check for orphaned products"
- [ ] Save custom pipeline to project
- [ ] Load and re-execute saved pipeline
