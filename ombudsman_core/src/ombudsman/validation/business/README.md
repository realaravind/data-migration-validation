# Custom Business Query Validation

This module enables you to validate complex business queries with multiple joins, date dimensions, and analytical logic beyond simple table-level comparisons.

## Overview

The custom query validator allows you to:
- Validate complex SQL queries with multiple table joins
- Compare results between SQL Server and Snowflake
- Test date-based analytics (monthly, quarterly, yearly)
- Validate Top N queries (top 5 customers, top 10 products, etc.)
- Test random sampling validations
- Execute business-specific validations that match your use cases

## Quick Start

### 1. Browse Examples

Check out comprehensive examples in:
```
ombudsman/config/custom_query_examples.yaml
```

This file contains 12 real-world examples including:
- Total revenue by product category
- Monthly sales summary with date dimensions
- Top 5 customers by revenue
- Complex multi-table joins
- Year-over-year comparisons
- Random sample validation
- And more...

### 2. Create Your Queries

Edit your custom queries in:
```
ombudsman/config/custom_queries.yaml
```

### 3. Query Definition Format

```yaml
- name: "Descriptive name for the query"
  comparison_type: "aggregation|rowset|count"
  tolerance: 0.01          # Optional, default 0.01
  limit: 100               # Optional, for rowset comparisons
  sql_query: |
    SELECT ...
    FROM ...
    WHERE ...
  snow_query: |
    SELECT ...
    FROM ...
    WHERE ...
```

## Comparison Types

### 1. Aggregation (Single Result)
Best for: Total metrics, overall counts, grand totals

```yaml
comparison_type: "aggregation"
```

Example:
```sql
SELECT
  SUM(Amount) as TotalRevenue,
  COUNT(*) as OrderCount,
  AVG(Amount) as AvgOrderValue
FROM fact.Sales
```

**Use when**: Your query returns a single row with aggregate metrics.

### 2. Rowset (Multiple Rows)
Best for: Grouped data, time series, ranked results

```yaml
comparison_type: "rowset"
limit: 100  # Compare first N rows
```

Example:
```sql
SELECT
  d.Year,
  d.Month,
  SUM(s.Amount) as Revenue
FROM fact.Sales s
INNER JOIN dim.Date d ON s.OrderDate = d.Date
GROUP BY d.Year, d.Month
ORDER BY d.Year, d.Month
```

**Use when**: Your query returns multiple rows that need to be compared.

### 3. Count (Simple Count)
Best for: Record counts, filtered counts

```yaml
comparison_type: "count"
```

Example:
```sql
SELECT COUNT(DISTINCT CustomerID) as count
FROM fact.Sales
WHERE OrderDate >= '2024-01-01'
```

**Use when**: You only care about the count of records.

## Common Patterns

### Pattern 1: Date Dimension Queries

**Monthly Sales:**
```yaml
- name: "Monthly Sales 2024"
  comparison_type: "rowset"
  limit: 12
  sql_query: |
    SELECT
      d.Month,
      d.MonthName,
      SUM(s.Amount) as TotalSales
    FROM fact.Sales s
    INNER JOIN dim.Date d ON s.OrderDate = d.Date
    WHERE d.Year = 2024
    GROUP BY d.Month, d.MonthName
    ORDER BY d.Month
  snow_query: |
    SELECT
      d.Month,
      d.MonthName,
      SUM(s.Amount) as TotalSales
    FROM FACT.SALES s
    INNER JOIN DIM.DATE d ON s.OrderDate = d.Date
    WHERE d.Year = 2024
    GROUP BY d.Month, d.MonthName
    ORDER BY d.Month
```

### Pattern 2: Top N Queries

**Top 5 Customers:**
```yaml
- name: "Top 5 Customers by Revenue"
  comparison_type: "rowset"
  limit: 5
  sql_query: |
    SELECT TOP 5
      c.CustomerID,
      c.CustomerName,
      SUM(s.Amount) as Revenue
    FROM fact.Sales s
    INNER JOIN dim.Customer c ON s.CustomerID = c.CustomerID
    GROUP BY c.CustomerID, c.CustomerName
    ORDER BY Revenue DESC
  snow_query: |
    SELECT
      c.CustomerID,
      c.CustomerName,
      SUM(s.Amount) as Revenue
    FROM FACT.SALES s
    INNER JOIN DIM.CUSTOMER c ON s.CustomerID = c.CustomerID
    GROUP BY c.CustomerID, c.CustomerName
    ORDER BY Revenue DESC
    LIMIT 5
```

### Pattern 3: Multi-Table Joins

**Sales with Multiple Dimensions:**
```yaml
- name: "Q1 2024 Sales by Region and Product"
  comparison_type: "rowset"
  limit: 100
  sql_query: |
    SELECT
      c.Region,
      p.Category,
      SUM(s.Amount) as Revenue,
      COUNT(*) as Orders
    FROM fact.Sales s
    INNER JOIN dim.Customer c ON s.CustomerID = c.CustomerID
    INNER JOIN dim.Product p ON s.ProductID = p.ProductID
    INNER JOIN dim.Date d ON s.OrderDate = d.Date
    WHERE d.Year = 2024 AND d.Quarter = 1
    GROUP BY c.Region, p.Category
    ORDER BY Revenue DESC
  snow_query: |
    SELECT
      c.Region,
      p.Category,
      SUM(s.Amount) as Revenue,
      COUNT(*) as Orders
    FROM FACT.SALES s
    INNER JOIN DIM.CUSTOMER c ON s.CustomerID = c.CustomerID
    INNER JOIN DIM.PRODUCT p ON s.ProductID = p.ProductID
    INNER JOIN DIM.DATE d ON s.OrderDate = d.Date
    WHERE d.Year = 2024 AND d.Quarter = 1
    GROUP BY c.Region, p.Category
    ORDER BY Revenue DESC
```

### Pattern 4: Specific Customer/Product Validation

```yaml
- name: "Customer 12345 Transaction History"
  comparison_type: "rowset"
  limit: 50
  sql_query: |
    SELECT
      s.OrderID,
      s.OrderDate,
      p.ProductName,
      s.Amount
    FROM fact.Sales s
    INNER JOIN dim.Product p ON s.ProductID = p.ProductID
    WHERE s.CustomerID = 12345
    ORDER BY s.OrderDate DESC
  snow_query: |
    SELECT
      s.OrderID,
      s.OrderDate,
      p.ProductName,
      s.Amount
    FROM FACT.SALES s
    INNER JOIN DIM.PRODUCT p ON s.ProductID = p.ProductID
    WHERE s.CustomerID = 12345
    ORDER BY s.OrderDate DESC
```

### Pattern 5: Random Sampling

```yaml
- name: "Random Sample 100 Orders"
  comparison_type: "rowset"
  limit: 100
  sql_query: |
    SELECT
      s.OrderID,
      s.CustomerID,
      s.Amount
    FROM fact.Sales s
    WHERE s.OrderID IN (
      SELECT TOP 100 OrderID
      FROM fact.Sales
      ORDER BY NEWID()
    )
    ORDER BY s.OrderID
  snow_query: |
    SELECT
      s.OrderID,
      s.CustomerID,
      s.Amount
    FROM FACT.SALES s
    WHERE s.OrderID IN (
      SELECT OrderID
      FROM FACT.SALES
      ORDER BY RANDOM()
      LIMIT 100
    )
    ORDER BY s.OrderID
```

## Usage in Code

```python
from ombudsman.validation.business import validate_custom_queries, load_user_queries

# Load queries from config
queries = load_user_queries()

# Or load specific queries
from ombudsman.validation.business import load_queries_from_yaml
queries = load_queries_from_yaml('path/to/your/queries.yaml')

# Run validation
result = validate_custom_queries(
    sql_conn=sql_connection,
    snow_conn=snowflake_connection,
    query_definitions=queries,
    mapping=table_mapping
)

# Check results
if result['status'] == 'PASS':
    print("All queries passed!")
else:
    print(f"Found {len(result['issues'])} issues")
    for issue in result['issues']:
        print(f"  - {issue['query_name']}: {issue}")

# View explain data (always available)
for query_name, explain in result['explain'].items():
    print(f"\nQuery: {query_name}")
    print(f"Interpretation: {explain['interpretation']}")
    print(f"SQL execution time: {explain['sql_execution_time']}s")
    print(f"Snowflake execution time: {explain['snow_execution_time']}s")
```

## Database-Specific Syntax Differences

### SQL Server vs Snowflake

| Feature | SQL Server | Snowflake |
|---------|-----------|-----------|
| Limit rows | `SELECT TOP N` | `LIMIT N` |
| Standard deviation | `STDEV()` | `STDDEV()` |
| Current date | `GETDATE()` | `CURRENT_DATE()` |
| Random | `NEWID()` | `RANDOM()` |

## Best Practices

1. **Start with examples**: Copy from `custom_query_examples.yaml` and modify

2. **Use appropriate comparison types**:
   - Single aggregation → `aggregation`
   - Multiple grouped rows → `rowset`
   - Just counting → `count`

3. **Set reasonable limits**: For rowset comparisons, limit to what you actually need (10-100 rows)

4. **Handle NULL values**: Use `COALESCE()` or `ISNULL()` to handle NULLs consistently

5. **Order results**: Always use `ORDER BY` for rowset comparisons to ensure consistent ordering

6. **Test incrementally**: Start with simple queries, then add complexity

7. **Use explain data**: Always check the explain data to understand mismatches

## Troubleshooting

### Issue: Queries return different row counts
**Solution**: Check for:
- Different NULL handling
- Outer vs inner joins
- Filter conditions

### Issue: Numeric values slightly different
**Solution**: Increase tolerance:
```yaml
tolerance: 0.1  # More lenient
```

### Issue: Date formatting differences
**Solution**: Cast to consistent format:
```sql
CAST(OrderDate AS DATE)
```

### Issue: Query timeout
**Solution**: Add indexes or simplify the query

## Getting Suggestions

Run this to see suggested patterns:
```python
from ombudsman.validation.business import get_query_suggestions

suggestions = get_query_suggestions()
for category, patterns in suggestions.items():
    print(f"\n{category}:")
    for pattern in patterns:
        print(f"  - {pattern}")
```

## Support

For more examples and patterns, see:
- `custom_query_examples.yaml` - 12 comprehensive examples
- Existing validators in `ombudsman/validation/` for inspiration
