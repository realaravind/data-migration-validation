# Visual Step-by-Step Guide - Intelligent Query Suggestions

## Open This URL First: http://localhost:8000/docs

You'll see the Swagger UI with all API endpoints.

---

## STEP 1: Extract Metadata

### Find This Section:
```
▼ Metadata
```

### Click On:
```
POST /metadata/extract
Extract metadata from both SQL Server and Snowflake
```

### Then:
1. Click **"Try it out"** button
2. You'll see a text box with example JSON
3. **Replace** the JSON with this:
```json
{
  "sql_database": "SampleDW",
  "sql_schemas": ["DIM", "FACT"],
  "snowflake_database": "SAMPLEDW",
  "snowflake_schemas": ["DIM", "FACT"]
}
```
4. Click **"Execute"** button
5. Wait 30-60 seconds
6. You'll see **green 200** response with "success"

✅ **Done with Step 1**

---

## STEP 2: Generate Mappings

### Find This Section:
```
▼ Mapping
```

### Click On:
```
POST /mapping/suggest
Generate intelligent mapping suggestions
```

### Then:
1. Click **"Try it out"** button
2. Click **"Execute"** button (no input needed!)
3. Wait 10-20 seconds
4. You'll see **green 200** response

✅ **Done with Step 2**

---

## STEP 3: Generate Intelligent Queries (THE MAGIC!)

### Find This Section:
```
▼ Custom Business Queries
```

### Click On:
```
POST /custom-queries/save-suggestions
Save intelligently generated suggestions directly to custom_queries.yaml
```

### Then:
1. Click **"Try it out"** button
2. Click **"Execute"** button (no input needed!)
3. Wait 5-10 seconds
4. You'll see response like:
```json
{
  "status": "success",
  "saved_count": 15,
  "message": "Saved 15 intelligent query suggestions!"
}
```

✅ **Done! You now have 15 auto-generated queries!**

---

## STEP 4: View Your Generated Queries

### Still in "Custom Business Queries" section

### Click On:
```
GET /custom-queries/user-queries
View user-defined queries from config/custom_queries.yaml
```

### Then:
1. Click **"Try it out"** button
2. Click **"Execute"** button
3. You'll see **all your generated queries** in the response!

Example:
```json
{
  "status": "success",
  "count": 15,
  "queries": [
    {
      "name": "Record Count - fact_sales",
      "comparison_type": "count",
      "sql_query": "SELECT COUNT(*) FROM dbo.fact_sales",
      "snow_query": "SELECT COUNT(*) FROM SAMPLEDW.FACT.FACT_SALES"
    },
    {
      "name": "Total SalesAmount - fact_sales",
      "comparison_type": "aggregation",
      "sql_query": "SELECT SUM(SalesAmount), AVG(SalesAmount) FROM dbo.fact_sales"
    }
    // ... 13 more queries
  ]
}
```

✅ **Done! You can see all your queries**

---

## STEP 5: Validate All Queries

### Still in "Custom Business Queries" section

### Click On:
```
POST /custom-queries/validate-user-queries
Validate queries from config/custom_queries.yaml
```

### Then:
1. Click **"Try it out"** button
2. Click **"Execute"** button
3. Wait 30-60 seconds (it's running all 15 queries!)
4. You'll see validation results:

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
          "interpretation": "Record counts match"
        }
      }
      // ... all results
    ]
  }
}
```

✅ **Done! You've validated all queries!**

---

## What Just Happened?

You now have:
- ✅ 15-20 auto-generated validation queries
- ✅ All queries saved to `custom_queries.yaml`
- ✅ Validation results showing which passed/failed
- ✅ Detailed explain data for each query

---

## Screenshots of What You'll See

### Step 1 - Swagger UI Main Page:
```
┌─────────────────────────────────────────────┐
│ Ombudsman Validation Studio API            │
│                                             │
│ ▼ Metadata                                  │
│   POST /metadata/extract  ← CLICK HERE     │
│   GET  /metadata/list                       │
│                                             │
│ ▼ Mapping                                   │
│   POST /mapping/suggest   ← THEN CLICK HERE│
│                                             │
│ ▼ Custom Business Queries                   │
│   POST /custom-queries/save-suggestions     │
│         ↑ THEN CLICK HERE!                  │
│   GET  /custom-queries/user-queries         │
│   POST /custom-queries/validate-user-queries│
│   GET  /custom-queries/examples             │
└─────────────────────────────────────────────┘
```

### Step 2 - Clicking on an Endpoint:
```
┌─────────────────────────────────────────────┐
│ POST /custom-queries/save-suggestions       │
│                                             │
│ Save intelligently generated suggestions... │
│                                             │
│ ┌─────────────────┐                         │
│ │ Try it out      │  ← CLICK THIS FIRST    │
│ └─────────────────┘                         │
│                                             │
│ (Request body section appears)              │
│                                             │
│ ┌─────────────────┐                         │
│ │    Execute      │  ← THEN CLICK THIS     │
│ └─────────────────┘                         │
└─────────────────────────────────────────────┘
```

### Step 3 - Response:
```
┌─────────────────────────────────────────────┐
│ Response                                    │
│ Code: 200 ✓                                 │
│                                             │
│ {                                           │
│   "status": "success",                      │
│   "saved_count": 15,                        │
│   "saved_to": "...custom_queries.yaml",     │
│   "message": "Saved 15 suggestions!"        │
│ }                                           │
└─────────────────────────────────────────────┘
```

---

## Common Questions

### Q: Where are my generated queries?
**A:** In this file:
```
ombudsman_core/src/ombudsman/config/custom_queries.yaml
```

View it:
```bash
cat ombudsman_core/src/ombudsman/config/custom_queries.yaml
```

---

### Q: How do I edit them?
**A:** Just open the file:
```bash
nano ombudsman_core/src/ombudsman/config/custom_queries.yaml
```

Edit any query, save, then re-validate using Swagger UI.

---

### Q: What if I want to add WHERE clauses?
**A:** Edit the file, example:
```yaml
- name: "Total Sales 2023"
  comparison_type: "aggregation"
  sql_query: |
    SELECT SUM(Amount)
    FROM dbo.fact_sales
    WHERE Year = 2023  ← ADD THIS
```

Save and re-validate.

---

### Q: Can I delete queries I don't need?
**A:** Yes! Just delete them from the YAML file.

---

### Q: How do I regenerate from scratch?
**A:** In Swagger UI:
```
POST /custom-queries/save-suggestions
```
Click Execute again. It will overwrite with fresh suggestions.

---

## That's It!

**Bookmark this URL:** http://localhost:8000/docs

**Follow these 5 clicks:**
1. POST `/metadata/extract` → Try it out → Execute
2. POST `/mapping/suggest` → Try it out → Execute
3. POST `/custom-queries/save-suggestions` → Try it out → Execute
4. GET `/custom-queries/user-queries` → Try it out → Execute (view them)
5. POST `/custom-queries/validate-user-queries` → Try it out → Execute (validate)

**Done!** You have intelligent query suggestions working.

---

## Video Walkthrough (If You Prefer)

If you want, I can create a bash script that opens the browser and shows you exactly where to click:

```bash
# This will open the Swagger UI
open http://localhost:8000/docs
```

Then just follow the steps above!
