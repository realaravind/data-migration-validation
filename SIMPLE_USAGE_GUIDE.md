# Simple Usage Guide - Intelligent Query Suggestions in Pipeline Creation

## The Easy Way (What You Asked For!)

Instead of using command line or Swagger UI, you can now use intelligent query suggestions **directly in the web interface** when creating pipelines.

## How It Works

### Step 1: Extract Metadata (One Time Setup)

Go to the web UI and extract your metadata first:

1. Open: http://localhost:3000
2. Click **"Metadata Extraction"** tab
3. Fill in your database details
4. Click **"Extract Metadata"**

This discovers all your tables, columns, and relationships.

**You only need to do this once!**

---

### Step 2: Create Pipeline with Suggested Queries

When you create a validation pipeline, the system will automatically suggest queries based on your metadata.

#### In the Pipeline Creation Page:

1. Go to **"Pipeline Execution"** tab
2. Click **"Suggest Custom Queries"** button (with sparkle icon ✨)
3. A dialog appears showing all intelligent suggestions:

```
┌────────────────────────────────────────────────────┐
│  ✨ Intelligent Query Suggestions                  │
│                                                     │
│  15 queries generated from your metadata           │
│  8 selected (HIGH priority auto-selected)          │
│                                                     │
│  ┌─────────────────────────────────────┐           │
│  │ Select All  │ HIGH Only │ Clear     │           │
│  └─────────────────────────────────────┘           │
│                                                     │
│  ▼ Basic Validation (3 queries)                    │
│    ☑ Record Count - fact_sales         [HIGH]     │
│    ☑ Record Count - dim_customer       [HIGH]     │
│    ☑ Record Count - dim_product        [HIGH]     │
│                                                     │
│  ▼ Metric Validation (5 queries)                   │
│    ☑ Total SalesAmount - fact_sales    [HIGH]     │
│    ☐ Average Quantity - fact_sales     [MEDIUM]   │
│    ...                                              │
│                                                     │
│  ▼ Join Validation (3 queries)                     │
│    ☐ fact_sales by dim_customer        [MEDIUM]   │
│    ...                                              │
│                                                     │
│  ▼ Time-Based Validation (2 queries)               │
│    ☑ Monthly Trend - fact_sales        [HIGH]     │
│    ...                                              │
│                                                     │
│  [Cancel]  [Add 8 Queries to Validations]          │
└────────────────────────────────────────────────────┘
```

4. **Check/uncheck** the queries you want
5. Click **"Add X Queries to Validations"**
6. The queries are automatically added to your pipeline!

---

## What You See in the Dialog

### Queries are Organized by Category:

- **Basic Validation** - Record counts for all tables
- **Metric Validation** - SUM, AVG for numeric columns
- **Join Validation** - Fact + dimension aggregations
- **Time-Based Validation** - Monthly/yearly trends
- **Top N Validation** - Top 5 customers, products, etc.
- **Complex Join Validation** - Multi-table joins

### Each Query Shows:

- ✅ Query name
- 🏷️ Priority badge (HIGH/MEDIUM/LOW)
- 📋 Type (count, aggregation, rowset)
- 📝 Description of what it validates

### Quick Actions:

- **Select All** - Check all 15+ queries
- **HIGH Only** - Only check HIGH priority queries (recommended!)
- **Clear** - Uncheck everything

---

## Example Workflow

### Scenario: You want to validate a data migration

**Step 1:** Go to Metadata Extraction (one time)
- Extract metadata → Gets all your tables and columns

**Step 2:** Go to Pipeline Execution
- Click **"Suggest Custom Queries" button**
- Dialog shows 15 intelligent suggestions
- HIGH priority queries are already selected (8 queries)
- Click **"Add 8 Queries to Validations"**

**Step 3:** Run the Pipeline
- Click **"Execute Pipeline"**
- All 8 queries run automatically
- See results: 7 passed, 1 failed
- Click on failed query to see details

**Done!** You've validated your migration with 8 comprehensive queries in 3 clicks.

---

## What Gets Auto-Selected?

By default, **HIGH priority queries** are auto-selected:

✅ **Record Counts** - All tables (ensures no data loss)
✅ **Total Metrics** - SUM/AVG of important columns
✅ **Monthly Trends** - Time-based validation (if date dimension exists)

You can select more if needed:

☐ **MEDIUM priority** - Join validations, Top N queries
☐ **LOW priority** - Complex multi-dimension joins

---

## Benefits of This Approach

### Before (Complicated):
1. Extract metadata via API
2. Generate mappings via API
3. Create relationships YAML file
4. Call intelligent-suggest API
5. Review JSON response
6. Copy to YAML file
7. Create pipeline manually

### After (Simple):
1. Extract metadata (one time, in UI)
2. Click "Suggest Queries" button
3. Select queries you want
4. Click "Add to Validations"

**Done!** 7 steps reduced to 2 clicks.

---

## The Dialog Remembers Your Metadata

Once you've extracted metadata, the "Suggest Queries" button:
- ✅ Always works (metadata is already loaded)
- ✅ Generates fresh suggestions based on current metadata
- ✅ Updates when you add new tables or relationships
- ✅ No need to run commands or use Swagger UI

---

## What If I Want Different Queries?

### Option 1: Select/Deselect in the Dialog
Just check or uncheck queries before clicking "Add to Validations"

### Option 2: Edit After Adding
After adding queries to your pipeline:
1. Go to pipeline YAML file
2. Edit the queries (add WHERE clauses, change tolerance, etc.)
3. Save
4. Re-run pipeline

### Option 3: Add Custom Queries Manually
You can always add your own custom queries:
1. Edit the pipeline YAML
2. Add a new query with your custom SQL
3. Save and run

---

## Behind the Scenes

When you click "Suggest Queries":

1. System loads your metadata (from previous extraction)
2. Analyzes:
   - Table types (fact vs dimension)
   - Numeric columns (for aggregations)
   - Relationships (for joins)
   - Date dimensions (for trends)
3. Generates 15-20 intelligent queries
4. Categorizes by type and priority
5. Auto-selects HIGH priority
6. Shows in dialog for you to review

All of this happens in **~2 seconds**!

---

## Quick Reference

| Action | What It Does |
|--------|--------------|
| **Suggest Queries button** | Opens dialog with intelligent suggestions |
| **Select All** | Check all suggested queries |
| **HIGH Only** | Check only HIGH priority queries (recommended) |
| **Clear** | Uncheck all queries |
| **Add to Validations** | Adds selected queries to your pipeline |

---

## Example: Real Use Case

You're migrating data from SQL Server to Snowflake with:
- 3 fact tables (Sales, Orders, Inventory)
- 5 dimension tables (Customer, Product, Date, Store, Employee)

**Without Intelligent Suggestions:**
- Manually write 20+ SQL queries
- Test each one
- Time: ~8 hours

**With Intelligent Suggestions:**
- Click "Suggest Queries"
- Select queries you want
- Add to pipeline
- Time: ~5 minutes

**Time saved: ~8 hours per project** ⏰

---

## Troubleshooting

### Problem: "Suggest Queries" button is disabled

**Solution:** Extract metadata first
1. Go to Metadata Extraction tab
2. Fill in database details
3. Click "Extract Metadata"
4. Wait for completion
5. Go back to Pipeline Execution
6. "Suggest Queries" button is now enabled

---

### Problem: Dialog shows "No metadata found"

**Solution:** Check metadata was extracted successfully
1. Open: http://localhost:8000/docs
2. Find: GET `/metadata/list`
3. Click "Try it out" → "Execute"
4. If empty, run metadata extraction again

---

### Problem: Only record count queries are suggested

**Solution:** Add relationship definitions
1. Go to Database Mapping tab
2. Click "Infer Relationships"
3. Review and save relationships
4. Click "Suggest Queries" again
5. Now you'll see join queries and time-based queries

---

## Next Steps

1. **Extract metadata** (if you haven't already)
   - Go to Metadata Extraction tab
   - Click "Extract Metadata"

2. **Try it!**
   - Go to Pipeline Execution tab
   - Click "Suggest Custom Queries"
   - Select queries
   - Click "Add to Validations"

3. **Run and see results**
   - Execute pipeline
   - View validation results

**That's it!** Much simpler than using API endpoints directly.

---

## Technical Note

This uses the same intelligent suggestion engine we built, but makes it accessible through a clean UI instead of requiring API calls. Behind the scenes:

```
UI Button Click
    ↓
Fetch /custom-queries/intelligent-suggest
    ↓
Analyze metadata + mappings + relationships
    ↓
Generate 15-20 queries
    ↓
Display in dialog
    ↓
User selects queries
    ↓
Add to pipeline configuration
    ↓
Ready to execute!
```

All the complexity is hidden. You just click buttons! 🎉
