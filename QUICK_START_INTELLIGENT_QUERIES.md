# Intelligent Query Suggestions - Quick Start (5 Minutes)

## The Simplest Way to Use It

### Option 1: Using Swagger UI (No Command Line Needed!)

**Just follow these 6 clicks:**

1. **Open your browser:** http://localhost:8000/docs

2. **Find "Metadata" section**
   - Click POST `/metadata/extract`
   - Click "Try it out"
   - Paste this in Request body:
   ```json
   {
     "sql_database": "SampleDW",
     "sql_schemas": ["DIM", "FACT"],
     "snowflake_database": "SAMPLEDW",
     "snowflake_schemas": ["DIM", "FACT"]
   }
   ```
   - Click "Execute"
   - ✅ Wait for green response

3. **Find "Mapping" section**
   - Click POST `/mapping/suggest`
   - Click "Try it out"
   - Click "Execute"
   - ✅ Wait for green response

4. **Find "Custom Business Queries" section**
   - Click POST `/custom-queries/save-suggestions`
   - Click "Try it out"
   - Click "Execute"
   - ✅ See "saved_count": 15+ queries generated!

5. **Validate all queries**
   - Click POST `/custom-queries/validate-user-queries`
   - Click "Try it out"
   - Click "Execute"
   - ✅ See validation results!

6. **Done!** You now have 15+ validated business queries.

---

### Option 2: Copy-Paste This Script (One Command!)

Just copy and paste this entire block into your terminal:

```bash
#!/bin/bash

echo "🚀 Starting Intelligent Query Generation..."
echo ""

# Step 1: Extract metadata
echo "📊 Step 1/4: Extracting metadata from databases..."
curl -s -X POST http://localhost:8000/metadata/extract \
  -H "Content-Type: application/json" \
  -d '{
    "sql_database": "SampleDW",
    "sql_schemas": ["DIM", "FACT"],
    "snowflake_database": "SAMPLEDW",
    "snowflake_schemas": ["DIM", "FACT"]
  }' > /tmp/metadata_result.json

if grep -q "success" /tmp/metadata_result.json; then
    echo "   ✅ Metadata extracted successfully"
else
    echo "   ❌ Metadata extraction failed"
    cat /tmp/metadata_result.json
    exit 1
fi

sleep 2

# Step 2: Generate mappings
echo "🔗 Step 2/4: Generating table mappings..."
curl -s -X POST http://localhost:8000/mapping/suggest > /tmp/mapping_result.json

if grep -q "success" /tmp/mapping_result.json; then
    echo "   ✅ Mappings generated successfully"
else
    echo "   ❌ Mapping generation failed"
    cat /tmp/mapping_result.json
    exit 1
fi

sleep 2

# Step 3: Generate intelligent suggestions
echo "🧠 Step 3/4: Generating intelligent query suggestions..."
curl -s -X POST http://localhost:8000/custom-queries/save-suggestions > /tmp/suggestions_result.json

QUERY_COUNT=$(cat /tmp/suggestions_result.json | python3 -c "import sys, json; print(json.load(sys.stdin).get('saved_count', 0))" 2>/dev/null || echo "0")

if [ "$QUERY_COUNT" -gt 0 ]; then
    echo "   ✅ Generated $QUERY_COUNT intelligent queries!"
else
    echo "   ❌ Query generation failed"
    cat /tmp/suggestions_result.json
    exit 1
fi

sleep 2

# Step 4: Validate queries
echo "✅ Step 4/4: Validating all queries..."
curl -s -X POST http://localhost:8000/custom-queries/validate-user-queries > /tmp/validation_result.json

VALIDATED=$(cat /tmp/validation_result.json | python3 -c "import sys, json; print(json.load(sys.stdin).get('queries_validated', 0))" 2>/dev/null || echo "0")

if [ "$VALIDATED" -gt 0 ]; then
    echo "   ✅ Validated $VALIDATED queries!"
    echo ""
    echo "📋 Validation Summary:"
    cat /tmp/validation_result.json | python3 -m json.tool | head -30
    echo ""
    echo "🎉 Success! Your intelligent queries are ready!"
    echo ""
    echo "📁 Queries saved to:"
    echo "   ombudsman_core/src/ombudsman/config/custom_queries.yaml"
    echo ""
    echo "🔍 View full results:"
    echo "   http://localhost:8000/docs → GET /custom-queries/user-queries"
else
    echo "   ❌ Validation failed"
    cat /tmp/validation_result.json
fi
```

---

## What Just Happened?

After running either option above, you now have:

✅ **15-20 auto-generated SQL queries** saved to:
   - `ombudsman_core/src/ombudsman/config/custom_queries.yaml`

✅ **Queries include:**
   - Record count validations (all tables)
   - Metric aggregations (SUM, AVG)
   - Join queries (fact + dimension)
   - Time-based analytics (monthly trends)
   - Top N queries (top 5 customers, products, etc.)
   - Multi-dimension joins

✅ **All queries validated** against both:
   - SQL Server
   - Snowflake

✅ **Results show:**
   - Which queries passed
   - Which queries failed
   - Exact differences when they fail

---

## View Your Queries

**Method 1: In the Web UI**
```bash
open http://localhost:8000/docs
# Find: GET /custom-queries/user-queries
# Click: Try it out → Execute
```

**Method 2: Command Line**
```bash
curl http://localhost:8000/custom-queries/user-queries | python3 -m json.tool
```

**Method 3: Open the File**
```bash
cat ombudsman_core/src/ombudsman/config/custom_queries.yaml
```

---

## What If I Want to Customize?

After auto-generation, just edit the file:

```bash
nano ombudsman_core/src/ombudsman/config/custom_queries.yaml
```

**Common customizations:**

1. **Add a WHERE clause:**
```yaml
sql_query: |
  SELECT SUM(Amount) FROM fact_sales
  WHERE Year = 2023
```

2. **Change tolerance (strictness):**
```yaml
tolerance: 0.001  # More strict than default 0.01
```

3. **More rows:**
```yaml
limit: 100  # Default is usually 20
```

Then re-validate:
```bash
curl -X POST http://localhost:8000/custom-queries/validate-user-queries
```

---

## What Queries Did It Create?

For a typical warehouse with:
- `fact_sales`, `fact_inventory`, `fact_orders`
- `dim_customer`, `dim_product`, `dim_date`, `dim_store`, `dim_employee`

**You'll get approximately:**

| Type | Count | Examples |
|------|-------|----------|
| Record Counts | 8 | "Record Count - fact_sales" |
| Metric Aggregations | 3-5 | "Total SalesAmount - fact_sales" |
| Join Validations | 2-3 | "fact_sales by dim_customer" |
| Time-Based | 1-2 | "Monthly Trend - fact_sales" |
| Top N | 2-3 | "Top 5 Customer" |
| Multi-Dimension | 1-2 | "fact_sales by Customer and Product" |
| **TOTAL** | **~15-20** | **All ready to use!** |

---

## Troubleshooting

### Problem: "No metadata found"

**Fix:**
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

---

### Problem: "No mapping found"

**Fix:**
```bash
curl -X POST http://localhost:8000/mapping/suggest
```

---

### Problem: Only got record count queries (no joins)

**Fix:** Create relationships file:
```bash
cat > ombudsman_core/src/ombudsman/config/relationships.yaml << 'EOF'
sales_to_customer:
  fact_table: fact_sales
  dim_table: dim_customer
  fact_key: CustomerKey
  dim_key: CustomerKey

sales_to_date:
  fact_table: fact_sales
  dim_table: dim_date
  fact_key: DateKey
  dim_key: DateKey
EOF
```

Then regenerate:
```bash
curl -X POST http://localhost:8000/custom-queries/save-suggestions
```

---

## Next Steps

1. **Review results** in Swagger UI: http://localhost:8000/docs

2. **Customize queries** if needed:
   ```bash
   nano ombudsman_core/src/ombudsman/config/custom_queries.yaml
   ```

3. **Re-validate** after changes:
   ```bash
   curl -X POST http://localhost:8000/custom-queries/validate-user-queries
   ```

4. **Use in pipelines** - Add to your validation pipelines for automated testing

---

## Full Documentation

For complete details, see:
- `HOW_TO_USE_INTELLIGENT_SUGGESTIONS.md` (comprehensive guide)
- `INTELLIGENT_SUGGESTIONS_SUMMARY.md` (technical overview)
- http://localhost:8000/docs (API documentation)

---

**That's it! You're now using intelligent query suggestions.** 🎉

**Time saved:** ~6-10 hours of manual SQL writing per project
**Queries generated:** 15-20 comprehensive validations
**Effort required:** 5 minutes to run the script above
