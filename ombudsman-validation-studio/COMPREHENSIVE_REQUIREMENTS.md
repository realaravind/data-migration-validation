# Data Migration Validation System - Comprehensive Requirements Document

## Executive Summary

This is a comprehensive data migration validation platform built with Python (FastAPI backend), React/TypeScript (frontend), and a modular validation engine (ombudsman_core). The system validates data migrations between SQL Server and Snowflake through intelligent pipeline execution, workload analysis, and automated rule generation.

---

## 1. SYSTEM ARCHITECTURE OVERVIEW

### 1.1 Core Components

```
┌─────────────────────────────────────────────────────────┐
│           Frontend (React/TypeScript - Vite)             │
│  - Landing Page, Project Manager, Pipeline Builder      │
│  - Workload Analysis, Results Viewer, Database Mapping   │
├─────────────────────────────────────────────────────────┤
│         Backend API (FastAPI - Python)                  │
│  ┌──────────────────────────────────────────────────┐   │
│  │ API Routers (20+ routers):                       │   │
│  │ - Projects, Pipelines, Batch Operations          │   │
│  │ - Metadata Extraction, Mapping Suggestions       │   │
│  │ - Workload Analysis, Results Management          │   │
│  │ - Authentication, Audit Logging                  │   │
│  │ - WebSocket Real-time Updates                    │   │
│  └──────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────┐   │
│  │ Core Services Layer:                             │   │
│  │ - Project Context & Management                   │   │
│  │ - Batch Job Execution                            │   │
│  │ - Audit Logging & Event Tracking                 │   │
│  │ - WebSocket Connection Management                │   │
│  │ - Custom Query Validation                        │   │
│  └──────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────┤
│    Ombudsman Core (Modular Validation Engine)            │
│  - MetadataLoader, MappingLoader                        │
│  - ValidationRegistry (30+ validators)                  │
│  - PipelineRunner, StepExecutor                         │
│  - Connection Managers (SQL, Snowflake)                 │
├─────────────────────────────────────────────────────────┤
│          Data Layer (File System + Database)             │
│  - File Storage: /data/projects, /data/results, etc.    │
│  - SQLite/SQL Server: Audit logs, Results Persistence   │
├─────────────────────────────────────────────────────────┤
│        External Data Sources                             │
│  - SQL Server (Source System)                           │
│  - Snowflake (Target System)                            │
└─────────────────────────────────────────────────────────┘
```

### 1.2 Technology Stack

**Backend:**
- Framework: FastAPI 0.109.0
- Server: Uvicorn
- ORM/Validation: SQLAlchemy 2.0, Pydantic 2.5
- Database Drivers: pyodbc (SQL Server), snowflake-connector-python
- Support: FastAPI-CORS, Python-Jose (Auth), Passlib (Hashing)

**Frontend:**
- Framework: React 18+ with TypeScript
- Build Tool: Vite
- Charts: Victory for data visualization
- UI: React components with custom styling

**Core Engine:**
- Base Language: Python 3.x
- Validator Framework: Registry-based (30+ validators)
- SQL Tools: sqlparse for query analysis
- Data Processing: Pandas, NumPy, Scipy

**Data Storage:**
- File System: YAML (configs), JSON (data)
- Optional Database: SQLite or SQL Server for audit logs and results

### 1.3 Component Interactions

```
Frontend (React/TypeScript)
    ↓ (HTTP REST API calls)
FastAPI Backend
    ├─→ Project Manager (reads/writes to /data/projects)
    ├─→ Pipeline Executor (delegates to Ombudsman Core)
    ├─→ Batch Manager (orchestrates parallel execution)
    ├─→ Workload Analyzer (parses queries)
    ├─→ Audit Logger (logs to /data/audit_logs)
    └─→ Database Repository (optional: SQLite/SQL Server)
        ↓
    Ombudsman Core Engine
        ├─→ Metadata Extraction (reads schemas)
        ├─→ Validation Execution (30+ validators)
        ├─→ Connection Management (SQL Server, Snowflake)
        └─→ Result Aggregation
        ↓
    SQL Server & Snowflake Databases
        (Read metadata, execute queries, compare results)
```

---

## 2. CURRENT FILE SYSTEM STORAGE

### 2.1 Storage Structure

```
/data/
├── projects/                      # Project workspaces
│   ├── {project_id}/
│   │   ├── project.json          # Project metadata
│   │   ├── config/               # Configuration files
│   │   │   ├── tables.yaml       # Table definitions
│   │   │   ├── column_mappings.yaml
│   │   │   ├── schema_mappings.yaml
│   │   │   ├── relationships.yaml
│   │   │   ├── sql_relationships.yaml
│   │   │   └── snow_relationships.yaml
│   │   └── pipelines/            # Generated pipelines
│   │       ├── {pipeline_name}.yaml
│   │       └── {pipeline_name}.meta.json
│   └── {project_id}/...
│
├── results/                      # Pipeline execution results
│   ├── run_{timestamp}.json      # Individual run results
│   └── ...
│
├── batch_jobs/                   # Batch operation tracking
│   ├── batch_{job_id}.json      # Batch job metadata
│   └── ...
│
├── audit_logs/                   # Audit trail
│   ├── audit_{date}.json        # Daily audit logs
│   └── ...
│
├── workloads/                    # Uploaded workload files
│   ├── {project_id}/
│   │   ├── workload_{id}.json
│   │   └── ...
│   └── ...
│
├── pipelines/                    # Global pipeline templates
│   ├── defaults/                 # Default templates
│   ├── templates/                # Custom templates
│   └── {pipeline_name}.yaml
│
├── auth/                         # Authentication data
│   ├── users.db                 # User database
│   └── ...
│
├── query_history/               # Query execution history
│   ├── {project_id}/
│   │   └── history.json
│   └── ...
│
├── batch_templates/             # Batch operation templates
│   └── {template_name}.yaml
│
└── active_project.txt           # Current active project ID
```

### 2.2 File Types and Formats

| File Type | Format | Purpose | Example Location |
|-----------|--------|---------|-------------------|
| Project Metadata | JSON | Project definition, schemas, DB mappings | `/data/projects/{id}/project.json` |
| Tables Definition | YAML | All tables in project with columns | `/data/projects/{id}/config/tables.yaml` |
| Column Mappings | YAML | Source→Target column mappings | `/data/projects/{id}/config/column_mappings.yaml` |
| Relationships | YAML | FK relationships between tables | `/data/projects/{id}/config/relationships.yaml` |
| Pipelines | YAML | Validation steps and queries | `/data/projects/{id}/pipelines/*.yaml` |
| Pipeline Metadata | JSON | Pipeline description, tags, timestamps | `/data/projects/{id}/pipelines/*.meta.json` |
| Results | JSON | Execution results with metrics | `/data/results/run_{timestamp}.json` |
| Batch Jobs | JSON | Batch operation details & progress | `/data/batch_jobs/batch_{id}.json` |
| Audit Logs | JSON | Audit trail of all operations | `/data/audit_logs/audit_{date}.json` |
| Workloads | JSON | Query store workload data | `/data/workloads/{project_id}/workload_{id}.json` |

### 2.3 Key Data Directories

**Projects Directory** (`/data/projects/{project_id}/`)
- Stores all project-specific configurations
- Contains pipelines, relationships, and table mappings
- Each project is isolated in its own directory

**Results Directory** (`/data/results/`)
- Stores all pipeline execution results
- Files named with execution timestamp
- Results retention: 7 days (automatic cleanup)

**Batch Jobs Directory** (`/data/batch_jobs/`)
- Tracks multi-pipeline execution batches
- Stores job metadata and progress
- One file per batch operation

**Audit Logs Directory** (`/data/audit_logs/`)
- Daily audit log files for compliance
- Tracks all system operations with timestamps
- 30+ day retention (configurable)

---

## 3. KEY FEATURES AND FUNCTIONALITY

### 3.1 Core Features

#### A. Project Management
- **Create Projects**: Define projects with SQL Server and Snowflake databases
- **Auto Schema Mapping**: Intelligently map SQL Server schemas to Snowflake schemas
- **Multi-Schema Support**: Handle multiple schemas per project
- **Project Lifecycle**: Create, load, save, delete with cascade cleanup
- **Azure DevOps Integration**: Optional bug tracking integration

**Key Endpoints:**
- `POST /projects/create` - Create new project
- `GET /projects/list` - List all projects
- `GET /projects/{id}` - Load and activate project
- `DELETE /projects/{id}` - Delete with cascade cleanup
- `POST /projects/{id}/setup` - Complete auto-setup

#### B. Metadata Extraction
- **Table Metadata**: Extracts table names, columns, data types
- **Source Databases**: Works with SQL Server and Snowflake
- **Multi-Schema**: Extract from multiple schemas simultaneously
- **Column Analysis**: Identifies numeric, date, and categorical columns
- **Schema Mapping**: Maps columns between databases

**Key Endpoints:**
- `POST /metadata/extract` - Extract schemas from database
- `POST /projects/{id}/extract-metadata` - Extract for project
- `POST /projects/{id}/setup` - Full project setup

#### C. Intelligent Mapping
- **Column Matching**: AI-based fuzzy matching of column names
- **Type Compatibility**: Validates data type compatibility
- **Confidence Scoring**: Rates mapping confidence
- **Prefix Normalization**: Handles naming conventions
- **Manual Override**: Users can correct mappings

**Key Endpoints:**
- `POST /mapping/suggest` - Suggest mappings
- `POST /mapping/intelligent` - ML-based suggestions
- `PUT /projects/{id}/update-schema-mappings` - Save mappings

#### D. Pipeline Management & Execution
- **Pipeline Creation**: Generate YAML-based validation pipelines
- **Intelligent Suggestions**: AI suggests validation types based on table type
- **Custom Pipelines**: Users create custom validation rules
- **Batch Execution**: Run multiple pipelines in parallel or sequence
- **Real-time Progress**: WebSocket updates during execution
- **Results Tracking**: Store and analyze results

**Pipeline Types:**
1. **Schema Validation**: Table structure, columns, data types
2. **Data Quality**: Nulls, uniqueness, regex patterns, domain values
3. **Relationship Integrity**: FK relationships, fact-dimension conformance
4. **Statistics**: Distribution, outliers, record counts
5. **Business Rules**: Custom SQL queries, metrics
6. **Time Series**: Continuity, duplicates, rolling drift
7. **Comparative**: Row counts, column comparisons, aggregations

**Key Endpoints:**
- `POST /pipelines/execute` - Execute pipeline
- `GET /pipelines/status/{run_id}` - Check status
- `GET /pipelines/list` - List executions
- `POST /pipelines/custom/save` - Save custom pipeline
- `POST /batch/create-pipeline` - Create batch

#### E. Batch Operations
- **Bulk Execution**: Run 100+ pipelines in single batch
- **Parallel Processing**: Concurrent execution with configurable limits
- **Error Handling**: Continue on error, retry failed operations
- **Progress Tracking**: Real-time batch progress
- **Consolidated Results**: Aggregate results across pipelines

**Batch Types:**
1. Pipeline Execution (bulk)
2. Data Generation (parallel)
3. Multi-Project Validation
4. Metadata Extraction (parallel)

**Key Endpoints:**
- `POST /batch/create-pipeline` - Create pipeline batch
- `POST /batch/execute/{job_id}` - Execute batch
- `GET /batch/status/{job_id}` - Get batch status
- `GET /batch/list` - List batch jobs

#### F. Workload Analysis
- **Query Capture**: Parse SQL Server Query Store exports
- **Pattern Recognition**: Identify table usage patterns
- **Join Analysis**: Find relationships from actual queries
- **Access Patterns**: Track column usage and operators
- **Performance Metrics**: Record query execution statistics

**Key Endpoints:**
- `POST /workload/upload` - Upload Query Store JSON
- `GET /workload/list/{project_id}` - List workloads
- `GET /workload/analyze` - Analyze workload

#### G. Validation Results & Reporting
- **Result Storage**: Store pipeline execution results
- **Result History**: Track historical validation trends
- **Export Formats**: PDF, Excel, JSON
- **Quality Metrics**: Aggregated DQ scores
- **Trend Analysis**: Daily quality trends
- **Baseline Comparison**: Compare against baseline

**Key Endpoints:**
- `GET /execution/results` - Fetch results
- `GET /history` - Results history
- `GET /results/export/pdf` - Export as PDF
- `GET /results/export/excel` - Export as Excel

#### H. Real-time Updates
- **WebSocket Events**: Pipeline execution progress
- **Step Events**: Individual step completion
- **Status Updates**: Pipeline status changes
- **Error Notifications**: Real-time error alerts

**WebSocket Events:**
- `pipeline.started`
- `step.started`, `step.completed`, `step.failed`
- `pipeline.completed`, `pipeline.failed`

#### I. Authentication & Authorization
- **User Management**: Create users, assign roles
- **Role-Based Access**: Admin, User, Viewer roles
- **Token-Based Auth**: JWT tokens for API access
- **Password Security**: BCrypt hashing
- **Audit Trail**: All user actions logged

**Key Endpoints:**
- `POST /auth/register` - Create user
- `POST /auth/login` - Authenticate
- `GET /auth/me` - Current user info

#### J. Audit Logging
- **Operation Tracking**: Log all system operations
- **User Actions**: Track who did what and when
- **Data Changes**: Track data modifications
- **Compliance**: Regulatory audit trail
- **Search & Filter**: Query audit logs by date, user, action

**Key Endpoints:**
- `GET /audit/logs` - Get audit logs
- `GET /audit/stats` - Audit statistics

### 3.2 Advanced Features

#### Custom Business Queries
- **Multi-table Joins**: Support complex queries with joins
- **Date Dimensions**: Query date-based hierarchies
- **Top N Analysis**: Query top N records
- **Aggregations**: SUM, AVG, COUNT, MIN, MAX
- **Comparisons**: SQL Server vs. Snowflake results
- **Tolerance Handling**: Allow percentage variance

#### Intelligent Pipeline Suggestions
- **Table Analysis**: Analyze table schema and data
- **Fact/Dimension Detection**: Identify table type
- **Key Detection**: Find business and surrogate keys
- **Relationship Recognition**: Infer FK relationships
- **Validation Recommendation**: Suggest optimal validators
- **Query Generation**: Generate custom comparison queries

#### Database Connection Management
- **Connection Pooling**: Maintain connection pools
- **Multi-Connection**: Handle multiple databases
- **Status Monitoring**: Check connection health
- **Pool Statistics**: Track connection usage
- **Timeout Handling**: Configurable timeouts

---

## 4. DATA MODELS

### 4.1 Core Entities

#### Project
```python
{
    "project_id": "ps5",
    "name": "PlayStore 5",
    "description": "Migrate PlayStore data to Snowflake",
    "created_at": "2025-01-13T12:00:00",
    "updated_at": "2025-01-13T12:00:00",
    "sql_database": "SampleDW",
    "sql_schemas": ["dbo", "dim", "fact"],
    "snowflake_database": "SAMPLEDW",
    "snowflake_schemas": ["PUBLIC", "DIM", "FACT"],
    "schema_mappings": {"dbo": "PUBLIC", "dim": "DIM", "fact": "FACT"},
    "table_mappings_count": 50,
    "has_metadata": True,
    "has_relationships": True,
    "automation_completed": True,
    "azure_devops": {...}  # Optional
}
```

#### Pipeline Run
```python
{
    "run_id": "run_20250113_120000",
    "pipeline_name": "ps5_dim_customer_validation",
    "project_id": "ps5",
    "status": "completed",  # pending, running, completed, failed
    "started_at": "2025-01-13T12:00:00",
    "completed_at": "2025-01-13T12:05:30",
    "duration_seconds": 330,
    "total_steps": 5,
    "successful_steps": 5,
    "failed_steps": 0,
    "warnings_count": 0,
    "pipeline_def": {...},  # Full pipeline YAML as dict
    "results": [...]  # Array of step results
}
```

#### Validation Step Result
```python
{
    "name": "Schema Validation",
    "validator_type": "schema_columns",
    "status": "passed",  # passed, failed, warning
    "message": "All columns match",
    "duration_ms": 245,
    "sql_row_count": 1000000,
    "snowflake_row_count": 1000000,
    "match_percentage": 100.0,
    "difference_type": None,
    "differing_rows": 0,
    "affected_columns": [],
    "comparison_details": {...}
}
```

#### Batch Job
```python
{
    "job_id": "batch_20250113_120000",
    "job_type": "bulk_pipeline_execution",
    "status": "completed",  # pending, running, completed, failed
    "name": "PlayStore Full Validation",
    "description": "Validate all tables",
    "operations": [
        {
            "operation_id": "op_1",
            "operation_type": "pipeline_execution",
            "status": "completed",
            "pipeline_name": "ps5_dim_customer",
            "result": {...}
        }
    ],
    "progress": {
        "total_operations": 50,
        "completed_operations": 50,
        "failed_operations": 0,
        "percent_complete": 100.0
    },
    "parallel_execution": True,
    "max_parallel": 5,
    "created_at": "2025-01-13T12:00:00",
    "started_at": "2025-01-13T12:01:00",
    "completed_at": "2025-01-13T13:30:00",
    "total_duration_ms": 5400000,
    "success_count": 50,
    "failure_count": 0
}
```

#### Workload Data
```python
{
    "workload_id": "wl_20250113_001",
    "project_id": "ps5",
    "upload_date": "2025-01-13T12:00:00",
    "query_count": 250,
    "total_executions": 15000,
    "date_range": {
        "earliest": "2025-01-01",
        "latest": "2025-01-13"
    },
    "table_usage": {
        "DIM_CUSTOMER": {
            "access_count": 150,
            "join_partners": ["FACT_SALES", "DIM_STORE"],
            "columns_used": {
                "CUSTOMER_ID": {
                    "usage_types": ["where", "join"],
                    "operators": ["=", "IN"],
                    "query_count": 145
                }
            }
        }
    }
}
```

#### Audit Log Entry
```python
{
    "timestamp": "2025-01-13T12:00:00",
    "action": "pipeline_executed",
    "user": "john@example.com",
    "resource_type": "pipeline",
    "resource_id": "ps5_dim_customer_validation",
    "status": "success",
    "details": {
        "project_id": "ps5",
        "run_id": "run_20250113_120000",
        "duration_seconds": 330
    }
}
```

### 4.2 Relationships

```
Project (1) ─── (Many) Pipelines
  │
  ├─── (Many) Batch Jobs
  │
  ├─── (Many) Workloads
  │
  ├─── (Many) Validation Runs
  │     │
  │     └─── (Many) Validation Steps
  │
  └─── (Many) Audit Logs

Pipeline (1) ─── (Many) Pipeline Runs
  │
  └─── (Many) Validation Steps

Batch Job (1) ─── (Many) Operations
  │
  └─── (Many) Pipeline Runs (via operations)

Workload (1) ─── (Many) Extracted Patterns
  │
  └─── (1) Project
```

---

## 5. API ENDPOINTS

### 5.1 Project Management
```
POST   /projects/create                              Create project
GET    /projects/list                                List all projects
GET    /projects/{project_id}                        Load project
PUT    /projects/{project_id}/update-schema-mappings Update mappings
DELETE /projects/{project_id}                        Delete project
POST   /projects/{project_id}/extract-metadata       Extract metadata
POST   /projects/{project_id}/infer-relationships    Infer relationships
POST   /projects/{project_id}/setup                  Complete setup
POST   /projects/{project_id}/create-comprehensive-pipelines  Create pipelines
POST   /projects/{project_id}/automate               Automate all
GET    /projects/{project_id}/relationships          Get relationships
PUT    /projects/{project_id}/relationships          Update relationships
GET    /projects/{project_id}/status                 Get setup status
```

### 5.2 Pipeline Execution
```
POST   /pipelines/execute                            Execute pipeline
GET    /pipelines/status/{run_id}                    Get execution status
GET    /pipelines/list                               List executions
GET    /pipelines/templates                          List templates
GET    /pipelines/defaults                           List default pipelines
GET    /pipelines/defaults/{pipeline_id}             Get default pipeline
DELETE /pipelines/{run_id}                           Delete run
POST   /pipelines/custom/save                        Save custom pipeline
GET    /pipelines/custom/project/{project_id}        List project pipelines
GET    /pipelines/custom/project/{project_id}/{name} Get pipeline
DELETE /pipelines/custom/project/{project_id}/{name} Delete pipeline
```

### 5.3 Batch Operations
```
POST   /batch/create-pipeline                        Create pipeline batch
POST   /batch/execute/{job_id}                       Execute batch
GET    /batch/status/{job_id}                        Get batch status
GET    /batch/list                                   List batch jobs
POST   /batch/cancel/{job_id}                        Cancel batch
POST   /batch/retry/{job_id}                         Retry failed ops
DELETE /batch/{job_id}                               Delete batch
```

### 5.4 Results & History
```
GET    /execution/results                            Get execution results
GET    /history                                      Get results history
GET    /history/runs                                 Get all runs
GET    /history/steps/{run_id}                       Get run steps
GET    /history/trends                               Get quality trends
GET    /results/export/pdf                           Export as PDF
GET    /results/export/excel                         Export as Excel
```

### 5.5 Workload Analysis
```
POST   /workload/upload                              Upload workload
GET    /workload/list/{project_id}                   List workloads
GET    /workload/{project_id}/{workload_id}          Get workload
GET    /workload/pipelines/list                      List generated pipelines
```

### 5.6 Metadata & Mapping
```
POST   /metadata/extract                             Extract schemas
POST   /mapping/suggest                              Suggest mappings
POST   /mapping/intelligent                          ML mappings
GET    /database-mapping/sql-server                  Get SQL Server tables
GET    /database-mapping/snowflake                   Get Snowflake tables
POST   /database-mapping/create-mappings             Create mappings
```

### 5.7 Connections
```
POST   /connections/sqlserver                        Test SQL Server
POST   /connections/snowflake                        Test Snowflake
GET    /connections/status                           Connection status
GET    /connections/pool-stats                       Pool statistics
```

### 5.8 Authentication
```
POST   /auth/register                                Register user
POST   /auth/login                                   Login
GET    /auth/me                                      Current user
POST   /auth/logout                                  Logout
POST   /auth/refresh                                 Refresh token
```

### 5.9 Audit Logging
```
GET    /audit/logs                                   Get audit logs
GET    /audit/stats                                  Audit statistics
POST   /audit/export                                 Export audit logs
```

### 5.10 Notifications
```
GET    /notifications                                Get notifications
POST   /notifications/subscribe                      Subscribe
DELETE /notifications/{id}                           Dismiss notification
```

### 5.11 WebSocket
```
WS     /ws/pipelines/{run_id}                        Pipeline updates
```

---

## 6. DATABASE MIGRATION STRATEGY (Key Consideration)

### 6.1 Current State (File-Based)
- Projects: `/data/projects/{id}/project.json`
- Results: `/data/results/{run_id}.json`
- Batch Jobs: `/data/batch_jobs/batch_{id}.json`
- Audit Logs: `/data/audit_logs/audit_{date}.json`

### 6.2 Database Schema Requirements

**Tables to Create:**

1. **projects** - Project metadata
2. **pipeline_runs** - Execution records
3. **validation_steps** - Step results (FK to pipeline_runs)
4. **execution_logs** - Detailed logs
5. **audit_logs** - Audit trail
6. **data_quality_metrics** - Aggregated metrics
7. **batch_jobs** - Batch operations
8. **workloads** - Workload metadata
9. **users** - Authentication users
10. **audit_events** - Detailed audit events

### 6.3 Migration Path

1. **Parallel Storage Phase**: Keep JSON files, add database writes
2. **Validation Phase**: Verify data consistency
3. **Switchover Phase**: Read from database, keep JSON as backup
4. **Cleanup Phase**: Archive old JSON files

### 6.4 Key Models for Database

```python
# Database Models (SQLAlchemy)
class Project(Base):
    project_id: str (PK)
    name: str
    description: str
    created_at: datetime
    updated_at: datetime
    # ... other fields

class PipelineRun(Base):
    run_id: str (PK)
    project_id: str (FK)
    pipeline_name: str
    status: Enum
    started_at: datetime
    completed_at: datetime
    # ... other fields

class ValidationStep(Base):
    step_id: int (PK, Auto)
    run_id: str (FK)
    step_name: str
    validator_type: str
    status: Enum
    # ... result fields

class AuditLog(Base):
    log_id: int (PK, Auto)
    timestamp: datetime
    action: str
    user: str
    resource_type: str
    resource_id: str
    # ... other fields
```

---

## 7. TECHNOLOGY DEPENDENCIES

### 7.1 Backend Dependencies
- **fastapi** (0.109.0) - REST API framework
- **uvicorn** - ASGI server
- **pydantic** (2.5.3) - Data validation
- **sqlalchemy** (2.0.25) - ORM
- **pyodbc** (5.0.1) - SQL Server driver
- **snowflake-connector-python** (3.6.0) - Snowflake SDK
- **pyyaml** (6.0.1) - YAML parsing
- **sqlparse** (0.4.4) - SQL parsing
- **python-jose** - JWT authentication
- **bcrypt** - Password hashing
- **reportlab** (4.0.7) - PDF generation
- **openpyxl** (3.1.2) - Excel generation
- **pandas**, **numpy**, **scipy** - Data processing

### 7.2 Frontend Dependencies
- **React** 18+
- **TypeScript**
- **Vite** - Build tool
- **Victory** - Charting library
- **React components** - Custom UI

### 7.3 Core Engine Dependencies
- Custom validation validators
- Connection management
- Registry pattern for extensibility

---

## 8. DEPLOYMENT CONSIDERATIONS

### 8.1 Docker Composition
- **Backend Container**: FastAPI + Ombudsman Core
- **Frontend Container**: React/Vite build
- **Optional Database**: SQLite or SQL Server container
- **Volume Mounts**: `/data` for persistent storage

### 8.2 Environment Configuration
```
MSSQL_HOST=host.docker.internal
MSSQL_USER=sa
MSSQL_PASSWORD=YourPassword
SNOWFLAKE_ACCOUNT=...
SNOWFLAKE_USER=...
SNOWFLAKE_PASSWORD=...
SNOWFLAKE_WAREHOUSE=COMPUTE_WH
DATABASE_URL=sqlite:///./test.db  # For results DB
```

### 8.3 Data Persistence
- **Projects**: Persistent `/data/projects` volume
- **Results**: Persistent `/data/results` volume
- **Audit Logs**: Persistent `/data/audit_logs` volume
- **Database**: Optional persistent database volume

---

## 9. SECURITY CONSIDERATIONS

### 9.1 Authentication
- JWT-based token authentication
- Role-based access control (Admin, User, Viewer)
- BCrypt password hashing
- Token refresh mechanism

### 9.2 Audit Trail
- All operations logged with user, timestamp, action
- Searchable audit logs
- Configurable retention policies
- Compliance-ready format

### 9.3 Data Protection
- Credentials not stored in JSON files
- Environment variable injection for sensitive data
- Optional encryption for audit logs
- HTTPS support in production

---

## 10. EXTENSIBILITY POINTS

### 10.1 Adding New Validators
- Register in `ValidationRegistry`
- Implement validator interface
- Add to bootstrap validators

### 10.2 Adding New Data Sources
- Implement connection manager
- Add metadata loader
- Register in connection factory

### 10.3 Adding New API Endpoints
- Create new router
- Include in main.py
- Follow authentication patterns

### 10.4 Custom Pipeline Templates
- Save YAML pipelines
- Make available in UI
- Manage through project context

---

## 11. MONITORING & OBSERVABILITY

### 11.1 Logging
- Structured JSON logs
- Log levels: DEBUG, INFO, WARNING, ERROR
- Audit logging for compliance
- WebSocket event logging

### 11.2 Metrics
- Pipeline execution times
- Validation step durations
- Batch job progress
- Connection pool stats
- Data quality scores

### 11.3 Error Handling
- Custom exception types
- Detailed error messages
- Stack trace logging
- User-friendly error responses

---

## 12. KNOWN LIMITATIONS & FUTURE ENHANCEMENTS

### Current Limitations
1. Single-instance only (no distributed execution)
2. In-memory pipeline run tracking (lost on restart)
3. Basic batch job tracking
4. No encryption at rest
5. Limited scaling for large workloads

### Recommended Enhancements
1. Implement database persistence for all operations
2. Add distributed job execution
3. Implement result caching
4. Add machine learning for validator suggestions
5. Implement real-time dashboard
6. Add multi-tenant support
7. Implement result archival/compression
8. Add advanced scheduling (cron, recurring)
9. Implement custom alert rules
10. Add data lineage tracking

---

## CONCLUSION

This comprehensive system provides a complete data migration validation platform with:
- **Intelligent automation** for pipeline generation
- **Real-time monitoring** of validation execution
- **Flexible storage** with file-based and database options
- **Extensive API** covering all operations
- **Security & audit** for compliance
- **Extensibility** for custom validators and sources

The system is ready for database migration with clear paths for scaling and enhancement.

