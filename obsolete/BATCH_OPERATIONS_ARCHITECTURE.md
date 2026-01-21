# Batch Operations System - Architecture

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         FRONTEND (React + TypeScript)                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │              BatchOperations.tsx Component                    │  │
│  │                                                               │  │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌──────────┐ │  │
│  │  │ Tab 1:     │ │ Tab 2:     │ │ Tab 3:     │ │ Tab 4:   │ │  │
│  │  │ Bulk       │ │ Batch Data │ │ Active     │ │ Job      │ │  │
│  │  │ Pipeline   │ │ Generation │ │ Jobs       │ │ History  │ │  │
│  │  │ Execution  │ │            │ │ (DataGrid) │ │(DataGrid)│ │  │
│  │  └────────────┘ └────────────┘ └────────────┘ └──────────┘ │  │
│  │                                                               │  │
│  │  Auto-Refresh Timer (2 seconds) ──────────────────────┐     │  │
│  │                                                        │     │  │
│  └────────────────────────────────────────────────────────│─────┘  │
│                                                           │         │
│                                                           ▼         │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    API Client Layer                          │  │
│  │  • POST /batch/pipelines/bulk-execute                        │  │
│  │  • POST /batch/data/bulk-generate                            │  │
│  │  • GET  /batch/jobs                                          │  │
│  │  • GET  /batch/jobs/{job_id}/progress                        │  │
│  │  • POST /batch/jobs/{job_id}/cancel                          │  │
│  └──────────────────────────────────────────────────────────────┘  │
└───────────────────────────────────┬─────────────────────────────────┘
                                    │
                                    │ HTTP/REST API
                                    │
┌───────────────────────────────────▼─────────────────────────────────┐
│                      BACKEND (FastAPI + Python)                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    batch/router.py                            │  │
│  │                   (FastAPI Router)                            │  │
│  │                                                               │  │
│  │  • Endpoint handlers                                         │  │
│  │  • Request validation (Pydantic)                             │  │
│  │  • Response formatting                                       │  │
│  │  • Error handling (HTTPException)                            │  │
│  └────────────────────────┬──────────────────────────────────────┘  │
│                           │                                          │
│                           ▼                                          │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                 batch/job_manager.py                          │  │
│  │                 (Singleton Manager)                           │  │
│  │                                                               │  │
│  │  • create_job()      ──────────────┐                         │  │
│  │  • get_job()                       │                         │  │
│  │  • update_job()                    │                         │  │
│  │  • list_jobs()                     │                         │  │
│  │  • cancel_job()                    │                         │  │
│  │  • delete_job()                    │                         │  │
│  │                                    │                         │  │
│  │  Thread Lock (Thread Safety)       │                         │  │
│  │                                    │                         │  │
│  └────────────────────────────────────┼──────────────────────────┘  │
│                                       │                             │
│                                       ▼                             │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                  Persistent Storage                           │  │
│  │              /data/batch_jobs/*.json                          │  │
│  │                                                               │  │
│  │  • Job state persisted to disk                               │  │
│  │  • Auto-load on startup                                      │  │
│  │  • JSON format                                               │  │
│  │  • File per job: {job_id}.json                               │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                 batch/executor.py                             │  │
│  │              (Async Job Executor)                             │  │
│  │                                                               │  │
│  │  execute_job_async(job_id)                                   │  │
│  │         │                                                     │  │
│  │         ▼                                                     │  │
│  │  ┌─────────────────────┐                                     │  │
│  │  │ Background Thread   │                                     │  │
│  │  │  _execute_job()     │                                     │  │
│  │  └──────────┬──────────┘                                     │  │
│  │             │                                                 │  │
│  │             ▼                                                 │  │
│  │  ┌─────────────────────────────────────────────┐            │  │
│  │  │  Execution Strategy Selector                │            │  │
│  │  │  • BULK_PIPELINE_EXECUTION                  │            │  │
│  │  │  • BATCH_DATA_GENERATION                    │            │  │
│  │  │  • MULTI_PROJECT_VALIDATION                 │            │  │
│  │  │  • BULK_METADATA_EXTRACTION                 │            │  │
│  │  └──────────┬──────────────────────────────────┘            │  │
│  │             │                                                 │  │
│  │             ▼                                                 │  │
│  │  ┌─────────────────────┬─────────────────────┐              │  │
│  │  │  Parallel Mode      │  Sequential Mode    │              │  │
│  │  │  (ThreadPoolExecutor│  (for loop)         │              │  │
│  │  │   with max_workers) │                     │              │  │
│  │  └──────────┬──────────┴──────────┬──────────┘              │  │
│  │             │                     │                          │  │
│  │             ▼                     ▼                          │  │
│  │  ┌──────────────────────────────────────────┐               │  │
│  │  │      Operation Executors                 │               │  │
│  │  │  • _execute_pipeline_operation()         │               │  │
│  │  │  • _execute_data_gen_operation()         │               │  │
│  │  │  • _execute_metadata_operation()         │               │  │
│  │  │  • _execute_project_operation()          │               │  │
│  │  └────────────────┬─────────────────────────┘               │  │
│  │                   │                                          │  │
│  │                   ▼                                          │  │
│  │  ┌──────────────────────────────────────────┐               │  │
│  │  │    Progress Updates (Real-time)          │               │  │
│  │  │  • update_operation_status()             │               │  │
│  │  │  • update_job_status()                   │               │  │
│  │  │  • calculate percent_complete            │               │  │
│  │  │  • estimate time_remaining               │               │  │
│  │  └──────────────────────────────────────────┘               │  │
│  │                                                               │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    batch/models.py                            │  │
│  │                  (Pydantic Models)                            │  │
│  │                                                               │  │
│  │  • BatchJob                                                  │  │
│  │  • BatchOperation                                            │  │
│  │  • BatchProgress                                             │  │
│  │  • BatchPipelineRequest                                      │  │
│  │  • BatchDataGenRequest                                       │  │
│  │  • BatchMultiProjectRequest                                  │  │
│  │  • BatchMetadataRequest                                      │  │
│  │                                                               │  │
│  │  Enums:                                                      │  │
│  │  • BatchJobStatus                                            │  │
│  │  • BatchJobType                                              │  │
│  │  • BatchOperationStatus                                      │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

## Data Flow Sequence

### 1. Job Creation Flow

```
User fills form → Submit button
                      │
                      ▼
         POST /batch/pipelines/bulk-execute
                      │
                      ▼
         router.bulk_execute_pipelines()
                      │
         ┌────────────┴────────────┐
         │                         │
         ▼                         ▼
   Create BatchOperations    Validate request
   from request data         (Pydantic)
         │                         │
         └────────────┬────────────┘
                      ▼
         batch_job_manager.create_job()
                      │
         ┌────────────┴────────────┐
         │                         │
         ▼                         ▼
   Generate job_id          Create BatchJob object
   (UUID)                   with operations
         │                         │
         └────────────┬────────────┘
                      ▼
         Save to /data/batch_jobs/{job_id}.json
                      │
                      ▼
         batch_executor.execute_job_async(job_id)
                      │
         ┌────────────┴────────────┐
         │                         │
         ▼                         ▼
   Start background         Return response
   thread                   immediately
         │                         │
         │                         ▼
         │              {
         │                "job_id": "...",
         │                "status": "queued",
         │                "total_operations": 5
         │              }
         │
         ▼
   Async execution
   continues...
```

### 2. Job Execution Flow (Parallel)

```
execute_job_async(job_id)
         │
         ▼
   Update status: RUNNING
         │
         ▼
   ThreadPoolExecutor(max_workers=max_parallel)
         │
         ▼
   ┌─────────────────────────────────────────┐
   │  Submit operations to thread pool       │
   │                                          │
   │  Thread 1: Pipeline A                   │
   │  Thread 2: Pipeline B                   │
   │  Thread 3: Pipeline C                   │
   └─────────────────────────────────────────┘
         │
         ▼
   For each operation:
         │
         ├──→ update_operation_status(RUNNING)
         │
         ├──→ Call operation executor
         │    • _execute_pipeline_operation()
         │    • Makes HTTP request to /pipelines/execute
         │
         ├──→ On success:
         │    update_operation_status(COMPLETED, result)
         │
         ├──→ On failure:
         │    update_operation_status(FAILED, error)
         │
         └──→ Update job progress
              • Calculate percent_complete
              • Estimate time_remaining
         │
         ▼
   as_completed(futures)
         │
         ├──→ Check stop_on_error
         │    If true and operation failed:
         │    Cancel remaining futures
         │
         └──→ Wait for all to complete
         │
         ▼
   Determine final status:
   • All success → COMPLETED
   • All failed → FAILED
   • Mixed → PARTIAL_SUCCESS
         │
         ▼
   update_job_status(final_status)
         │
         ▼
   Save final state to disk
```

### 3. Progress Monitoring Flow

```
Frontend Timer (every 2 seconds)
         │
         ▼
   GET /batch/jobs/{job_id}/progress
         │
         ▼
   router.get_job_progress()
         │
         ▼
   batch_job_manager.get_job(job_id)
         │
         ▼
   Return progress data:
   {
     "job_status": "running",
     "progress": {
       "total_operations": 5,
       "completed_operations": 2,
       "failed_operations": 0,
       "percent_complete": 40.0,
       "current_operation": "pipeline_2_fact_sales",
       "estimated_time_remaining_ms": 30000
     }
   }
         │
         ▼
   Frontend updates UI:
   • Progress bar: 40%
   • Status: "2 / 5 completed"
   • Current: "pipeline_2_fact_sales"
   • ETA: "30 seconds remaining"
```

### 4. Job Cancellation Flow

```
User clicks Cancel button
         │
         ▼
   POST /batch/jobs/{job_id}/cancel
         │
         ▼
   router.cancel_batch_job()
         │
         ▼
   batch_job_manager.cancel_job(job_id)
         │
         ▼
   Update job status: CANCELLED
         │
         ▼
   For each pending/running operation:
   • Set status to SKIPPED
   • Set error message
         │
         ▼
   Executor checks job status
   (in operation loop)
         │
         ▼
   If CANCELLED:
   • Stop processing new operations
   • Cancel remaining futures (parallel)
   • Exit execution loop
         │
         ▼
   Save final state
         │
         ▼
   Return success response
```

### 5. Retry Failed Operations Flow

```
User clicks Retry button
         │
         ▼
   POST /batch/jobs/{job_id}/retry
         │
         ▼
   router.retry_failed_operations()
         │
         ▼
   Get all failed operations
         │
         ▼
   For each failed operation:
   • Reset status to PENDING
   • Clear error message
   • Reset timestamps
         │
         ▼
   Update job status: QUEUED
         │
         ▼
   batch_executor.execute_job_async(job_id)
         │
         ▼
   Re-execute job
   (only PENDING operations run)
         │
         ▼
   Update progress as execution proceeds
```

## Component Interaction Matrix

```
┌─────────────────┬──────────┬───────────┬──────────┬─────────┐
│                 │ Router   │ Manager   │ Executor │ Storage │
├─────────────────┼──────────┼───────────┼──────────┼─────────┤
│ Router          │    -     │   Calls   │  Calls   │    -    │
│ Manager         │ Returns  │     -     │  Updates │  R/W    │
│ Executor        │    -     │  Updates  │    -     │    -    │
│ Storage         │    -     │    R/W    │    -     │    -    │
└─────────────────┴──────────┴───────────┴──────────┴─────────┘

Legend:
  Calls   - Direct function calls
  Returns - Data return path
  Updates - State updates
  R/W     - Read/Write operations
```

## State Transitions

```
Job States:

PENDING ──────┐
              │
              ▼
QUEUED ───────┼──────→ RUNNING ──┬──→ COMPLETED
              │                   │
              │                   ├──→ FAILED
              │                   │
              │                   ├──→ PARTIAL_SUCCESS
              │                   │
              ▼                   ▼
         CANCELLED ←──────────────┘


Operation States:

PENDING ──→ RUNNING ──┬──→ COMPLETED
                      │
                      ├──→ FAILED
                      │
                      └──→ SKIPPED (if job cancelled)
```

## Thread Safety

```
BatchJobManager (Singleton)
   │
   ├── _lock (threading.Lock)
   │     │
   │     └── Protects:
   │          • _jobs dictionary
   │          • File I/O operations
   │
   └── Operations:
        • create_job() ──→ with _lock
        • update_job() ──→ with _lock
        • delete_job() ──→ with _lock
```

## Storage Format

```
/data/batch_jobs/
  │
  ├── {job_id_1}.json
  │     └── {
  │          "job_id": "...",
  │          "status": "completed",
  │          "operations": [...],
  │          "progress": {...},
  │          ...
  │        }
  │
  ├── {job_id_2}.json
  └── {job_id_3}.json
```

## API Request/Response Flow

```
HTTP Request
     │
     ▼
FastAPI Middleware
     │
     ├── CORS
     ├── Audit Logging
     └── Error Handling
     │
     ▼
Router Endpoint
     │
     ├── Pydantic Validation
     └── Type Checking
     │
     ▼
Business Logic
     │
     ├── Job Manager
     ├── Executor
     └── Models
     │
     ▼
Response Formation
     │
     ├── Pydantic Serialization
     └── JSON Formatting
     │
     ▼
HTTP Response
```

## Technology Stack

```
Frontend:
  • React 18
  • TypeScript
  • Material-UI v5
  • DataGrid
  • React Router

Backend:
  • FastAPI
  • Pydantic v2
  • Python 3.8+
  • Threading
  • asyncio

Storage:
  • JSON files
  • File system
  • Auto-persistence

Communication:
  • REST API
  • HTTP/HTTPS
  • JSON payloads
```

## Scalability Considerations

```
Current Design:
  • Single-node operation
  • Thread-based parallelism
  • File-based storage
  • In-memory job cache

Scalability Limits:
  • Max 10 concurrent workers
  • ~1000 jobs recommended
  • Single server instance

Future Enhancements:
  • Redis for job queue
  • Celery for distributed execution
  • PostgreSQL for job storage
  • Load balancer for API
  • Kubernetes for scaling
```

## Performance Characteristics

```
Operation Times (Typical):
  • Create job: < 100ms
  • List jobs (100): < 50ms
  • Get job details: < 10ms
  • Update progress: < 20ms
  • Cancel job: < 50ms
  • Delete job: < 30ms

Throughput:
  • Sequential: 1 operation at a time
  • Parallel: Up to 10 simultaneous operations
  • API: > 1000 requests/second

Storage:
  • ~5KB per job (JSON)
  • 1000 jobs ≈ 5MB
  • Fast SSD recommended
```

## Error Handling Strategy

```
Levels:
  1. Frontend: Try-catch + Snackbar
  2. API: HTTPException
  3. Job Manager: Exception logging
  4. Executor: Operation-level error capture
  5. Storage: File I/O error handling

Error Propagation:
  Operation Error
       │
       ├── Captured in operation.error
       ├── Status set to FAILED
       └── Job continues (unless stop_on_error)
       │
       ▼
  Job Error Aggregation
       │
       └── Final status reflects all errors
```
