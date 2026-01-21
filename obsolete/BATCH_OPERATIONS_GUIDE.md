# Batch Operations Guide

## Overview

The Batch Operations system enables you to execute multiple validation pipelines, generate data for multiple schemas, validate across projects, and extract metadata from multiple sources - all in a single coordinated batch job.

### Key Features

- **Parallel Execution**: Run multiple operations simultaneously with configurable parallelism
- **Sequential Execution**: Execute operations one after another with order guarantees
- **Error Handling**: Continue on errors or stop at the first failure
- **Real-time Progress**: Monitor job progress with live updates
- **Retry Support**: Automatically retry failed operations
- **Job History**: Track all batch jobs with detailed operation logs
- **Export Results**: Download job results in JSON format

---

## Use Cases

### 1. Bulk Pipeline Execution

Execute multiple validation pipelines in a single batch job.

**When to use:**
- Daily/weekly validation runs across all dimension and fact tables
- Regression testing after schema changes
- Scheduled validation suites
- CI/CD integration for data quality checks

**Example:**
```json
{
  "job_name": "Daily Validation Suite",
  "description": "Run all dimension and fact validations",
  "pipelines": [
    {"pipeline_id": "dim_customer_validation"},
    {"pipeline_id": "dim_product_validation"},
    {"pipeline_id": "dim_date_validation"},
    {"pipeline_id": "fact_sales_validation"}
  ],
  "parallel_execution": true,
  "max_parallel": 3,
  "stop_on_error": false,
  "project_id": "retail_migration"
}
```

### 2. Batch Data Generation

Generate sample data for multiple schemas simultaneously.

**When to use:**
- Setting up test environments
- Creating demo datasets
- Performance testing with large data volumes
- Refreshing development databases

**Example:**
```json
{
  "job_name": "Generate All Test Data",
  "description": "Create sample data for all schemas",
  "items": [
    {"schema_type": "Retail", "row_count": 10000},
    {"schema_type": "Finance", "row_count": 5000},
    {"schema_type": "Healthcare", "row_count": 8000}
  ],
  "parallel_execution": true,
  "max_parallel": 2
}
```

### 3. Multi-Project Validation

Validate across multiple projects in one batch.

**When to use:**
- Organization-wide validation reporting
- Cross-project data quality assessments
- Migration checkpoints across multiple systems
- Quarterly data quality audits

**Example:**
```json
{
  "job_name": "Quarterly Multi-Project Validation",
  "description": "Validate all active migration projects",
  "projects": [
    {
      "project_id": "retail_migration",
      "pipeline_ids": ["dim_validation", "fact_validation"]
    },
    {
      "project_id": "finance_migration",
      "pipeline_ids": ["gl_validation", "ar_validation"]
    }
  ],
  "parallel_execution": false,
  "stop_on_error": false
}
```

### 4. Bulk Metadata Extraction

Extract metadata from multiple database connections.

**When to use:**
- Initial system discovery across multiple databases
- Schema synchronization between environments
- Database inventory and cataloging
- Automated metadata refresh

**Example:**
```json
{
  "job_name": "Extract All Database Metadata",
  "description": "Pull metadata from all connected sources",
  "items": [
    {"connection_type": "sqlserver", "schema_name": "dbo"},
    {"connection_type": "sqlserver", "schema_name": "staging"},
    {"connection_type": "snowflake", "schema_name": "PUBLIC"}
  ],
  "parallel_execution": true,
  "max_parallel": 2
}
```

---

## API Endpoints

### Job Creation

#### 1. Bulk Execute Pipelines
```http
POST /batch/pipelines/bulk-execute
Content-Type: application/json

{
  "job_name": "Daily Validation",
  "pipelines": [
    {"pipeline_id": "pipeline1"},
    {"pipeline_id": "pipeline2"}
  ],
  "parallel_execution": true,
  "max_parallel": 5,
  "stop_on_error": false,
  "project_id": "my_project",
  "tags": ["daily", "automated"]
}
```

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "message": "Batch pipeline execution job created with 2 pipelines",
  "total_operations": 2
}
```

#### 2. Bulk Generate Data
```http
POST /batch/data/bulk-generate
Content-Type: application/json

{
  "job_name": "Generate Test Data",
  "items": [
    {"schema_type": "Retail", "row_count": 10000}
  ],
  "parallel_execution": true,
  "max_parallel": 2
}
```

#### 3. Multi-Project Validation
```http
POST /batch/projects/multi-validate
Content-Type: application/json

{
  "job_name": "Weekly Multi-Project Check",
  "projects": [
    {
      "project_id": "project1",
      "pipeline_ids": ["val1", "val2"]
    }
  ]
}
```

#### 4. Bulk Extract Metadata
```http
POST /batch/metadata/bulk-extract
Content-Type: application/json

{
  "job_name": "Metadata Sync",
  "items": [
    {"connection_type": "sqlserver", "schema_name": "dbo"}
  ],
  "parallel_execution": true
}
```

### Job Management

#### List Jobs
```http
GET /batch/jobs?status=running&job_type=bulk_pipeline_execution&limit=50
```

**Query Parameters:**
- `status`: Filter by status (pending, running, completed, failed, cancelled)
- `job_type`: Filter by type
- `project_id`: Filter by project
- `limit`: Results per page (default: 100, max: 500)
- `offset`: Pagination offset

**Response:**
```json
{
  "jobs": [...],
  "total": 150,
  "page": 1,
  "page_size": 50
}
```

#### Get Job Details
```http
GET /batch/jobs/{job_id}
```

**Response:**
```json
{
  "job": {
    "job_id": "550e8400-e29b-41d4-a716-446655440000",
    "job_type": "bulk_pipeline_execution",
    "status": "running",
    "name": "Daily Validation",
    "operations": [...],
    "progress": {
      "total_operations": 5,
      "completed_operations": 2,
      "failed_operations": 0,
      "skipped_operations": 0,
      "percent_complete": 40.0,
      "estimated_time_remaining_ms": 30000
    }
  },
  "current_progress": {...}
}
```

#### Cancel Job
```http
POST /batch/jobs/{job_id}/cancel
Content-Type: application/json

{
  "reason": "User cancelled - testing purposes",
  "force": false
}
```

#### Retry Failed Operations
```http
POST /batch/jobs/{job_id}/retry
Content-Type: application/json

{
  "operation_ids": null,  // null = retry all failed
  "max_retries": 3
}
```

#### Delete Job
```http
DELETE /batch/jobs/{job_id}
```

### Monitoring

#### Get Job Progress
```http
GET /batch/jobs/{job_id}/progress
```

#### Get Operation Details
```http
GET /batch/jobs/{job_id}/operations
```

#### Get Statistics
```http
GET /batch/statistics
```

**Response:**
```json
{
  "status": "success",
  "statistics": {
    "total_jobs": 250,
    "status_distribution": {
      "running": 3,
      "completed": 200,
      "failed": 15,
      "cancelled": 5
    },
    "type_distribution": {
      "bulk_pipeline_execution": 150,
      "batch_data_generation": 50,
      "multi_project_validation": 30,
      "bulk_metadata_extraction": 20
    },
    "active_jobs": 3,
    "recent_jobs": [...]
  }
}
```

---

## Frontend Usage

### Accessing Batch Operations

1. Navigate to the Batch Operations page via the route `/batch`
2. Select from 4 available tabs:
   - Bulk Pipeline Execution
   - Batch Data Generation
   - Active Jobs
   - Job History

### Bulk Pipeline Execution Tab

**Steps:**
1. Enter a descriptive job name
2. Select pipelines using checkboxes
3. Choose execution mode:
   - **Parallel**: Execute multiple pipelines simultaneously
   - **Sequential**: Execute one after another
4. If parallel, set max parallel workers (1-10)
5. Optionally enable "Stop on First Error"
6. Click "Execute Pipelines"

**UI Features:**
- Real-time pipeline selection
- Visual feedback for execution mode
- Clear indication of selected pipelines

### Batch Data Generation Tab

**Steps:**
1. Enter a job name
2. Select schemas (Retail, Finance, Healthcare)
3. Set row count per schema
4. Choose parallel execution option
5. Click "Generate Data"

**UI Features:**
- Multi-schema selection
- Configurable row counts
- Parallel execution toggle

### Active Jobs Tab

**Features:**
- Real-time job monitoring
- Auto-refresh every 2 seconds
- Progress bars for each job
- Quick actions:
  - View Details
  - Cancel (for running jobs)
  - Retry Failed (for failed jobs)

**Columns:**
- Job Name
- Type
- Status (with colored chips)
- Progress (visual progress bar)
- Operations summary (success/total)
- Duration
- Actions

### Job History Tab

**Features:**
- Complete job history
- Filter by status, type, date
- Export results to JSON
- Delete completed jobs

**Status Indicators:**
- 🔵 **Running**: Job is currently executing
- ✅ **Completed**: All operations succeeded
- ❌ **Failed**: All operations failed
- ⚠️ **Partial Success**: Some operations succeeded
- ⏸️ **Pending**: Job queued but not started
- 🚫 **Cancelled**: User cancelled the job

### Job Details Dialog

Click "View Details" on any job to see:
- Job metadata (ID, name, type, description)
- Overall progress with percentage
- Operation breakdown (total, completed, failed, skipped)
- Individual operation details:
  - Status
  - Duration
  - Results
  - Error messages (if failed)

### Real-time Updates

Active jobs refresh automatically every 2 seconds. The UI displays:
- Live progress bars
- Current operation being executed
- Estimated time remaining
- Operation-level status updates

---

## Best Practices

### Parallel Execution

**When to use parallel execution:**
- Operations are independent (no shared resources)
- Database can handle concurrent connections
- Faster completion is priority

**Recommended parallel limits:**
- **Small databases**: 2-3 workers
- **Medium databases**: 3-5 workers
- **Large databases**: 5-10 workers

**Considerations:**
- Monitor database CPU and memory
- Watch for connection pool exhaustion
- Consider network bandwidth

### Sequential Execution

**When to use sequential execution:**
- Operations have dependencies
- Database has limited capacity
- Specific execution order required
- Debugging and troubleshooting

### Error Handling

**Stop on Error = True:**
- Use for critical validations
- When failures invalidate subsequent operations
- During initial testing phases

**Stop on Error = False:**
- Use for comprehensive reporting
- When you want to see all failures
- In production monitoring scenarios

### Job Naming

**Good naming conventions:**
- Include date/time: "Daily Validation 2024-12-04"
- Include scope: "All Dimension Tables"
- Include environment: "Production Data Gen"
- Include purpose: "Pre-Migration Check"

**Examples:**
```
✅ "Daily Retail Validation - 2024-12-04"
✅ "Generate Test Data - Finance Schema"
✅ "Multi-Project Validation - Q4 2024"
❌ "Job 1"
❌ "Test"
```

### Monitoring and Alerts

1. **Set up notifications** for failed batch jobs
2. **Review job history** regularly
3. **Monitor execution times** for performance degradation
4. **Export results** for reporting and compliance
5. **Use tags** for organization and filtering

### Performance Optimization

1. **Batch similar operations** together
2. **Use parallel execution** when possible
3. **Tune max_parallel** based on database capacity
4. **Schedule large jobs** during off-peak hours
5. **Monitor resource usage** during execution

---

## Troubleshooting

### Job Stuck in Pending

**Causes:**
- Executor not started
- System overload
- Resource constraints

**Solutions:**
1. Check backend logs
2. Restart the backend service
3. Cancel and retry the job

### High Failure Rate

**Causes:**
- Database connection issues
- Invalid pipeline configurations
- Resource exhaustion

**Solutions:**
1. Check connection status
2. Validate pipeline YAML files
3. Reduce parallel execution
4. Review operation errors in job details

### Slow Execution

**Causes:**
- Too many parallel operations
- Database performance
- Network latency

**Solutions:**
1. Reduce max_parallel setting
2. Use sequential execution
3. Optimize database queries
4. Check network connectivity

### Jobs Not Appearing

**Causes:**
- Storage directory permissions
- Backend restart cleared memory
- Filter settings too restrictive

**Solutions:**
1. Check BATCH_JOBS_DIR permissions
2. Verify jobs are being persisted to disk
3. Clear filters in job list
4. Refresh the page

---

## Integration Examples

### Python Script Integration

```python
import requests

# Create bulk pipeline execution job
response = requests.post(
    "http://localhost:8000/batch/pipelines/bulk-execute",
    json={
        "job_name": "Automated Daily Validation",
        "pipelines": [
            {"pipeline_id": "dim_customer_validation"},
            {"pipeline_id": "fact_sales_validation"}
        ],
        "parallel_execution": True,
        "max_parallel": 3,
        "tags": ["automated", "daily"]
    }
)

job_id = response.json()["job_id"]

# Monitor progress
import time
while True:
    progress = requests.get(
        f"http://localhost:8000/batch/jobs/{job_id}/progress"
    ).json()

    if progress["job_status"] in ["completed", "failed", "cancelled"]:
        break

    print(f"Progress: {progress['progress']['percent_complete']}%")
    time.sleep(5)
```

### CURL Examples

```bash
# Create batch job
curl -X POST http://localhost:8000/batch/pipelines/bulk-execute \
  -H "Content-Type: application/json" \
  -d '{
    "job_name": "Test Validation",
    "pipelines": [{"pipeline_id": "test_pipeline"}],
    "parallel_execution": false
  }'

# Get job status
curl http://localhost:8000/batch/jobs/{job_id}

# Cancel job
curl -X POST http://localhost:8000/batch/jobs/{job_id}/cancel

# Get statistics
curl http://localhost:8000/batch/statistics
```

---

## Advanced Features

### Custom Operation Metadata

Include custom metadata in operations:

```json
{
  "job_name": "Custom Validation",
  "pipelines": [
    {
      "pipeline_id": "dim_customer",
      "config_override": {
        "threshold": 0.95,
        "sample_size": 1000
      }
    }
  ]
}
```

### Retry Strategies

Configure retry behavior:

```json
{
  "operation_ids": ["pipeline_0_dim_customer"],
  "max_retries": 3
}
```

### Tagging and Organization

Use tags for organization:

```json
{
  "job_name": "Production Validation",
  "tags": ["production", "scheduled", "high-priority"],
  "project_id": "retail_migration"
}
```

### Export Formats

Export job results:
- **JSON**: Full job data with all operations
- **CSV**: Tabular format for spreadsheet analysis

---

## Architecture

### Components

1. **Models** (`batch/models.py`):
   - Data models for jobs, operations, and requests
   - Pydantic validation
   - Type safety

2. **Job Manager** (`batch/job_manager.py`):
   - Job lifecycle management
   - Persistence to disk
   - Thread-safe operations

3. **Executor** (`batch/executor.py`):
   - Async job execution
   - Parallel/sequential coordination
   - Error handling and retries

4. **Router** (`batch/router.py`):
   - FastAPI endpoints
   - Request validation
   - Response formatting

5. **Frontend** (`BatchOperations.tsx`):
   - React components
   - Material-UI design
   - Real-time updates

### Data Flow

```
User Input → Frontend Form → API Request → Job Manager (Create Job)
                                              ↓
                                         Job Stored to Disk
                                              ↓
                                         Executor (Async)
                                              ↓
                                    Execute Operations (Parallel/Sequential)
                                              ↓
                                    Update Progress → Frontend (Real-time)
                                              ↓
                                         Job Complete
```

### Storage

Jobs are persisted to: `BATCH_JOBS_DIR` (default: `/data/batch_jobs`)

**File format:** JSON
**Naming:** `{job_id}.json`

---

## FAQ

**Q: How many jobs can run simultaneously?**
A: By default, the executor supports up to 10 concurrent workers. Each job can have its own max_parallel setting.

**Q: Are jobs persisted across restarts?**
A: Yes, jobs are saved to disk and reloaded on startup.

**Q: Can I schedule batch jobs?**
A: Not directly. Use external schedulers (cron, Airflow) to call the API endpoints.

**Q: What happens if a job is cancelled mid-execution?**
A: Running operations complete, but pending operations are marked as skipped.

**Q: Can I modify a running job?**
A: No. You must cancel and create a new job.

**Q: How long are jobs retained?**
A: Jobs are retained indefinitely unless manually deleted.

---

## Support

For issues, questions, or feature requests:
- Review the API documentation at `/docs`
- Check backend logs for errors
- Verify database connections
- Contact support@pluralinsight.com
