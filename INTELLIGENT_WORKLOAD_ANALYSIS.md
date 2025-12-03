# Intelligent Workload Analysis & Column Classification

## Overview

The workload analyzer now applies **data warehouse intelligence** to understand column semantics and suggest appropriate validations. It thinks like a data analyst, not just a pattern matcher!

## Intelligent Column Classification

### What Changed

Previously, the system would blindly suggest aggregations (SUM, AVG, etc.) on ANY numeric column, including:
- ❌ `product_key` (ID field)
- ❌ `customer_id` (Primary key)
- ❌ `store_number` (Code/identifier)

Now, the system intelligently classifies columns into:
1. **Identifiers** (IDs, Keys, Codes) - Should NOT be aggregated
2. **Measures** (Amounts, Quantities, Prices) - SHOULD be aggregated
3. **Attributes** (Names, Descriptions) - Context fields

## Column Role Detection Logic

### Identifier Detection (`_is_identifier_column`)

A column is classified as an **identifier** if:

**Pattern-based detection:**
- Ends with: `_id`, `_key`, `_pk`, `_sk`, `_code`, `_number`, `_num`
- Equals: `key`, `id`, `code`

**Table type detection:**
- **Dimension tables** (`dim_*`): Almost all columns are identifiers/attributes
  - Exception: Columns with measure keywords (price, cost, amount, etc.)
  - Example: `dim_product.product_key` → Identifier ✓
  - Example: `dim_product.unit_price` → Measure (exception) ✓

### Measure Detection (`_is_measure_column`)

A column is classified as a **measure** if:

**Must be numeric first:**
- Data type: INT, BIGINT, DECIMAL, NUMERIC, FLOAT, REAL, MONEY, etc.

**NOT an identifier:**
- Passes through identifier check first

**Measure keyword detection:**
- Contains: `amount`, `quantity`, `qty`, `price`, `cost`, `total`, `sum`
- Contains: `revenue`, `sales`, `discount`, `tax`, `fee`, `balance`
- Contains: `weight`, `volume`, `size`, `rate`, `percent`, `score`, `value`

**Table type detection:**
- **Fact tables** (`fact_*`): Numeric columns (excluding keys) are measures
  - Example: `fact_sales.quantity` → Measure ✓
  - Example: `fact_sales.amount` → Measure ✓
  - Example: `fact_sales.product_key` → Identifier (excluded) ✗

## Updated Validation Suggestions

### Distribution Checks (analyzer.py:177-212)

**Before:**
```python
if is_numeric:  # Would suggest for ANY numeric column
    suggestions.append(ValidationSuggestion(
        validator_name='validate_distribution',
        ...
    ))
```

**After:**
```python
is_measure = self._is_measure_column(col_name, table_name, col_type)
if is_measure:  # Only for actual measures!
    suggestions.append(ValidationSuggestion(
        validator_name='validate_distribution',
        reason=f"Measure column used in {col_usage.query_count} queries...",
        metadata={'column_role': 'measure'}
    ))
```

### Statistical Validations (analyzer.py:321-357)

**Before:**
```python
if is_numeric and has_stat_func:
    # Would suggest SUM(product_key) 😱
```

**After:**
```python
is_measure = self._is_measure_column(col_name, table_name, col_type)
if is_measure and has_stat_func:
    # Only suggests SUM(amount), AVG(price), etc. 👍
    suggestions.append(ValidationSuggestion(
        reason=f"Measure column with statistical aggregations ({', '.join(funcs)})",
        metadata={'column_role': 'measure'}
    ))
```

## Real-World Examples

### Example 1: Dimension Table (dim_product)

**Columns:**
- `product_key` (INT) → **Identifier** → No aggregations suggested ✓
- `product_id` (INT) → **Identifier** → No aggregations suggested ✓
- `product_name` (VARCHAR) → **Attribute** → No aggregations suggested ✓
- `category` (VARCHAR) → **Attribute** → GROUP BY suggestions ✓
- `unit_price` (DECIMAL) → **Measure** (exception) → SUM, AVG suggested ✓

### Example 2: Fact Table (fact_sales)

**Columns:**
- `sale_key` (INT) → **Identifier** → No aggregations suggested ✓
- `product_key` (INT) → **Identifier** (FK) → JOIN suggestions only ✓
- `customer_key` (INT) → **Identifier** (FK) → JOIN suggestions only ✓
- `quantity` (INT) → **Measure** → SUM, AVG suggested ✓
- `amount` (DECIMAL) → **Measure** → SUM, AVG suggested ✓
- `discount_amount` (DECIMAL) → **Measure** → SUM, AVG suggested ✓

### Example 3: What Gets Suggested Now

**Dimension Table (dim_customer):**
```
❌ SUM(customer_key)     → Filtered out (identifier)
❌ AVG(customer_id)      → Filtered out (identifier)
✓ COUNT(customer_name)   → Suggested (cardinality)
✓ GROUP BY region        → Suggested (categorical)
```

**Fact Table (fact_sales):**
```
✓ SUM(amount)            → Suggested (measure)
✓ AVG(unit_price)        → Suggested (measure)
✓ SUM(quantity)          → Suggested (measure)
❌ SUM(product_key)      → Filtered out (identifier)
❌ AVG(customer_key)     → Filtered out (identifier)
✓ COUNT(*)               → Suggested (cardinality)
```

## Benefits

### 1. Meaningful Validations
- Only suggests aggregations that make business sense
- Avoids nonsensical validations like `SUM(product_id)`

### 2. Data Warehouse Awareness
- Understands star schema patterns (fact vs dimension)
- Recognizes surrogate keys vs natural keys vs measures

### 3. Analyst-Like Thinking
- **Identifiers**: Used for JOINs and grouping, not aggregation
- **Measures**: Used for SUM, AVG, MIN, MAX calculations
- **Attributes**: Used for filtering and descriptive context

### 4. Better User Experience
- Reduces noise in suggestions
- Increases confidence in auto-generated validations
- Focuses on business-relevant comparisons

## Technical Implementation

### Files Modified

1. **workload/analyzer.py** (lines 32-109)
   - Added `_is_identifier_column()` method
   - Added `_is_measure_column()` method
   - Updated `_suggest_distribution_checks()` to use measure detection
   - Updated `_suggest_statistics()` to use measure detection

### Column Classification Flow

```
Column Encountered
    ↓
Check Data Type (numeric?)
    ↓
Check if Identifier (_is_identifier_column)
    ├─ Yes → Suggest: JOINs, GROUP BY, Cardinality
    └─ No → Continue
        ↓
    Check if Measure (_is_measure_column)
        ├─ Yes → Suggest: SUM, AVG, Distribution, Statistics
        └─ No → Suggest: Data quality checks only
```

## Configuration

The intelligence is built-in and requires no configuration. It automatically:
- Detects table type (dimension vs fact) from naming
- Identifies column role from naming patterns
- Applies appropriate validation suggestions

## Future Enhancements

Potential improvements:
1. **ML-based classification**: Learn from user feedback on suggestions
2. **Schema metadata integration**: Use foreign key relationships for better detection
3. **Business glossary**: Allow users to define custom measure/identifier patterns
4. **Query pattern learning**: Improve detection based on how columns are actually used

## Testing

To verify the intelligence is working:

1. **Upload a Query Store workload** with dimension and fact tables
2. **Review suggestions** in the Pipeline Builder
3. **Verify** that:
   - No aggregations suggested on `*_id`, `*_key` columns
   - Aggregations suggested on `amount`, `quantity`, `price` columns
   - GROUP BY suggested on categorical columns
   - JOIN validations suggested on foreign keys

## Summary

The system now thinks like a data analyst:
- 🧠 **Understands** column semantics (ID vs measure vs attribute)
- 📊 **Applies** data warehouse best practices (star schema patterns)
- ✅ **Suggests** meaningful validations (no more `SUM(customer_id)`)
- 🎯 **Focuses** on business-relevant comparisons

This makes the auto-generated validation pipelines much more useful and trustworthy!
