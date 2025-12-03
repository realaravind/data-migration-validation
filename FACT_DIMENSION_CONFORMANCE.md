# Fact-Dimension Conformance Validation

## Overview

The system now automatically detects and generates **Fact-Dimension Conformance** validations from your Query Store workload. This ensures that foreign keys in fact tables have matching records in dimension tables, validating referential integrity in star schema data warehouses.

## What is Fact-Dimension Conformance?

In a star schema data warehouse:
- **Fact tables** contain business events with foreign keys to dimensions (e.g., `fact_sales`)
- **Dimension tables** contain descriptive attributes (e.g., `dim_product`, `dim_customer`)
- **Conformance** means: Every foreign key in a fact table must have a matching primary key in the dimension table

### Why It Matters

During data migration, conformance violations can occur when:
- Dimension records are missing or not migrated
- Foreign key values are corrupted or transformed incorrectly
- Data loading order causes temporary orphaned keys
- Source system had referential integrity issues

## How It Works

### 1. Automatic Detection from Query Workload

The workload analyzer examines your SQL Server Query Store and identifies:
- **JOIN patterns** between fact and dimension tables
- **Foreign key columns** used in these JOINs
- **Star schema relationships** (fact → dimension)

**Detection logic** (`workload/analyzer.py:142-208`):
```python
# Detects fact tables (fact_*)
is_fact_table = 'fact_' in table_lower or table_lower.startswith('fact')

# Detects dimension tables (dim_*)
is_dim_partner = 'dim_' in partner_lower or partner_lower.startswith('dim')

# Identifies foreign key columns (columns ending in _id, _key, etc.)
if self._is_identifier_column(col_name, table_name):
    join_columns.append(col_name)

# Creates conformance validation
if is_fact_table and is_dim_partner:
    validation_type = 'fact_dimension_conformance'
```

### 2. Validation SQL Generation

For each detected relationship, the system generates SQL queries to find **orphaned foreign keys** (keys in the fact table that don't exist in the dimension table).

**Generated SQL** (`workload/pipeline_generator.py:345-388`):

**SQL Server:**
```sql
SELECT COUNT(*) as orphaned_count
FROM fact_sales f
LEFT JOIN dim_product d ON f.product_key = d.product_key
WHERE d.product_key IS NULL
```

**Snowflake:**
```sql
SELECT COUNT(*) as orphaned_count
FROM FACT_SALES f
LEFT JOIN DIM_PRODUCT d ON f.PRODUCT_KEY = d.PRODUCT_KEY
WHERE d.PRODUCT_KEY IS NULL
```

### 3. Comparison and Validation

The validation:
1. Runs both queries (SQL Server and Snowflake)
2. Compares the orphaned counts
3. **Ideally, both should return 0** (no orphaned keys)
4. If counts differ, it indicates a migration issue

**Expected Results:**
- ✅ **PASS**: Both systems have 0 orphaned keys
- ⚠️ **WARN**: Both systems have the same number of orphaned keys (source data issue)
- ❌ **FAIL**: Different orphaned key counts (migration integrity issue)

## Real-World Example

### Scenario: Retail Data Warehouse

**Tables:**
- `fact_sales` - Contains sales transactions
- `dim_product` - Contains product information
- `dim_customer` - Contains customer information

**Detected Relationships:**
1. `fact_sales.product_key` → `dim_product.product_key`
2. `fact_sales.customer_key` → `dim_customer.customer_key`

### Generated Validations

**Validation 1: Product Conformance**
```yaml
- name: validation_1_comparative
  type: comparative
  validator: custom_sql
  description: "Fact-Dimension Conformance: All product_key in fact_sales must exist in dim_product"
  confidence: 75.0
  enabled: true
  config:
    sql_server_query: |
      SELECT COUNT(*) as orphaned_count
      FROM fact_sales f
      LEFT JOIN dim_product d ON f.product_key = d.product_key
      WHERE d.product_key IS NULL
    snowflake_query: |
      SELECT COUNT(*) as orphaned_count
      FROM FACT_SALES f
      LEFT JOIN DIM_PRODUCT d ON f.PRODUCT_KEY = d.PRODUCT_KEY
      WHERE d.PRODUCT_KEY IS NULL
    compare_mode: result_set
    tolerance: 0.0
  metadata:
    validation_type: fact_dimension_conformance
    fact_table: fact_sales
    dimension_table: dim_product
    foreign_keys: ["product_key"]
```

**Validation 2: Customer Conformance**
```yaml
- name: validation_2_comparative
  type: comparative
  validator: custom_sql
  description: "Fact-Dimension Conformance: All customer_key in fact_sales must exist in dim_customer"
  confidence: 75.0
  enabled: true
  config:
    sql_server_query: |
      SELECT COUNT(*) as orphaned_count
      FROM fact_sales f
      LEFT JOIN dim_customer d ON f.customer_key = d.customer_key
      WHERE d.customer_key IS NULL
    snowflake_query: |
      SELECT COUNT(*) as orphaned_count
      FROM FACT_SALES f
      LEFT JOIN DIM_CUSTOMER d ON f.CUSTOMER_KEY = d.CUSTOMER_KEY
      WHERE d.CUSTOMER_KEY IS NULL
    compare_mode: result_set
    tolerance: 0.0
  metadata:
    validation_type: fact_dimension_conformance
    fact_table: fact_sales
    dimension_table: dim_customer
    foreign_keys: ["customer_key"]
```

## User Workflow

### 1. Upload Query Store Workload
Navigate to **Workload Analysis** and upload your SQL Server Query Store data.

### 2. Review Suggestions
The analyzer will generate suggestions including:
- ✅ Distribution checks (for measures like `amount`, `quantity`)
- ✅ Statistical validations (for aggregated measures)
- ✅ Cardinality checks (for unique columns)
- ✅ **Fact-Dimension Conformance** (for foreign key relationships)

**What You'll See:**
```
Table: fact_sales

Suggestions:
1. Fact-Dimension Conformance: All product_key in fact_sales must exist in dim_product
   Confidence: 75% | Source: workload | Queries: 15

2. Fact-Dimension Conformance: All customer_key in fact_sales must exist in dim_customer
   Confidence: 75% | Source: workload | Queries: 12

3. Measure column with statistical aggregations (amount)
   Confidence: 85% | Source: workload | Queries: 20
```

### 3. Select and Generate Pipeline
Select the conformance validations you want to include in your pipeline and click **Generate Pipeline**.

### 4. Execute and Review Results
Run the pipeline and review the results:
- **0 orphaned keys**: ✅ Perfect conformance
- **Same count in both systems**: ⚠️ Source data issue (existed before migration)
- **Different counts**: ❌ Migration integrity issue requiring investigation

## Technical Implementation

### Files Modified

#### 1. `workload/analyzer.py` (lines 142-208)
**Added intelligent conformance detection:**
- Detects fact tables (`fact_*` naming pattern)
- Detects dimension tables (`dim_*` naming pattern)
- Filters join columns to only include foreign keys (identifiers)
- Creates suggestions with proper metadata

**Key Method:**
```python
def _suggest_referential_integrity(self, table_usage: TableUsage) -> List[ValidationSuggestion]:
    """Suggest referential integrity / fact-dimension conformance checks based on JOIN patterns"""
    # ... detection logic ...

    if is_conformance:
        validator_name = 'comparative'
        metadata = {
            'validation_type': 'fact_dimension_conformance',
            'fact_table': table_usage.table_name,
            'dimension_table': partner_table,
            'foreign_keys': join_columns,
            'description': f"Verify all foreign keys from {fact_table} have matching records in {dim_table}"
        }
```

#### 2. `workload/pipeline_generator.py` (lines 341-430)
**Added SQL generation for conformance validations:**
- Detects 'comparative' validator with 'fact_dimension_conformance' metadata
- Generates LEFT JOIN queries to find orphaned keys
- Creates both SQL Server and Snowflake versions
- Sets appropriate tolerance (0.0 for exact match)

**Key Method:**
```python
def _create_validation_rule(self, validation: Dict[str, Any], index: int) -> Dict[str, Any]:
    # ...
    elif validator_name == 'comparative' and metadata.get('validation_type') == 'fact_dimension_conformance':
        # Generate LEFT JOIN queries to find orphaned foreign keys
        sql_server_query = f"""
            SELECT COUNT(*) as orphaned_count
            FROM {fact_table} f
            LEFT JOIN {dim_table} d ON {fk_join_conditions}
            WHERE {fk_is_null_conditions}
        """
        # ... Snowflake version ...
```

#### 3. `workload/pipeline_generator.py` (lines 497-520)
**Updated validator type mapping:**
```python
def _map_validator_type(self, validator_name: str) -> str:
    if name_lower == 'comparative':
        return 'comparative'
    # ... other types ...
```

## Benefits

### 1. Automatic Data Warehouse Intelligence
- Understands star schema patterns
- Recognizes fact-dimension relationships
- No manual configuration required

### 2. Comprehensive Integrity Validation
- Validates foreign key conformance
- Identifies orphaned records
- Compares both systems consistently

### 3. Migration Confidence
- Ensures referential integrity after migration
- Detects data loading issues early
- Provides clear pass/fail results

### 4. Query-Driven Validation
- Based on actual query patterns
- Validates relationships that matter to your workload
- Prioritizes frequently-joined tables

## Troubleshooting

### No Conformance Suggestions Generated

**Possible causes:**
1. Workload doesn't contain JOIN queries
2. Tables don't follow naming conventions (fact_*, dim_*)
3. JOIN columns are not identifiers (don't end in _id, _key, etc.)

**Solution:**
- Ensure workload includes representative queries with JOINs
- Use consistent naming conventions for fact and dimension tables
- Foreign key columns should follow identifier naming patterns

### Validation Shows Orphaned Keys in Both Systems

**This indicates:**
- Source data already had referential integrity issues
- Orphaned keys existed before migration
- The validation correctly detected the issue

**Next steps:**
- Investigate source data quality
- Determine if orphaned keys are acceptable
- Consider cleaning source data before migration

### Different Orphaned Counts Between Systems

**This indicates:**
- Migration integrity issue
- Data not migrated correctly
- Possible transformation errors

**Next steps:**
- Identify which specific keys are orphaned
- Review data transformation logic
- Check data loading order and dependencies

## Future Enhancements

Potential improvements:
1. **Detailed orphan reporting**: Return specific orphaned key values, not just counts
2. **Multi-column foreign keys**: Support composite foreign keys
3. **Custom naming patterns**: Allow user-defined fact/dimension naming conventions
4. **Orphan remediation**: Suggest fixes for orphaned keys
5. **Dependency ordering**: Recommend loading order based on conformance relationships

## Summary

The Fact-Dimension Conformance validation feature:
- 🧠 **Automatically detects** star schema relationships from query patterns
- 🔍 **Identifies orphaned** foreign keys in both systems
- ⚖️ **Compares integrity** between SQL Server and Snowflake
- ✅ **Ensures conformance** of fact-dimension relationships
- 📊 **Validates migration** correctness for data warehouse schemas

This makes the system aware of data warehouse best practices and ensures that your migrated data maintains proper referential integrity!
