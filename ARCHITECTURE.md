# Ombudsman Validation Studio - System Architecture

## Table of Contents
1. [Overview](#overview)
2. [System Architecture](#system-architecture)
3. [Component Architecture](#component-architecture)
4. [Data Flow](#data-flow)
5. [Technology Stack](#technology-stack)
6. [Deployment Architecture](#deployment-architecture)
7. [Security Architecture](#security-architecture)
8. [Integration Architecture](#integration-architecture)
9. [Scalability & Performance](#scalability--performance)

---

## Overview

Ombudsman Validation Studio is an intelligent data migration validation platform designed to ensure data integrity during database migrations from SQL Server to Snowflake (or other data warehouses). The system provides comprehensive validation across multiple dimensions including schema, data quality, referential integrity, business rules, and warehouse-specific validations.

### Key Characteristics
- **Architecture Pattern**: Microservices with containerized deployment
- **Frontend**: Single Page Application (SPA) using React
- **Backend**: RESTful API using FastAPI (Python)
- **Deployment**: Docker Compose for single-VM deployment
- **Database Support**: SQL Server (source), Snowflake (target), Any SQL database for application data

---

## System Architecture

### High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           USER LAYER                                     │
│                                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                 │
│  │   Browser    │  │   Browser    │  │   Browser    │                 │
│  │  (Chrome)    │  │  (Firefox)   │  │   (Safari)   │                 │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘                 │
│         │                  │                  │                          │
│         └──────────────────┴──────────────────┘                          │
│                            │                                             │
└────────────────────────────┼─────────────────────────────────────────────┘
                             │ HTTPS (Port 3000)
                             │
┌────────────────────────────▼─────────────────────────────────────────────┐
│                     PRESENTATION LAYER                                   │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │              React Frontend Container (studio-frontend)             │ │
│  │                                                                     │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐            │ │
│  │  │  Landing     │  │  Pipeline    │  │  Metadata    │            │ │
│  │  │  Page        │  │  Builder     │  │  Extraction  │            │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘            │ │
│  │                                                                     │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐            │ │
│  │  │  Database    │  │  Workload    │  │  Comparison  │            │ │
│  │  │  Mapping     │  │  Analysis    │  │  Viewer      │            │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘            │ │
│  │                                                                     │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐            │ │
│  │  │  Results     │  │  Project     │  │  User        │            │ │
│  │  │  Viewer      │  │  Manager     │  │  Profile     │            │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘            │ │
│  │                                                                     │ │
│  │  Technology: React 18, TypeScript, Material-UI v5, Vite           │ │
│  │  Port: 3000                                                        │ │
│  └─────────────────────────────┬───────────────────────────────────────┘ │
│                                │ REST API (Port 8000)                   │
└────────────────────────────────┼───────────────────────────────────────┘
                                 │
┌────────────────────────────────▼───────────────────────────────────────┐
│                      APPLICATION LAYER                                 │
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────────┐ │
│  │           FastAPI Backend Container (studio-backend)              │ │
│  │                                                                   │ │
│  │  ┌─────────────────────────────────────────────────────────────┐ │ │
│  │  │                    API ROUTERS                               │ │ │
│  │  │                                                              │ │ │
│  │  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │ │ │
│  │  │  │   Auth   │ │ Projects │ │Pipelines │ │ Metadata │      │ │ │
│  │  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘      │ │ │
│  │  │                                                              │ │ │
│  │  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │ │ │
│  │  │  │ Mapping  │ │ Workload │ │Execution │ │  Rules   │      │ │ │
│  │  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘      │ │ │
│  │  │                                                              │ │ │
│  │  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │ │ │
│  │  │  │  Data    │ │ Results  │ │ Mermaid  │ │Connection│      │ │ │
│  │  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘      │ │ │
│  │  └─────────────────────────────────────────────────────────────┘ │ │
│  │                                                                   │ │
│  │  ┌─────────────────────────────────────────────────────────────┐ │ │
│  │  │                  BUSINESS LOGIC                              │ │ │
│  │  │                                                              │ │ │
│  │  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │ │ │
│  │  │  │  Intelligent │  │  Pipeline    │  │  Metadata    │     │ │ │
│  │  │  │  Query Gen   │  │  Executor    │  │  Extractor   │     │ │ │
│  │  │  └──────────────┘  └──────────────┘  └──────────────┘     │ │ │
│  │  │                                                              │ │ │
│  │  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │ │ │
│  │  │  │  Workload    │  │  Database    │  │  Results     │     │ │ │
│  │  │  │  Analyzer    │  │  Mapper      │  │  Aggregator  │     │ │ │
│  │  │  └──────────────┘  └──────────────┘  └──────────────┘     │ │ │
│  │  └─────────────────────────────────────────────────────────────┘ │ │
│  │                                                                   │ │
│  │  Technology: FastAPI, Python 3.11, Pydantic, SQLAlchemy         │ │
│  │  Port: 8000                                                      │ │
│  └───────────────────────────────┬───────────────────────────────────┘ │
│                                  │                                     │
└──────────────────────────────────┼─────────────────────────────────────┘
                                   │
┌──────────────────────────────────▼─────────────────────────────────────┐
│                         CORE LIBRARY LAYER                             │
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────────┐ │
│  │                   Ombudsman Core Library                          │ │
│  │                                                                   │ │
│  │  ┌─────────────────────────────────────────────────────────────┐ │ │
│  │  │                  VALIDATION MODULES                          │ │ │
│  │  │                                                              │ │ │
│  │  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │ │ │
│  │  │  │  Schema  │ │   Data   │ │Referential│ │Dimension │      │ │ │
│  │  │  │Validation│ │ Quality  │ │Integrity │ │Validation│      │ │ │
│  │  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘      │ │ │
│  │  │                                                              │ │ │
│  │  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │ │ │
│  │  │  │   Fact   │ │  Metrics │ │Time Series│ │ Business │      │ │ │
│  │  │  │Validation│ │Validation│ │Validation│ │  Rules   │      │ │ │
│  │  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘      │ │ │
│  │  └─────────────────────────────────────────────────────────────┘ │ │
│  │                                                                   │ │
│  │  ┌─────────────────────────────────────────────────────────────┐ │ │
│  │  │                    CORE SERVICES                             │ │ │
│  │  │                                                              │ │ │
│  │  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │ │ │
│  │  │  │  Connection  │  │   Metadata   │  │   Mapping    │     │ │ │
│  │  │  │   Manager    │  │    Loader    │  │    Loader    │     │ │ │
│  │  │  └──────────────┘  └──────────────┘  └──────────────┘     │ │ │
│  │  │                                                              │ │ │
│  │  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │ │ │
│  │  │  │  Pipeline    │  │     Step     │  │Relationship  │     │ │ │
│  │  │  │   Runner     │  │   Executor   │  │  Inferrer    │     │ │ │
│  │  │  └──────────────┘  └──────────────┘  └──────────────┘     │ │ │
│  │  └─────────────────────────────────────────────────────────────┘ │ │
│  │                                                                   │ │
│  │  Technology: Python 3.11, pyodbc, snowflake-connector-python    │ │
│  └───────────────────────────────┬───────────────────────────────────┘ │
│                                  │                                     │
└──────────────────────────────────┼─────────────────────────────────────┘
                                   │
┌──────────────────────────────────▼─────────────────────────────────────┐
│                          DATA LAYER                                    │
│                                                                        │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐   │
│  │                  │  │                  │  │                  │   │
│  │  OVS Studio DB   │  │  SQL Server      │  │  Snowflake       │   │
│  │  (Application)   │  │  (Source DW)     │  │  (Target DW)     │   │
│  │                  │  │                  │  │                  │   │
│  │  ┌────────────┐  │  │  ┌────────────┐ │  │  ┌────────────┐  │   │
│  │  │   Users    │  │  │  │   Facts    │ │  │  │   Facts    │  │   │
│  │  │  Projects  │  │  │  │ Dimensions │ │  │  │ Dimensions │  │   │
│  │  │  Pipelines │  │  │  │  Staging   │ │  │  │  Staging   │  │   │
│  │  │  Results   │  │  │  │            │ │  │  │            │  │   │
│  │  │  Mappings  │  │  │  │            │ │  │  │            │  │   │
│  │  └────────────┘  │  │  └────────────┘ │  │  └────────────┘  │   │
│  │                  │  │                  │  │                  │   │
│  │  SQL Server      │  │  SQL Server      │  │  Snowflake       │   │
│  │  or PostgreSQL   │  │  2016+           │  │  Enterprise      │   │
│  │                  │  │                  │  │                  │   │
│  │  Port: 1433      │  │  Port: 1433      │  │  Port: 443       │   │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘   │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

---

## Component Architecture

### Frontend Components (React SPA)

#### 1. Landing Page
- **Purpose**: Dashboard with feature overview
- **Features**: Navigation to all major features
- **Components**: Feature cards, quick actions

#### 2. Project Manager
- **Purpose**: Create, list, and manage validation projects
- **Features**: Project CRUD operations, project selection
- **State**: Active project stored in localStorage

#### 3. Database & Schema Mapping
- **Purpose**: Configure source-target mappings
- **Features**:
  - Schema-to-schema mapping
  - Table-to-table mapping
  - Column-to-column mapping
  - Fuzzy matching suggestions
- **API Endpoints**: `/mapping/suggest`, `/projects/{id}/mapping`

#### 4. Metadata Extraction
- **Purpose**: Extract and view database metadata
- **Features**:
  - Connect to SQL Server/Snowflake
  - Extract tables, columns, relationships
  - Display metadata in tabular format
  - Export to YAML
- **API Endpoints**: `/metadata/extract`, `/metadata/extract-relationships`

#### 5. Pipeline Builder
- **Purpose**: Create validation pipelines visually
- **Features**:
  - Visual pipeline graph
  - Step library (30+ validation types)
  - Dependency management
  - Step configuration
  - Mermaid diagram generation
- **API Endpoints**: `/pipelines/create`, `/pipelines/execute`

#### 6. Workload Analysis
- **Purpose**: Analyze SQL Server Query Store workloads
- **Features**:
  - Query pattern detection
  - Intelligent validation suggestions
  - Semantic column classification
  - Shape mismatch detection
- **API Endpoints**: `/workload/analyze`, `/workload/suggest`

#### 7. Comparison Viewer
- **Purpose**: View row-level data differences
- **Features**:
  - Side-by-side comparison
  - Highlight differences
  - Filter by mismatch type
  - Export results
- **API Endpoints**: `/execution/shape-comparison`

#### 8. Results Viewer
- **Purpose**: View pipeline execution results
- **Features**:
  - Execution history
  - Step-by-step results
  - Pass/fail status
  - Detailed logs
- **API Endpoints**: `/execution/results/{execution_id}`

#### 9. User Profile & Authentication
- **Purpose**: User management and authentication
- **Features**:
  - JWT-based authentication
  - User registration/login
  - Password management
  - Profile updates
- **API Endpoints**: `/auth/register`, `/auth/login`, `/auth/me`

### Backend Components (FastAPI)

#### API Routers

1. **auth.py** - User authentication and authorization
   - POST `/auth/register` - Register new user
   - POST `/auth/login` - User login (JWT token)
   - GET `/auth/me` - Get current user
   - PUT `/auth/password` - Change password

2. **projects.py** - Project management
   - GET `/projects/` - List all projects
   - POST `/projects/` - Create new project
   - GET `/projects/{id}` - Get project details
   - PUT `/projects/{id}` - Update project
   - DELETE `/projects/{id}` - Delete project

3. **metadata.py** - Metadata extraction
   - POST `/metadata/extract` - Extract database metadata
   - POST `/metadata/extract-relationships` - Extract FK relationships
   - GET `/metadata/export/{project_id}` - Export to YAML

4. **mapping.py** - Database mapping
   - POST `/mapping/suggest` - Get fuzzy mapping suggestions
   - GET `/projects/{id}/mapping` - Get project mappings
   - PUT `/projects/{id}/mapping` - Save mappings

5. **pipelines.py** - Pipeline management
   - GET `/pipelines/` - List pipelines
   - POST `/pipelines/` - Create pipeline
   - GET `/pipelines/{id}` - Get pipeline
   - PUT `/pipelines/{id}` - Update pipeline
   - DELETE `/pipelines/{id}` - Delete pipeline
   - POST `/pipelines/{id}/execute` - Execute pipeline

6. **workload.py** - Workload analysis
   - POST `/workload/analyze` - Analyze Query Store data
   - POST `/workload/suggest` - Get intelligent suggestions
   - GET `/workload/patterns` - Get query patterns

7. **execution.py** - Pipeline execution
   - GET `/execution/results/{execution_id}` - Get results
   - GET `/execution/history` - Execution history
   - POST `/execution/shape-comparison` - Generate comparison

8. **connections.py** - Database connectivity
   - POST `/connections/test` - Test connection
   - GET `/connections/status` - Connection status

9. **mermaid.py** - Diagram generation
   - POST `/mermaid/pipeline` - Generate pipeline diagram
   - POST `/mermaid/erd` - Generate ERD diagram

### Core Library Components (Ombudsman Core)

#### Validation Modules

1. **Schema Validation** (`validation/schema/`)
   - `validate_schema_columns.py` - Column existence
   - `validate_schema_datatypes.py` - Data type matching
   - `validate_schema_nullability.py` - NULL constraints

2. **Data Quality Validation** (`validation/dq/`)
   - `validate_record_counts.py` - Row count comparison
   - `validate_nulls.py` - NULL value validation
   - `validate_uniqueness.py` - Uniqueness constraints
   - `validate_statistics.py` - Statistical validation
   - `validate_distribution.py` - Distribution analysis
   - `validate_outliers.py` - Outlier detection
   - `validate_domain_values.py` - Domain validation
   - `validate_regex_patterns.py` - Pattern matching

3. **Referential Integrity** (`validation/ri/`)
   - `validate_foreign_keys.py` - FK constraint validation

4. **Dimension Validation** (`validation/dimensions/`)
   - `validate_dim_business_keys.py` - Business key validation
   - `validate_dim_surrogate_keys.py` - Surrogate key validation
   - `validate_scd1.py` - SCD Type 1 validation
   - `validate_scd2.py` - SCD Type 2 validation
   - `validate_composite_keys.py` - Composite key validation

5. **Fact Validation** (`validation/facts/`)
   - `validate_fact_dim_conformance.py` - Fact-dimension conformance
   - `validate_late_arriving_facts.py` - Late arriving fact detection

6. **Metrics Validation** (`validation/metrics/`)
   - `validate_metric_sums.py` - Sum validation
   - `validate_metric_averages.py` - Average validation
   - `validate_ratios.py` - Ratio validation

7. **Time Series Validation** (`validation/timeseries/`)
   - `validate_ts_continuity.py` - Continuity validation
   - `validate_ts_duplicates.py` - Duplicate detection
   - `validate_ts_rolling_drift.py` - Drift detection
   - `validate_period_over_period.py` - Period comparison

8. **Business Rules** (`validation/business/`)
   - Custom business validation logic

#### Core Services

1. **Connection Manager** (`core/connections.py`)
   - Manages database connections
   - Connection pooling
   - Connection testing
   - Support for SQL Server, Snowflake, PostgreSQL

2. **Metadata Loader** (`core/metadata_loader.py`)
   - Extract table schemas
   - Extract column metadata
   - Extract indexes and constraints
   - Caching for performance

3. **Mapping Loader** (`core/mapping_loader.py`)
   - Load mapping configurations
   - Fuzzy matching algorithm
   - Mapping validation
   - YAML parsing

4. **Relationship Inferrer** (`core/relationship_inferrer.py`)
   - Infer FK relationships
   - Detect naming patterns
   - Confidence scoring

5. **Pipeline Runner** (`pipeline/pipeline_runner.py`)
   - Execute validation pipelines
   - Dependency resolution
   - Parallel execution
   - Error handling

6. **Step Executor** (`pipeline/step_executor.py`)
   - Execute individual validation steps
   - Parameter injection
   - Result collection
   - Logging

---

## Data Flow

### 1. User Authentication Flow

```
┌─────────┐      POST /auth/register       ┌──────────┐
│ Browser │ ───────────────────────────────>│  Backend │
└─────────┘                                 └──────────┘
     │                                            │
     │         { username, password }             │
     │                                            ▼
     │                                      ┌──────────┐
     │                                      │ Hash PWD │
     │                                      └──────────┘
     │                                            │
     │                                            ▼
     │                                      ┌──────────┐
     │                                      │  OVS DB  │
     │         User Created                 │  INSERT  │
     │     <───────────────────────────     └──────────┘
     │
     ▼
┌─────────┐      POST /auth/login          ┌──────────┐
│ Browser │ ───────────────────────────────>│  Backend │
└─────────┘                                 └──────────┘
     │                                            │
     │         { username, password }             │
     │                                            ▼
     │                                      ┌──────────┐
     │                                      │ Verify   │
     │                                      │ Password │
     │                                      └──────────┘
     │                                            │
     │                                            ▼
     │                                      ┌──────────┐
     │                                      │ Generate │
     │         JWT Token                    │   JWT    │
     │     <───────────────────────────     └──────────┘
     │
     ▼
     Store in localStorage
     │
     │     Subsequent requests with
     │     Authorization: Bearer <token>
     ▼
```

### 2. Metadata Extraction Flow

```
┌─────────┐  1. Click "Extract Metadata"   ┌──────────┐
│ Browser │ ───────────────────────────────>│ Frontend │
└─────────┘                                 └──────────┘
                                                  │
                                                  │ 2. POST /metadata/extract
                                                  ▼
                                            ┌──────────┐
                                            │  Backend │
                                            └──────────┘
                                                  │
                                                  │ 3. Call ombudsman_core
                                                  ▼
                                            ┌──────────┐
                                            │ Metadata │
                                            │  Loader  │
                                            └──────────┘
                                                  │
                          ┌───────────────────────┴───────────────────────┐
                          │                                               │
                    4. Connect                                      4. Connect
                          ▼                                               ▼
                    ┌──────────┐                                    ┌──────────┐
                    │   SQL    │                                    │Snowflake │
                    │  Server  │                                    └──────────┘
                    └──────────┘                                          │
                          │                                               │
             5. Query INFORMATION_SCHEMA              5. Query INFORMATION_SCHEMA
                          │                                               │
                          └───────────────────────┬───────────────────────┘
                                                  │
                                            6. Aggregate
                                                  ▼
                                            ┌──────────┐
                                            │  Return  │
                                            │ Metadata │
                                            └──────────┘
                                                  │
                                                  │ 7. JSON Response
                                                  ▼
                                            ┌──────────┐
                                            │ Frontend │
                                            └──────────┘
                                                  │
                                                  │ 8. Display in UI
                                                  ▼
                                            ┌──────────┐
                                            │  Table   │
                                            │  View    │
                                            └──────────┘
```

### 3. Pipeline Execution Flow

```
┌─────────┐  1. Click "Execute Pipeline"   ┌──────────┐
│ Browser │ ───────────────────────────────>│ Frontend │
└─────────┘                                 └──────────┘
                                                  │
                                                  │ 2. POST /pipelines/{id}/execute
                                                  ▼
                                            ┌──────────┐
                                            │  Backend │
                                            └──────────┘
                                                  │
                                                  │ 3. Load pipeline config
                                                  ▼
                                            ┌──────────┐
                                            │ Pipeline │
                                            │  Runner  │
                                            └──────────┘
                                                  │
                                                  │ 4. Resolve dependencies
                                                  │    Build execution graph
                                                  ▼
                                            ┌──────────┐
                                            │   DAG    │
                                            │ Builder  │
                                            └──────────┘
                                                  │
                                                  │ 5. For each step (in order)
                                                  ▼
                                   ┌──────────────┴──────────────┐
                                   │                             │
                            Step 1 (parallel)              Step 2 (parallel)
                                   │                             │
                                   ▼                             ▼
                            ┌──────────┐                  ┌──────────┐
                            │   Step   │                  │   Step   │
                            │ Executor │                  │ Executor │
                            └──────────┘                  └──────────┘
                                   │                             │
                        6. Load validation module    6. Load validation module
                                   │                             │
                                   ▼                             ▼
                      ┌──────────────────┐          ┌──────────────────┐
                      │ validate_schema_ │          │ validate_record_ │
                      │    columns.py    │          │    counts.py     │
                      └──────────────────┘          └──────────────────┘
                                   │                             │
                        7. Execute validation        7. Execute validation
                                   │                             │
                  ┌────────────────┴────────────┐   ┌────────────┴────────────┐
                  │                             │   │                         │
          Query SQL Server              Query Snowflake      Query SQL Server  Query Snowflake
                  │                             │   │                         │
                  ▼                             ▼   ▼                         ▼
            ┌──────────┐                  ┌──────────┐                  ┌──────────┐
            │   SQL    │                  │Snowflake │                  │   SQL    │ ...
            │  Server  │                  └──────────┘                  │  Server  │
            └──────────┘                        │                       └──────────┘
                  │                             │                             │
                  └──────────────┬──────────────┘                             │
                                 │                                            │
                          8. Compare results                          8. Compare counts
                                 │                                            │
                                 ▼                                            ▼
                           ┌──────────┐                              ┌──────────┐
                           │  PASS /  │                              │  PASS /  │
                           │   FAIL   │                              │   FAIL   │
                           └──────────┘                              └──────────┘
                                 │                                            │
                                 └────────────────┬───────────────────────────┘
                                                  │
                                          9. Aggregate results
                                                  ▼
                                            ┌──────────┐
                                            │  Save to │
                                            │  OVS DB  │
                                            └──────────┘
                                                  │
                                                  │ 10. Return execution_id
                                                  ▼
                                            ┌──────────┐
                                            │ Frontend │
                                            └──────────┘
                                                  │
                                                  │ 11. Navigate to Results
                                                  ▼
                                            ┌──────────┐
                                            │ Results  │
                                            │  Viewer  │
                                            └──────────┘
```

### 4. Intelligent Workload Analysis Flow

```
┌─────────┐  1. Upload Query Store data    ┌──────────┐
│ Browser │ ───────────────────────────────>│ Frontend │
└─────────┘                                 └──────────┘
                                                  │
                                                  │ 2. POST /workload/analyze
                                                  ▼
                                            ┌──────────┐
                                            │  Backend │
                                            └──────────┘
                                                  │
                                                  │ 3. Parse queries
                                                  ▼
                                            ┌──────────┐
                                            │ Workload │
                                            │ Analyzer │
                                            └──────────┘
                                                  │
                          ┌───────────────────────┼───────────────────────┐
                          │                       │                       │
                    4. Extract              4. Classify             4. Detect
                      tables                 columns                patterns
                          │                       │                       │
                          ▼                       ▼                       ▼
                    ┌──────────┐           ┌──────────┐           ┌──────────┐
                    │  Tables  │           │Identifier│           │  SUM()   │
                    │   Used   │           │  vs      │           │  AVG()   │
                    │          │           │ Measure  │           │ COUNT()  │
                    └──────────┘           └──────────┘           └──────────┘
                          │                       │                       │
                          └───────────────────────┼───────────────────────┘
                                                  │
                                        5. Match with metadata
                                                  ▼
                                            ┌──────────┐
                                            │ Metadata │
                                            │  Loader  │
                                            └──────────┘
                                                  │
                                      6. Infer relationships
                                                  ▼
                                            ┌──────────┐
                                            │Relationship│
                                            │ Inferrer │
                                            └──────────┘
                                                  │
                                   7. Generate smart suggestions
                                                  ▼
                                            ┌──────────┐
                                            │- Validate│
                                            │  SUM on  │
                                            │ Amount   │
                                            │- Validate│
                                            │  FK to   │
                                            │ Customer │
                                            └──────────┘
                                                  │
                                                  │ 8. Return suggestions
                                                  ▼
                                            ┌──────────┐
                                            │ Frontend │
                                            └──────────┘
                                                  │
                                                  │ 9. Display suggestions
                                                  │ 10. User clicks "Add to Pipeline"
                                                  ▼
                                            ┌──────────┐
                                            │ Pipeline │
                                            │ Builder  │
                                            └──────────┘
```

---

## Technology Stack

### Frontend Stack

```
┌────────────────────────────────────────────────────────────┐
│                     Frontend Stack                         │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  Core Framework:                                           │
│  ├─ React 18.3.1                 (UI library)             │
│  ├─ TypeScript 5.6.2             (Type safety)            │
│  └─ Vite 5.4.2                   (Build tool)             │
│                                                            │
│  UI Framework:                                             │
│  ├─ Material-UI (MUI) 6.3.0      (Component library)      │
│  ├─ @mui/icons-material          (Icons)                  │
│  └─ @emotion/react               (CSS-in-JS)              │
│                                                            │
│  Routing & State:                                          │
│  ├─ React Router 7.1.1           (Navigation)             │
│  └─ localStorage                 (Client-side persistence) │
│                                                            │
│  HTTP Client:                                              │
│  └─ Fetch API                    (REST API calls)         │
│                                                            │
│  Diagram Rendering:                                        │
│  └─ Mermaid                      (Pipeline diagrams)       │
│                                                            │
│  Development:                                              │
│  ├─ ESLint                       (Linting)                │
│  └─ Vite Dev Server              (Hot reload)             │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

### Backend Stack

```
┌────────────────────────────────────────────────────────────┐
│                     Backend Stack                          │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  Core Framework:                                           │
│  ├─ FastAPI 0.115.6              (Web framework)          │
│  ├─ Python 3.11                  (Language)               │
│  ├─ Uvicorn                      (ASGI server)            │
│  └─ Pydantic                     (Data validation)        │
│                                                            │
│  Database Drivers:                                         │
│  ├─ pyodbc 5.2.0                 (SQL Server)             │
│  ├─ snowflake-connector-python   (Snowflake)              │
│  └─ SQLAlchemy                   (ORM for OVS DB)         │
│                                                            │
│  Authentication:                                           │
│  ├─ python-jose                  (JWT tokens)             │
│  ├─ passlib                      (Password hashing)       │
│  └─ bcrypt                       (Hashing algorithm)      │
│                                                            │
│  Configuration:                                            │
│  ├─ python-dotenv                (Environment variables)  │
│  └─ PyYAML                       (YAML parsing)           │
│                                                            │
│  Utilities:                                                │
│  ├─ fuzzywuzzy                   (Fuzzy matching)         │
│  ├─ pandas                       (Data manipulation)      │
│  └─ networkx                     (Graph algorithms)       │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

### Core Library Stack

```
┌────────────────────────────────────────────────────────────┐
│                   Core Library Stack                       │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  Language:                                                 │
│  └─ Python 3.11+                                           │
│                                                            │
│  Database Connectivity:                                    │
│  ├─ pyodbc 5.2.0                 (SQL Server, PostgreSQL) │
│  ├─ snowflake-connector-python   (Snowflake)              │
│  └─ psycopg2                     (PostgreSQL alternative) │
│                                                            │
│  Data Processing:                                          │
│  ├─ pandas                       (DataFrames)             │
│  ├─ numpy                        (Numerical computing)    │
│  └─ scipy                        (Statistical analysis)   │
│                                                            │
│  Configuration:                                            │
│  ├─ PyYAML                       (YAML parsing)           │
│  └─ python-dotenv                (Environment variables)  │
│                                                            │
│  Graph Processing:                                         │
│  └─ networkx                     (Pipeline DAG)           │
│                                                            │
│  Logging:                                                  │
│  └─ Python logging               (Structured logging)     │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

### Infrastructure Stack

```
┌────────────────────────────────────────────────────────────┐
│                  Infrastructure Stack                      │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  Containerization:                                         │
│  ├─ Docker Engine 24.0+                                    │
│  ├─ Docker Compose 2.20+                                   │
│  └─ Multi-stage builds                                     │
│                                                            │
│  Process Management:                                       │
│  ├─ systemd (Ubuntu)             (Auto-start service)     │
│  └─ Task Scheduler (Windows)     (Auto-start service)     │
│                                                            │
│  Reverse Proxy (Optional):                                 │
│  ├─ Nginx                        (Load balancing)         │
│  └─ Traefik                      (Container-aware proxy)  │
│                                                            │
│  Monitoring (Optional):                                    │
│  ├─ Docker stats                 (Resource monitoring)    │
│  ├─ Prometheus                   (Metrics collection)     │
│  └─ Grafana                      (Visualization)          │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

---

## Deployment Architecture

### Single-VM Deployment (Current Model)

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Ubuntu 22.04 LTS / Windows Server            │
│                              Virtual Machine                        │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │                      Docker Engine                            │ │
│  │                                                               │ │
│  │  ┌─────────────────────────────────────────────────────────┐ │ │
│  │  │  Docker Compose Network (ombudsman-network)             │ │ │
│  │  │                                                         │ │ │
│  │  │  ┌─────────────────────┐  ┌─────────────────────┐     │ │ │
│  │  │  │  studio-frontend    │  │   studio-backend    │     │ │ │
│  │  │  │                     │  │                     │     │ │ │
│  │  │  │  React + Vite       │  │  FastAPI + Python   │     │ │ │
│  │  │  │  Nginx (static)     │  │  Uvicorn ASGI       │     │ │ │
│  │  │  │                     │  │                     │     │ │ │
│  │  │  │  Port: 3000         │  │  Port: 8000         │     │ │ │
│  │  │  │                     │  │                     │     │ │ │
│  │  │  │  /app/dist/         │  │  /app/              │     │ │ │
│  │  │  │                     │  │  ombudsman_core/    │     │ │ │
│  │  │  └─────────┬───────────┘  └─────────┬───────────┘     │ │ │
│  │  │            │                        │                 │ │ │
│  │  │            │   HTTP (internal)      │                 │ │ │
│  │  │            │                        │                 │ │ │
│  │  └────────────┼────────────────────────┼─────────────────┘ │ │
│  │               │                        │                   │ │
│  └───────────────┼────────────────────────┼───────────────────┘ │
│                  │                        │                     │
│  ┌───────────────▼────────────────────────▼───────────────────┐ │
│  │                    Host Network                            │ │
│  │                                                            │ │
│  │  0.0.0.0:3000 ──> studio-frontend:3000                    │ │
│  │  0.0.0.0:8000 ──> studio-backend:8000                     │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                 Environment Configuration                  │ │
│  │                                                            │ │
│  │  SINGLE SOURCE OF TRUTH: ombudsman-validation-studio/.env  │ │
│  │                                                            │ │
│  │  /opt/ombudsman-validation-studio/.env                     │ │
│  │  ├─ MSSQL_HOST=192.168.1.100                              │ │
│  │  ├─ MSSQL_DATABASE=your-database                          │ │
│  │  ├─ SNOWFLAKE_ACCOUNT=xyz.us-east-1.aws                   │ │
│  │  ├─ SNOWFLAKE_DATABASE=your-database                      │ │
│  │  ├─ SNOWFLAKE_SCHEMA=your-schema                          │ │
│  │  ├─ OVS_DB_HOST=192.168.1.100                             │ │
│  │  └─ JWT_SECRET_KEY=***                                    │ │
│  │                                                            │ │
│  │  ombudsman_core/.env -> ../ombudsman-validation-studio/.env│ │
│  │  (Symlinked to ensure single source of truth)             │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                  Systemd Service (Auto-start)              │ │
│  │                                                            │ │
│  │  /etc/systemd/system/ombudsman-studio.service             │ │
│  │  └─ ExecStart=docker compose up -d                        │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ Outbound connections
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐     ┌───────────────┐     ┌───────────────┐
│  SQL Server   │     │  Snowflake    │     │  OVS Studio   │
│  (Source DW)  │     │  (Target DW)  │     │  Database     │
│               │     │               │     │  (App Data)   │
│  Port: 1433   │     │  Port: 443    │     │  Port: 1433   │
│               │     │               │     │               │
│  External or  │     │  Cloud SaaS   │     │  Same as SQL  │
│  Same Host    │     │               │     │  Server       │
└───────────────┘     └───────────────┘     └───────────────┘
```

### Deployment Specifications

#### Hardware Requirements

**Minimum (Development/Testing)**
- **OS**: Ubuntu 20.04 LTS or Windows Server 2019
- **CPU**: 2 cores
- **RAM**: 4 GB
- **Disk**: 20 GB
- **Network**: 100 Mbps

**Recommended (Production)**
- **OS**: Ubuntu 22.04 LTS or Windows Server 2022
- **CPU**: 4+ cores (8+ for heavy workloads)
- **RAM**: 8 GB (16+ for heavy workloads)
- **Disk**: 50 GB SSD (100+ for large datasets)
- **Network**: 1 Gbps

#### Network Requirements

**Required Ports**
- **3000/tcp**: Frontend web interface (inbound from users)
- **8000/tcp**: Backend API (inbound from frontend)
- **1433/tcp**: SQL Server connection (outbound to source/OVS DB)
- **443/tcp**: Snowflake connection (outbound to target)

**Firewall Configuration**
```bash
# Ubuntu (UFW)
sudo ufw allow 3000/tcp
sudo ufw allow 8000/tcp

# Windows (PowerShell)
New-NetFirewallRule -DisplayName "Ombudsman Frontend" -Direction Inbound -LocalPort 3000 -Protocol TCP -Action Allow
New-NetFirewallRule -DisplayName "Ombudsman Backend" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow
```

#### Container Specifications

**Frontend Container** (`studio-frontend`)
```dockerfile
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 3000
```

**Backend Container** (`studio-backend`)
```dockerfile
FROM python:3.11-slim
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    unixodbc \
    unixodbc-dev \
    curl \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Install SQL Server ODBC Driver 18
RUN curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - \
    && curl https://packages.microsoft.com/config/debian/11/prod.list > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y msodbcsql18 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Copy ombudsman_core
COPY ../ombudsman_core /app/ombudsman_core

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Docker Compose Configuration**
```yaml
version: '3.8'

services:
  studio-backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: studio-backend
    ports:
      - "8000:8000"
    environment:
      - SQL_SERVER_HOST=${SQL_SERVER_HOST}
      - SQL_SERVER_PORT=${SQL_SERVER_PORT}
      - SQL_SERVER_USER=${SQL_SERVER_USER}
      - SQL_SERVER_PASSWORD=${SQL_SERVER_PASSWORD}
      - SQL_SERVER_DATABASE=${SQL_SERVER_DATABASE}
      - SNOWFLAKE_ACCOUNT=${SNOWFLAKE_ACCOUNT}
      - SNOWFLAKE_USER=${SNOWFLAKE_USER}
      - SNOWFLAKE_PASSWORD=${SNOWFLAKE_PASSWORD}
      - SNOWFLAKE_WAREHOUSE=${SNOWFLAKE_WAREHOUSE}
      - SNOWFLAKE_DATABASE=${SNOWFLAKE_DATABASE}
      - SNOWFLAKE_SCHEMA=${SNOWFLAKE_SCHEMA}
      - OVS_DB_HOST=${OVS_DB_HOST}
      - OVS_DB_PORT=${OVS_DB_PORT}
      - OVS_DB_NAME=${OVS_DB_NAME}
      - OVS_DB_USER=${OVS_DB_USER}
      - OVS_DB_PASSWORD=${OVS_DB_PASSWORD}
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
      - JWT_ALGORITHM=${JWT_ALGORITHM}
      - JWT_ACCESS_TOKEN_EXPIRE_MINUTES=${JWT_ACCESS_TOKEN_EXPIRE_MINUTES}
    networks:
      - ombudsman-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  studio-frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: studio-frontend
    ports:
      - "3000:80"
    depends_on:
      - studio-backend
    networks:
      - ombudsman-network
    restart: unless-stopped

networks:
  ombudsman-network:
    driver: bridge
```

---

## Security Architecture

### Authentication & Authorization

```
┌─────────────────────────────────────────────────────────────┐
│                    Security Layers                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Layer 1: Transport Security                                │
│  ├─ HTTPS/TLS 1.3 (production)                             │
│  └─ HTTP (development only)                                 │
│                                                             │
│  Layer 2: Authentication                                    │
│  ├─ JWT (JSON Web Tokens)                                  │
│  │  ├─ Algorithm: HS256                                    │
│  │  ├─ Expiry: 30 minutes (configurable)                  │
│  │  ├─ Claims: user_id, username, role                    │
│  │  └─ Signature: HMAC with secret key                    │
│  │                                                         │
│  └─ Password Security                                       │
│     ├─ Hashing: bcrypt                                     │
│     ├─ Rounds: 12                                          │
│     └─ No plaintext storage                                │
│                                                             │
│  Layer 3: Authorization                                     │
│  ├─ Role-based access control (RBAC)                       │
│  ├─ Project ownership validation                           │
│  └─ Resource-level permissions                             │
│                                                             │
│  Layer 4: Database Security                                 │
│  ├─ Parameterized queries (SQL injection prevention)       │
│  ├─ Connection string encryption                           │
│  ├─ Least privilege database users                         │
│  └─ TrustServerCertificate for SQL Server                  │
│                                                             │
│  Layer 5: API Security                                      │
│  ├─ CORS configuration (allowed origins)                   │
│  ├─ Rate limiting (optional)                               │
│  ├─ Input validation (Pydantic models)                     │
│  └─ Error sanitization (no stack traces to client)         │
│                                                             │
│  Layer 6: Container Security                                │
│  ├─ Non-root user execution                                │
│  ├─ Read-only root filesystem (where possible)             │
│  ├─ Minimal base images (Alpine/slim)                      │
│  └─ No secrets in Dockerfiles                              │
│                                                             │
│  Layer 7: Network Security                                  │
│  ├─ Internal Docker network (container-to-container)       │
│  ├─ Firewall rules (UFW/Windows Firewall)                  │
│  └─ VPN for production database access (recommended)       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### JWT Token Flow

```
1. User Login
   ↓
   POST /auth/login { username, password }
   ↓
2. Backend validates credentials
   ↓
   bcrypt.verify(password, stored_hash)
   ↓
3. Generate JWT token
   ↓
   jwt.encode({
     "sub": user_id,
     "username": username,
     "role": "user",
     "exp": datetime.utcnow() + timedelta(minutes=30)
   }, SECRET_KEY, algorithm="HS256")
   ↓
4. Return token to client
   ↓
   { "access_token": "eyJ0eXAi...", "token_type": "bearer" }
   ↓
5. Client stores token (localStorage)
   ↓
6. Subsequent requests include token
   ↓
   Authorization: Bearer eyJ0eXAi...
   ↓
7. Backend validates token (Dependency injection)
   ↓
   async def get_current_user(token: str = Depends(oauth2_scheme)):
       payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
       return User.get(payload["sub"])
   ↓
8. Execute protected endpoint
```

### Configuration Management

**Unified Configuration Architecture**

The system uses a **single source of truth** approach to eliminate configuration ambiguity:

```
Configuration Hierarchy:
======================

1. GLOBAL CONFIGURATION (Single Source of Truth)
   └─ ombudsman-validation-studio/.env
      ├─ Database connection credentials
      ├─ Snowflake connection settings
      ├─ JWT authentication secrets
      └─ System-wide defaults

2. SYMLINKED REFERENCE
   └─ ombudsman_core/.env → ../ombudsman-validation-studio/.env
      ├─ Created automatically via symlink
      ├─ Ensures no configuration duplication
      └─ Any changes to studio/.env apply globally

3. PROJECT-SPECIFIC OVERRIDES (Optional)
   └─ backend/data/projects/{project_id}/project.json
      ├─ Database name overrides
      ├─ Schema name overrides
      ├─ Project-specific mappings
      └─ Managed via UI

4. DOCKER COMPOSE DEFAULTS (Fallback)
   └─ docker-compose.yml environment section
      ├─ Default values if .env missing
      ├─ Template for required variables
      └─ Documentation of expected variables
```

**Why This Architecture?**

- **No Ambiguity**: Users configure database settings in ONE place only
- **Consistency**: Backend and core library use identical settings
- **Flexibility**: Per-project database overrides via UI
- **Simplicity**: No manual synchronization needed

**Creating the Symlink** (done automatically on first setup):
```bash
cd ombudsman_core
rm .env  # Remove old file if exists
ln -s ../ombudsman-validation-studio/.env .env
```

### Secrets Management

**Environment Variables** (`.env` file - **SINGLE SOURCE OF TRUTH**)
```bash
# LOCATION: ombudsman-validation-studio/.env
# NEVER commit to version control
# Store in secure location

# SQL Server Configuration
MSSQL_HOST=your-server.database.windows.net
MSSQL_PORT=1433
MSSQL_DATABASE=your-database
MSSQL_USER=your-user
MSSQL_PASSWORD=YourStrongPassword123!

# Snowflake Configuration
SNOWFLAKE_ACCOUNT=xyz-region.cloud
SNOWFLAKE_USER=your-user
SNOWFLAKE_PASSWORD=YourSnowflakePassword123!
SNOWFLAKE_WAREHOUSE=COMPUTE_WH
SNOWFLAKE_DATABASE=your-database
SNOWFLAKE_SCHEMA=PUBLIC

# OVS Studio Database
OVS_DB_HOST=localhost
OVS_DB_PORT=1433
OVS_DB_NAME=ovs_studio
OVS_DB_USER=your-user
OVS_DB_PASSWORD=YourStrongPassword123!

# JWT secret (32+ random characters)
JWT_SECRET_KEY=change-this-to-a-very-long-random-secret-key
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# Generate JWT secret with: openssl rand -base64 32
```

**Production Recommendations**
- Use secrets management tools (HashiCorp Vault, AWS Secrets Manager, Azure Key Vault)
- Rotate secrets regularly (quarterly)
- Use different credentials for dev/staging/prod
- Enable database audit logging
- Monitor failed login attempts
- Implement account lockout policies

---

## Integration Architecture

### Database Integration

```
┌─────────────────────────────────────────────────────────────┐
│                  Database Connectivity                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  SQL Server Integration                                     │
│  ├─ Driver: ODBC Driver 18 for SQL Server                  │
│  ├─ Protocol: TCP/IP (TDS)                                  │
│  ├─ Port: 1433 (default)                                    │
│  ├─ Authentication: SQL Server Authentication               │
│  ├─ Connection String:                                      │
│  │  DRIVER={ODBC Driver 18 for SQL Server};                │
│  │  SERVER=host,port;                                       │
│  │  DATABASE=dbname;                                        │
│  │  UID=username;                                           │
│  │  PWD=password;                                           │
│  │  TrustServerCertificate=yes;                             │
│  │                                                          │
│  └─ Features Used:                                          │
│     ├─ INFORMATION_SCHEMA for metadata                      │
│     ├─ sys.foreign_keys for FK relationships                │
│     ├─ Query Store for workload analysis                    │
│     └─ Parameterized queries for validation                 │
│                                                             │
│  Snowflake Integration                                      │
│  ├─ Driver: snowflake-connector-python                     │
│  ├─ Protocol: HTTPS                                         │
│  ├─ Port: 443                                               │
│  ├─ Authentication: Username/Password or Key Pair           │
│  ├─ Connection Parameters:                                  │
│  │  account=xyz.region.cloud                               │
│  │  user=username                                          │
│  │  password=password                                       │
│  │  warehouse=COMPUTE_WH                                    │
│  │  database=dbname                                         │
│  │  schema=PUBLIC                                           │
│  │                                                          │
│  └─ Features Used:                                          │
│     ├─ INFORMATION_SCHEMA for metadata                      │
│     ├─ Snowflake-specific SQL functions                     │
│     └─ Parameterized queries for validation                 │
│                                                             │
│  PostgreSQL Integration (for OVS Studio DB)                 │
│  ├─ Driver: psycopg2 or pyodbc                             │
│  ├─ Protocol: TCP/IP                                        │
│  ├─ Port: 5432 (default)                                    │
│  └─ Used for storing application data                       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Connection Pooling

```python
# Backend connection manager (core/connections.py)

class ConnectionManager:
    def __init__(self):
        self.pools = {}

    def get_sql_server_connection(self, config: dict):
        """Get SQL Server connection with pooling"""
        pool_key = f"{config['host']}_{config['database']}"

        if pool_key not in self.pools:
            conn_str = (
                f"DRIVER={{ODBC Driver 18 for SQL Server}};"
                f"SERVER={config['host']},{config['port']};"
                f"DATABASE={config['database']};"
                f"UID={config['user']};"
                f"PWD={config['password']};"
                f"TrustServerCertificate=yes;"
            )
            self.pools[pool_key] = pyodbc.connect(conn_str, autocommit=False)

        return self.pools[pool_key]

    def get_snowflake_connection(self, config: dict):
        """Get Snowflake connection"""
        pool_key = f"{config['account']}_{config['database']}"

        if pool_key not in self.pools:
            self.pools[pool_key] = snowflake.connector.connect(
                account=config['account'],
                user=config['user'],
                password=config['password'],
                warehouse=config['warehouse'],
                database=config['database'],
                schema=config['schema']
            )

        return self.pools[pool_key]
```

### API Integration Points

**External Systems**
- SQL Server (source database)
- Snowflake (target database)
- OVS Studio Database (application data)

**No external API dependencies** - The system is self-contained and does not require internet connectivity for operation (except for Snowflake cloud access).

---

## Scalability & Performance

### Current Scalability Model

**Vertical Scaling** (Single VM)
```
┌─────────────────────────────────────────────────────────┐
│                  Scaling Strategy                       │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Current: Single-VM Deployment                          │
│  ├─ Suitable for: 10-50 concurrent users               │
│  ├─ Dataset size: < 100M rows per table                │
│  └─ Validation complexity: Moderate                     │
│                                                         │
│  Scaling Options:                                       │
│                                                         │
│  1. Vertical Scaling (Increase VM resources)            │
│     ├─ Add more CPU cores (4 → 8 → 16)                 │
│     ├─ Add more RAM (8GB → 16GB → 32GB)                │
│     └─ Use faster storage (SSD → NVMe)                  │
│                                                         │
│  2. Database Optimization                               │
│     ├─ Index source/target databases                    │
│     ├─ Partition large tables                           │
│     ├─ Use materialized views                           │
│     └─ Optimize query patterns                          │
│                                                         │
│  3. Application Optimization                            │
│     ├─ Enable query result caching                      │
│     ├─ Implement pagination for large result sets       │
│     ├─ Use async/await for I/O operations              │
│     └─ Parallelize independent validation steps         │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Performance Optimization

**Backend Optimizations**
```python
# 1. Connection pooling (reuse connections)
connection_manager = ConnectionManager()

# 2. Parallel validation execution
async def execute_pipeline(pipeline):
    # Group steps by dependency level
    levels = build_execution_graph(pipeline)

    for level in levels:
        # Execute independent steps in parallel
        tasks = [execute_step(step) for step in level]
        results = await asyncio.gather(*tasks)

# 3. Query result caching
from functools import lru_cache

@lru_cache(maxsize=128)
def get_table_metadata(connection, table_name):
    # Cache metadata for 5 minutes
    return extract_metadata(connection, table_name)

# 4. Batch processing for large datasets
def validate_record_counts(source_conn, target_conn, batch_size=10000):
    # Process in chunks instead of loading all at once
    for offset in range(0, total_rows, batch_size):
        batch = fetch_batch(source_conn, offset, batch_size)
        validate_batch(batch)
```

**Frontend Optimizations**
```typescript
// 1. Lazy loading of routes
const PipelineBuilder = lazy(() => import('./pages/PipelineBuilder'));
const ResultsViewer = lazy(() => import('./pages/ResultsViewer'));

// 2. Pagination for large lists
const [page, setPage] = useState(0);
const [rowsPerPage, setRowsPerPage] = useState(25);

// 3. Debounced search inputs
const debouncedSearch = useMemo(
  () => debounce((value) => performSearch(value), 300),
  []
);

// 4. React.memo for expensive components
const PipelineGraph = React.memo(({ pipeline }) => {
  // Only re-render if pipeline changes
  return <MermaidDiagram data={pipeline} />;
});
```

### Performance Metrics

**Expected Performance** (on recommended hardware)

| Operation | Time | Notes |
|-----------|------|-------|
| User login | < 500ms | JWT generation |
| Metadata extraction (100 tables) | 5-10s | Depends on network latency |
| Simple validation (row count) | 1-5s | Per table pair |
| Complex validation (FK check) | 10-30s | Depends on data volume |
| Pipeline execution (10 steps) | 30-120s | Parallel execution |
| Results loading | < 2s | With pagination |
| Dashboard render | < 1s | Initial page load |

**Bottlenecks**
1. **Network latency** to source/target databases (mitigate with same-region deployment)
2. **Large dataset queries** (mitigate with sampling strategies)
3. **Complex FK validations** (mitigate with indexed columns)
4. **Workload analysis parsing** (mitigate with background jobs)

---

## Monitoring & Observability

### Logging Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Logging Layers                        │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Application Logs (Backend)                             │
│  ├─ Location: /app/logs/                               │
│  ├─ Format: JSON structured logging                    │
│  ├─ Levels: DEBUG, INFO, WARNING, ERROR, CRITICAL      │
│  └─ Rotation: Daily, keep 30 days                      │
│                                                         │
│  Container Logs                                         │
│  ├─ View: docker compose logs -f                       │
│  ├─ Backend: docker logs studio-backend                │
│  └─ Frontend: docker logs studio-frontend              │
│                                                         │
│  System Logs                                            │
│  ├─ Ubuntu: journalctl -u ombudsman-studio -f          │
│  └─ Windows: Event Viewer → Applications               │
│                                                         │
│  Database Logs                                          │
│  ├─ SQL Server: Error log, Query Store                 │
│  ├─ Snowflake: Query history, audit logs               │
│  └─ OVS DB: Application transaction logs               │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Health Checks

```yaml
# Docker Compose health checks
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s
```

```python
# Backend health endpoint
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "services": {
            "database": check_db_connection(),
            "cache": check_cache_connection()
        }
    }
```

---

## Disaster Recovery

### Backup Strategy

**What to Backup**
1. **OVS Studio Database** (critical)
   - User accounts
   - Projects and configurations
   - Pipeline definitions
   - Execution history

2. **Configuration Files**
   - `.env` file
   - `docker-compose.yml`
   - Mapping YAML files

3. **Custom Validation Scripts**
   - Business rule validations
   - Custom query definitions

**Backup Script** (automated)
```bash
#!/bin/bash
# Automated backup script (run daily via cron)

BACKUP_DIR=/opt/ombudsman-studio/backups
DATE=$(date +%Y%m%d-%H%M%S)

# 1. Backup OVS Studio database
docker exec studio-backend \
  python -c "
from ombudsman.bootstrap import backup_database
backup_database('$BACKUP_DIR/ovs_db_$DATE.sql')
"

# 2. Backup configuration
cp /opt/ombudsman-validation-studio/.env $BACKUP_DIR/env_$DATE.bak
cp /opt/ombudsman-validation-studio/docker-compose.yml $BACKUP_DIR/compose_$DATE.yml

# 3. Remove backups older than 30 days
find $BACKUP_DIR -type f -mtime +30 -delete
```

### Restore Procedure

```bash
# 1. Stop services
cd /opt/ombudsman-validation-studio
docker compose down

# 2. Restore configuration
cp $BACKUP_DIR/env_YYYYMMDD.bak .env
cp $BACKUP_DIR/compose_YYYYMMDD.yml docker-compose.yml

# 3. Restore database
docker exec studio-backend \
  python -c "
from ombudsman.bootstrap import restore_database
restore_database('$BACKUP_DIR/ovs_db_YYYYMMDD.sql')
"

# 4. Restart services
docker compose up -d
```

---

## Future Architecture Enhancements

### Potential Improvements

1. **Horizontal Scaling** (Kubernetes deployment)
   - Multiple backend replicas
   - Load balancer
   - Shared cache (Redis)

2. **Microservices Decomposition**
   - Separate validation service
   - Separate metadata service
   - Message queue (RabbitMQ/Kafka)

3. **Advanced Caching**
   - Redis for query results
   - CDN for frontend assets

4. **Real-time Features**
   - WebSocket for live pipeline execution updates
   - Real-time collaboration

5. **Enhanced Monitoring**
   - Prometheus metrics
   - Grafana dashboards
   - ELK stack for log aggregation

6. **AI/ML Integration**
   - Anomaly detection in validation results
   - Intelligent mapping suggestions (ML-based)
   - Predictive performance optimization

---

## Glossary

- **OVS**: Ombudsman Validation Studio
- **DAG**: Directed Acyclic Graph (pipeline execution order)
- **SCD**: Slowly Changing Dimension
- **FK**: Foreign Key
- **JWT**: JSON Web Token
- **ODBC**: Open Database Connectivity
- **TDS**: Tabular Data Stream (SQL Server protocol)
- **ASGI**: Asynchronous Server Gateway Interface
- **SPA**: Single Page Application

---

**Document Version**: 1.0
**Last Updated**: 2025-12-15
**Maintained By**: Ombudsman Development Team
