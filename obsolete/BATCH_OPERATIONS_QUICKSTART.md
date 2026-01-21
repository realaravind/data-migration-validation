# Batch Operations - Quick Start Guide

## Get Started in 5 Minutes

### Prerequisites
- Ombudsman Validation Studio running (Docker or local)
- Backend: `http://localhost:8000`
- Frontend: `http://localhost:3000`

---

## Step 1: Access Batch Operations

1. Open browser: `http://localhost:3000`
2. Click **"10. Batch Operations"** from landing page
3. Or navigate directly to: `http://localhost:3000/batch`

---

## Step 2: Create Your First Batch Job

### Option A: Bulk Pipeline Execution

**Use Case:** Run multiple validation pipelines at once

1. Click **"Bulk Pipeline Execution"** tab
2. Enter job name: `My First Batch Job`
3. Select pipelines:
   - ✓ `dim_customer_validation`
   - ✓ `fact_sales_validation`
4. Toggle **"Execute in Parallel"** ON
5. Set **Max Parallel** to `3`
6. Click **"Execute Pipelines"** button

**Result:** Job created and starts running immediately!

---

### Option B: Batch Data Generation

**Use Case:** Generate test data for multiple schemas

1. Click **"Batch Data Generation"** tab
2. Enter job name: `Generate Test Data`
3. Select schemas:
   - ✓ Retail
   - ✓ Finance
4. Set **Row Count**: `1000`
5. Toggle **"Generate in Parallel"** ON
6. Click **"Generate Data"** button

**Result:** Data generation begins for all selected schemas!

---

## Step 3: Monitor Progress

### Real-time Monitoring

1. Click **"Active Jobs"** tab
2. Watch real-time updates:
   - Progress bars show completion percentage
   - Status chips indicate current state
   - Operation counts update live (e.g., "2 / 5")

### Auto-Refresh
- Jobs refresh every **2 seconds** automatically
- No manual refresh needed!

---

## Step 4: View Job Details

1. In Active Jobs or Job History
2. Click **👁️ (eye icon)** next to any job
3. View detailed information:
   - Overall progress with percentage
   - Individual operation status
   - Error messages (if any)
   - Results data

---

## Step 5: Manage Jobs

### Cancel a Running Job
1. Find job in **Active Jobs** tab
2. Click **⏹️ (stop icon)**
3. Confirm cancellation
4. Job stops and marks pending ops as skipped

### Retry Failed Operations
1. Find failed job in **Job History** tab
2. Click **🔄 (refresh icon)**
3. Only failed operations run again
4. Job moves back to Active Jobs

### Delete Completed Job
1. Find job in **Job History** tab
2. Click **🗑️ (trash icon)**
3. Confirm deletion
4. Job removed from system

### Export Results
1. Click **⬇️ (download icon)** on any job
2. JSON file downloads with full job data
3. Open in text editor or analysis tool

---

## Common Usage Patterns

### Pattern 1: Daily Validation Suite

```
Job Name: "Daily Validation - 2024-12-04"
Pipelines: All dimension + fact validations
Parallel: YES
Max Parallel: 5
Stop on Error: NO
```

**Why:** Comprehensive daily check, want to see ALL issues

---

### Pattern 2: Critical Pre-Migration Check

```
Job Name: "Pre-Migration Validation - Critical"
Pipelines: Key fact tables only
Parallel: NO (sequential)
Stop on Error: YES
```

**Why:** Must pass in order, fail fast if issues found

---

### Pattern 3: Test Data Setup

```
Job Name: "Setup Development Environment"
Schemas: Retail, Finance, Healthcare
Row Count: 10000 each
Parallel: YES
```

**Why:** Quickly populate dev database with realistic data

---

## Understanding Status Indicators

| Status | Icon | Meaning | Actions Available |
|--------|------|---------|-------------------|
| 🔵 Running | ⏳ | Currently executing | Cancel, View |
| ✅ Completed | ✓ | All operations succeeded | View, Delete, Export |
| ❌ Failed | ✗ | All operations failed | Retry, View, Delete |
| ⚠️ Partial Success | ⚠ | Some succeeded, some failed | Retry, View, Delete |
| ⏸️ Pending | ⏳ | Queued, not started | Cancel, View |
| 🚫 Cancelled | ⊘ | User cancelled | View, Delete |

---

## Reading Progress Information

### Progress Bar
```
████████████░░░░░░░░ 60%
```
- **Filled portion**: Completed operations
- **Percentage**: Overall completion
- **Updates live** during execution

### Operation Summary
```
"3 / 5 completed (1 failed)"
```
- **3**: Successfully completed
- **5**: Total operations
- **1 failed**: Number of failures

### Duration Display
```
"2m 30s"
```
- Shows elapsed time
- Updates in real-time
- Helps estimate future runs

---

## API Quick Reference

### Create Bulk Pipeline Job
```bash
curl -X POST http://localhost:8000/batch/pipelines/bulk-execute \
  -H "Content-Type: application/json" \
  -d '{
    "job_name": "My Job",
    "pipelines": [
      {"pipeline_id": "dim_customer_validation"}
    ],
    "parallel_execution": true,
    "max_parallel": 3
  }'
```

### Get Job Status
```bash
curl http://localhost:8000/batch/jobs/{job_id}
```

### List All Jobs
```bash
curl http://localhost:8000/batch/jobs?limit=50
```

### Cancel Job
```bash
curl -X POST http://localhost:8000/batch/jobs/{job_id}/cancel
```

### Get Statistics
```bash
curl http://localhost:8000/batch/statistics
```

---

## Tips & Best Practices

### 🎯 Tip 1: Use Descriptive Names
```
✅ Good: "Daily Retail Validation - 2024-12-04"
❌ Bad:  "Job 1"
```

### 🎯 Tip 2: Start with Parallel Execution
- Faster completion
- Better resource utilization
- Reduce to 2-3 if database struggles

### 🎯 Tip 3: Use Stop on Error for Critical Jobs
- Pre-production validations
- Migration go/no-go checks
- Quality gates

### 🎯 Tip 4: Continue on Error for Reporting
- Daily monitoring
- Comprehensive testing
- Issue identification

### 🎯 Tip 5: Export Results Regularly
- Keep historical records
- Trend analysis
- Compliance documentation

---

## Troubleshooting

### Job Stuck in Pending?
**Solution:**
1. Check backend logs
2. Restart backend service
3. Verify database connections

### All Operations Failing?
**Solution:**
1. Click "View Details" on failed job
2. Read error messages
3. Check database connection status
4. Verify pipeline configurations

### Progress Not Updating?
**Solution:**
1. Check browser console for errors
2. Verify API is accessible
3. Manually click "Refresh" button
4. Reload page

### Can't Cancel Job?
**Solution:**
1. Job may already be completing
2. Refresh the page
3. Check job status in backend logs

---

## Next Steps

### Explore Advanced Features
1. **Multi-Project Validation**: Validate across multiple projects
2. **Bulk Metadata Extraction**: Extract from multiple sources
3. **Job History Analysis**: Review past executions
4. **Statistics Dashboard**: View aggregate metrics

### Read Full Documentation
- **Complete Guide**: `BATCH_OPERATIONS_GUIDE.md`
- **Architecture**: `BATCH_OPERATIONS_ARCHITECTURE.md`
- **API Docs**: `http://localhost:8000/docs`

### Integrate with Automation
- Use API endpoints in scripts
- Schedule with cron/Airflow
- Build custom dashboards
- Export to BI tools

---

## Example Workflows

### Workflow 1: Morning Data Quality Check
```
8:00 AM - Create batch job:
  • All dimension validations
  • All fact validations
  • Parallel: 5 workers
  • Continue on error

8:10 AM - Review results:
  • Export failed operations
  • Create tickets for failures
  • Notify team
```

### Workflow 2: Weekend Test Data Refresh
```
Saturday 2:00 AM - Automated script:
  • Clear existing test data
  • Generate Retail (50K rows)
  • Generate Finance (30K rows)
  • Generate Healthcare (40K rows)
  • Parallel: 3 workers

Saturday 4:00 AM - Complete:
  • Fresh data ready
  • Monday team uses for testing
```

### Workflow 3: Release Validation
```
Pre-Release - Manual execution:
  • Create "Release 2024.12 Validation"
  • Select all critical pipelines
  • Sequential execution
  • Stop on first error

Review:
  • If all pass → Approve release
  • If any fail → Block release
  • Export results for sign-off
```

---

## Key Takeaways

✅ **Easy to Use**: Simple 4-tab interface
✅ **Real-time**: Live progress updates every 2 seconds
✅ **Flexible**: Parallel or sequential, stop on error or continue
✅ **Manageable**: Cancel, retry, delete jobs easily
✅ **Exportable**: Download results in JSON format
✅ **Reliable**: Persists jobs to disk, survives restarts

---

## Support & Resources

- **Frontend**: `http://localhost:3000/batch`
- **API Docs**: `http://localhost:8000/docs`
- **Full Guide**: `BATCH_OPERATIONS_GUIDE.md`
- **Architecture**: `BATCH_OPERATIONS_ARCHITECTURE.md`

**Questions?** Check the FAQ section in `BATCH_OPERATIONS_GUIDE.md`

---

## Ready to Start?

1. Open `http://localhost:3000/batch`
2. Click "Bulk Pipeline Execution" tab
3. Create your first batch job!

**Happy Validating! 🚀**
