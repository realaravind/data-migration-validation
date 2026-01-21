# How to Use Intelligent Query Suggestions - Quick Start Guide

## What Does It Do?

The intelligent query suggestion system **automatically creates custom validation queries** for you based on your actual database schema. Instead of writing 15-20 complex SQL queries by hand, you click a button and get them all generated instantly.

## Step-by-Step Usage

### Step 1: Extract Metadata from Your Databases

First, you need to tell the system about your database structure.

**Using the Web UI (Recommended):**
1. Open your browser and go to: http://localhost:3000
2. Click on "Metadata Extraction" in the navigation
3. Fill in the form:
   - SQL Server Database: `SampleDW`
   - SQL Server Schemas: `DIM, FACT`
   - Snowflake Database: `SAMPLEDW`
   - Snowflake Schemas: `DIM, FACT`
4. Click "Extract Metadata"
5. Wait for completion (usually 30-60 seconds)

**Using API (Alternative):**
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

**What This Does:**
- Discovers all tables in your database
- Finds all columns and their data types
- Identifies numeric columns (for SUM/AVG queries)
- Detects primary keys
- Saves everything to `ombudsman_core/data/metadata.json`

---

### Step 2: Generate Table Mappings

The system needs to know which SQL Server tables map to which Snowflake tables.

**Using the Web UI (Recommended):**
1. Go to: http://localhost:3000
2. Click on "Database Mapping" in the navigation
3. Click "Extract & Map Tables" button
4. Review the auto-generated mappings
5. Edit any incorrect mappings if needed
6. Click "Save Mappings"

**Using API (Alternative):**
```bash
curl -X POST http://localhost:8000/mapping/suggest
```

**What This Does:**
- Matches SQL Server tables to Snowflake tables
- Creates column-level mappings
- Saves to `ombudsman_core/data/mapping.json`

---

### Step 3: (Optional) Define Table Relationships

For best results, tell the system how your tables relate to each other.

**Create or edit file:** `/Users/aravind/sourcecode/projects/data-migration-validator/ombudsman_core/src/ombudsman/config/relationships.yaml`

```yaml
# Example: Sales fact table relationships
sales_to_customer:
  fact_table: fact_sales
  dim_table: dim_customer
  fact_key: CustomerKey
  dim_key: CustomerKey

sales_to_product:
  fact_table: fact_sales
  dim_table: dim_product
  fact_key: ProductKey
  dim_key: ProductKey

sales_to_date:
  fact_table: fact_sales
  dim_table: dim_date
  fact_key: DateKey
  dim_key: DateKey
```

**What This Does:**
- Enables the system to create JOIN queries
- Generates fact+dimension aggregation queries
- Creates time-based trend queries

---

### Step 4: Generate Intelligent Suggestions 🧠

Now the magic happens! Generate all your custom queries automatically.

**Method A: Using Swagger UI (Easiest):**
1. Open: http://localhost:8000/docs
2. Scroll down to "Custom Business Queries" section
3. Find **POST /custom-queries/intelligent-suggest**
4. Click "Try it out"
5. Click "Execute"
6. See all generated queries in the response!

**Method B: Using API:**
```bash
curl -X POST http://localhost:8000/custom-queries/intelligent-suggest \
  | python3 -m json.tool
```

**Method C: Auto-Save to File (Best for Quick Start):**
```bash
curl -X POST http://localhost:8000/custom-queries/save-suggestions
```

This automatically saves all suggestions to:
`ombudsman_core/src/ombudsman/config/custom_queries.yaml`

---

### Step 5: Review Generated Queries

**Using Swagger UI:**
1. Go to: http://localhost:8000/docs
2. Find **GET /custom-queries/user-queries**
3. Click "Try it out" → "Execute"
4. See all your saved queries

**Using API:**
```bash
curl http://localhost:8000/custom-queries/user-queries | python3 -m json.tool
```

**Manually:**
```bash
cat /Users/aravind/sourcecode/projects/data-migration-validator/ombudsman_core/src/ombudsman/config/custom_queries.yaml
```

---

### Step 6: Validate the Queries

Run all generated queries to compare SQL Server vs Snowflake.

**Using Swagger UI:**
1. Go to: http://localhost:8000/docs
2. Find **POST /custom-queries/validate-user-queries**
3. Click "Try it out" → "Execute"
4. See validation results with pass/fail status

**Using API:**
```bash
curl -X POST http://localhost:8000/custom-queries/validate-user-queries \
  | python3 -m json.tool
```

---

## What Queries Get Generated?

Here's exactly what the system creates for you:

### 1. Record Count Queries (HIGH Priority)
**One for each table discovered**

```yaml
- name: "Record Count - fact_sales"
  comparison_type: "count"
  sql_query: "SELECT COUNT(*) as count FROM dbo.fact_sales"
  snow_query: "SELECT COUNT(*) as count FROM SAMPLEDW.FACT.FACT_SALES"
```

### 2. Metric Aggregation Queries (HIGH Priority)
**For each numeric column in fact tables**

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
```

### 3. Join Queries (MEDIUM Priority)
**Fact table grouped by dimension**

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
```

### 4. Time-Based Queries (HIGH Priority)
**Monthly/yearly trends**

```yaml
- name: "Monthly Trend - fact_sales"
  comparison_type: "rowset"
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
```

### 5. Top N Queries (MEDIUM Priority)
**Top 5 by dimension**

```yaml
- name: "Top 5 Customer"
  comparison_type: "rowset"
  limit: 5
  sql_query: |
    SELECT TOP 5
      c.CustomerName,
      SUM(SalesAmount) as total_metric
    FROM dbo.fact_sales f
    INNER JOIN dbo.dim_customer c ON f.CustomerKey = c.CustomerKey
    GROUP BY c.CustomerName
    ORDER BY total_metric DESC
```

### 6. Multi-Dimension Joins (LOW Priority)
**Complex queries with multiple dimensions**

```yaml
- name: "fact_sales by Customer and Product"
  comparison_type: "rowset"
  limit: 50
  sql_query: |
    SELECT
      c.CustomerName,
      p.ProductName,
      SUM(SalesAmount) as total_metric
    FROM dbo.fact_sales f
    INNER JOIN dbo.dim_customer c ON f.CustomerKey = c.CustomerKey
    INNER JOIN dbo.dim_product p ON f.ProductKey = p.ProductKey
    GROUP BY c.CustomerName, p.ProductName
    ORDER BY total_metric DESC
```

---

## Complete Example Session

Let me show you a complete workflow:

```bash
# Step 1: Extract metadata
echo "Step 1: Extracting metadata..."
curl -X POST http://localhost:8000/metadata/extract \
  -H "Content-Type: application/json" \
  -d '{"sql_database": "SampleDW", "sql_schemas": ["DIM", "FACT"],
       "snowflake_database": "SAMPLEDW", "snowflake_schemas": ["DIM", "FACT"]}' \
  2>/dev/null | python3 -m json.tool | head -20

# Step 2: Generate mappings
echo -e "\n\nStep 2: Generating mappings..."
curl -X POST http://localhost:8000/mapping/suggest 2>/dev/null | python3 -m json.tool | head -20

# Step 3: Auto-generate and save queries
echo -e "\n\nStep 3: Generating intelligent suggestions..."
curl -X POST http://localhost:8000/custom-queries/save-suggestions 2>/dev/null | python3 -m json.tool

# Step 4: Validate all queries
echo -e "\n\nStep 4: Validating queries..."
curl -X POST http://localhost:8000/custom-queries/validate-user-queries 2>/dev/null | python3 -m json.tool | head -50

echo -e "\n\n✅ Done! Check results above."
```

---

## Understanding the Results

When you validate queries, you'll see results like this:

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
          "interpretation": "Record counts match: 50000 records",
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
          "interpretation": "Aggregations match within tolerance",
          "execution_time_sql": 0.23
        }
      }
    ]
  }
}
```

**Key Fields:**
- `status`: PASS or FAIL
- `explain.sql_result`: What SQL Server returned
- `explain.snow_result`: What Snowflake returned
- `explain.interpretation`: Human-readable explanation
- `execution_time_*`: How long each query took

---

## Customizing Generated Queries

After auto-generation, you can edit the queries:

```bash
# Open the file
nano /Users/aravind/sourcecode/projects/data-migration-validator/ombudsman_core/src/ombudsman/config/custom_queries.yaml
```

**Common customizations:**

1. **Add WHERE clauses:**
```yaml
sql_query: |
  SELECT SUM(Amount) FROM fact_sales
  WHERE Year = 2023 AND Status = 'Completed'
```

2. **Change tolerance:**
```yaml
tolerance: 0.001  # More strict (default is 0.01)
```

3. **Adjust limits:**
```yaml
limit: 100  # More rows (default varies by query type)
```

4. **Add custom calculations:**
```yaml
sql_query: |
  SELECT
    SUM(Amount) as total,
    SUM(CASE WHEN Status='Returned' THEN Amount ELSE 0 END) as returns,
    SUM(Amount) - SUM(CASE WHEN Status='Returned' THEN Amount ELSE 0 END) as net
  FROM fact_sales
```

---

## Troubleshooting

### "No metadata found"
**Problem:** You see: `{"status":"error","message":"No metadata found"}`

**Solution:** Run Step 1 (metadata extraction) first:
```bash
curl -X POST http://localhost:8000/metadata/extract \
  -H "Content-Type: application/json" \
  -d '{"sql_database": "SampleDW", "sql_schemas": ["DIM", "FACT"],
       "snowflake_database": "SAMPLEDW", "snowflake_schemas": ["DIM", "FACT"]}'
```

---

### "No mapping found"
**Problem:** System can't match tables

**Solution:** Run Step 2 (mapping generation):
```bash
curl -X POST http://localhost:8000/mapping/suggest
```

---

### "No join queries generated"
**Problem:** Only getting record count queries

**Solution:** Create `relationships.yaml` file (Step 3):
```bash
nano /Users/aravind/sourcecode/projects/data-migration-validator/ombudsman_core/src/ombudsman/config/relationships.yaml
```

Add your table relationships (see Step 3 example above).

---

### "Query validation fails"
**Problem:** Generated queries return errors

**Possible causes:**
1. **Database not accessible** - Check connection settings
2. **Tables don't exist** - Verify table names in metadata
3. **Columns renamed** - Update mapping
4. **Permissions issue** - Check database user permissions

**Debug:**
```bash
# Check what tables were found
curl http://localhost:8000/custom-queries/user-queries | python3 -m json.tool

# Test connection
curl http://localhost:8000/connections/status
```

---

## Quick Reference - All Endpoints

| Endpoint | What It Does |
|----------|-------------|
| POST `/metadata/extract` | Extract database schema |
| POST `/mapping/suggest` | Generate table mappings |
| POST `/custom-queries/intelligent-suggest` | Preview suggestions (doesn't save) |
| POST `/custom-queries/save-suggestions` | Generate & auto-save to file |
| GET `/custom-queries/user-queries` | View saved queries |
| POST `/custom-queries/validate-user-queries` | Run all validations |
| GET `/custom-queries/examples` | Browse 12 example templates |
| GET `/custom-queries/config-location` | Find config file paths |

---

## Full Web UI Workflow

If you prefer clicking buttons instead of running commands:

1. **Go to:** http://localhost:3000

2. **Metadata Extraction Tab:**
   - Fill in database details
   - Click "Extract Metadata"

3. **Database Mapping Tab:**
   - Click "Extract & Map Tables"
   - Review mappings
   - Click "Save Mappings"

4. **Open Swagger UI:** http://localhost:8000/docs

5. **Find "Custom Business Queries" section**

6. **Click on POST /custom-queries/save-suggestions**
   - Click "Try it out"
   - Click "Execute"

7. **Click on POST /custom-queries/validate-user-queries**
   - Click "Try it out"
   - Click "Execute"
   - See validation results!

---

## What You Get

**For a typical data warehouse:**
- 3 fact tables
- 5 dimension tables
- Relationships defined

**You'll get ~15-20 auto-generated queries covering:**
- ✅ Record counts for all 8 tables
- ✅ Metric aggregations for fact tables
- ✅ Fact+dimension join queries
- ✅ Monthly trend analysis
- ✅ Top 5 queries by dimension
- ✅ Complex multi-dimension joins

**All generated in ~5 seconds!**

**Time saved:** ~6-10 hours of manual SQL writing

---

## Need Help?

**View API documentation:**
```bash
open http://localhost:8000/docs
```

**Check backend logs:**
```bash
docker logs data-migration-validator-studio-backend-1
```

**View generated files:**
```bash
# Metadata
cat /Users/aravind/sourcecode/projects/data-migration-validator/ombudsman_core/data/metadata.json

# Mappings
cat /Users/aravind/sourcecode/projects/data-migration-validator/ombudsman_core/data/mapping.json

# Generated queries
cat /Users/aravind/sourcecode/projects/data-migration-validator/ombudsman_core/src/ombudsman/config/custom_queries.yaml
```

---

**That's it! You now have intelligent query suggestions working. Just follow these 6 steps and you're done!**
