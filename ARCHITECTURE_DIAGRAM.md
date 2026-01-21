This document contains visual architecture diagrams in Mermaid format that can be rendered in GitHub, GitLab, or any Mermaid-compatible viewer.

---

## 1. System Architecture - High Level

```mermaid
graph TB
    subgraph "User Layer"
        U1[Web Browser<br/>Chrome/Firefox/Safari]
    end

    subgraph "VM - Ubuntu 22.04 / Windows Server"
        subgraph "Docker Engine"
            subgraph "Docker Compose Network"
                FE[Frontend Container<br/>React + Vite + Nginx<br/>Port 3000]
                BE[Backend Container<br/>FastAPI + Python 3.11<br/>Port 8000]
            end
        end
        ENV[Environment Config<br/>.env file]
        SYS[Systemd Service<br/>Auto-start]
    end

    subgraph "Core Library"
        CORE[Ombudsman Core<br/>Validation Modules<br/>Pipeline Engine]
    end

    subgraph "External Databases"
        SQL[(SQL Server<br/>Source DW<br/>Port 1433)]
        SNOW[(Snowflake<br/>Target DW<br/>Port 443)]
        OVS[(OVS Studio DB<br/>Application Data<br/>Port 1433)]
    end

    U1 -->|HTTPS :3000| FE
    FE -->|REST API :8000| BE
    BE -->|Uses| CORE
    BE -.->|Reads from| ENV
    SYS -.->|Manages| Docker
    CORE -->|Connects| SQL
    CORE -->|Connects| SNOW
    BE -->|Stores| OVS

    style FE fill:#4CAF50
    style BE fill:#2196F3
    style CORE fill:#FF9800
    style SQL fill:#E91E63
    style SNOW fill:#00BCD4
    style OVS fill:#9C27B0
```

---

## 2. Component Architecture

```mermaid
graph LR
    subgraph "Frontend - React SPA"
        LP[Landing Page]
        PM[Project Manager]
        DM[Database Mapping]
        ME[Metadata Extraction]
        PB[Pipeline Builder]
        WA[Workload Analysis]
        CV[Comparison Viewer]
        RV[Results Viewer]
        UP[User Profile]
    end

    subgraph "Backend - FastAPI"
        AUTH[Auth Router<br/>/auth/*]
        PROJ[Projects Router<br/>/projects/*]
        META[Metadata Router<br/>/metadata/*]
        MAP[Mapping Router<br/>/mapping/*]
        PIPE[Pipelines Router<br/>/pipelines/*]
        WORK[Workload Router<br/>/workload/*]
        EXEC[Execution Router<br/>/execution/*]
        CONN[Connections Router<br/>/connections/*]
    end

    subgraph "Core Library"
        VAL[Validation Modules<br/>30+ validators]
        RUNNER[Pipeline Runner]
        LOADER[Metadata Loader]
        MAPPER[Mapping Loader]
        CONNMGR[Connection Manager]
    end

    LP --> PROJ
    PM --> PROJ
    DM --> MAP
    ME --> META
    PB --> PIPE
    WA --> WORK
    CV --> EXEC
    RV --> EXEC
    UP --> AUTH

    AUTH --> CONNMGR
    PROJ --> CONNMGR
    META --> LOADER
    MAP --> MAPPER
    PIPE --> RUNNER
    WORK --> LOADER
    EXEC --> RUNNER

    RUNNER --> VAL
    VAL --> CONNMGR

    style LP fill:#E3F2FD
    style PM fill:#E3F2FD
    style DM fill:#E3F2FD
    style ME fill:#E3F2FD
    style PB fill:#E3F2FD
    style WA fill:#E3F2FD
    style CV fill:#E3F2FD
    style RV fill:#E3F2FD
    style UP fill:#E3F2FD
    style AUTH fill:#BBDEFB
    style PROJ fill:#BBDEFB
    style META fill:#BBDEFB
    style MAP fill:#BBDEFB
    style PIPE fill:#BBDEFB
    style WORK fill:#BBDEFB
    style EXEC fill:#BBDEFB
    style CONN fill:#BBDEFB
    style VAL fill:#90CAF9
    style RUNNER fill:#90CAF9
    style LOADER fill:#90CAF9
    style MAPPER fill:#90CAF9
    style CONNMGR fill:#90CAF9
```

---

## 3. Data Flow - User Authentication

```mermaid
sequenceDiagram
    participant B as Browser
    participant FE as Frontend
    participant BE as Backend
    participant DB as OVS Studio DB

    B->>FE: 1. Enter credentials
    FE->>BE: 2. POST /auth/login<br/>{username, password}
    BE->>BE: 3. Validate credentials<br/>bcrypt.verify()
    BE->>DB: 4. Query user table
    DB-->>BE: 5. User record
    BE->>BE: 6. Generate JWT token<br/>jwt.encode()
    BE-->>FE: 7. Return token<br/>{access_token, token_type}
    FE->>FE: 8. Store in localStorage
    FE-->>B: 9. Redirect to dashboard

    Note over B,DB: Subsequent requests include:<br/>Authorization: Bearer <token>

    B->>FE: 10. Access protected page
    FE->>BE: 11. GET /projects/<br/>Authorization: Bearer <token>
    BE->>BE: 12. Verify JWT token<br/>jwt.decode()
    BE->>DB: 13. Fetch projects
    DB-->>BE: 14. Projects data
    BE-->>FE: 15. Return projects
    FE-->>B: 16. Display projects
```

---

## 4. Data Flow - Metadata Extraction

```mermaid
sequenceDiagram
    participant U as User
    participant FE as Frontend
    participant BE as Backend
    participant CORE as Metadata Loader
    participant SQL as SQL Server
    participant SNOW as Snowflake

    U->>FE: 1. Click "Extract Metadata"
    FE->>BE: 2. POST /metadata/extract<br/>{source_config, target_config}
    BE->>CORE: 3. Call extract_metadata()

    par Extract from Source
        CORE->>SQL: 4a. Connect & Query<br/>INFORMATION_SCHEMA.TABLES
        SQL-->>CORE: 5a. Tables list
        CORE->>SQL: 6a. Query<br/>INFORMATION_SCHEMA.COLUMNS
        SQL-->>CORE: 7a. Columns metadata
    and Extract from Target
        CORE->>SNOW: 4b. Connect & Query<br/>INFORMATION_SCHEMA.TABLES
        SNOW-->>CORE: 5b. Tables list
        CORE->>SNOW: 6b. Query<br/>INFORMATION_SCHEMA.COLUMNS
        SNOW-->>CORE: 7b. Columns metadata
    end

    CORE->>CORE: 8. Aggregate & format
    CORE-->>BE: 9. Return metadata JSON
    BE-->>FE: 10. Return to frontend
    FE->>FE: 11. Display in tables
    FE-->>U: 12. Show metadata UI
```

---

## 5. Data Flow - Pipeline Execution

```mermaid
sequenceDiagram
    participant U as User
    participant FE as Frontend
    participant BE as Backend
    participant RUNNER as Pipeline Runner
    participant EXEC as Step Executor
    participant VAL as Validation Module
    participant SQL as SQL Server
    participant SNOW as Snowflake
    participant DB as OVS Studio DB

    U->>FE: 1. Click "Execute Pipeline"
    FE->>BE: 2. POST /pipelines/{id}/execute
    BE->>RUNNER: 3. Load pipeline config
    RUNNER->>RUNNER: 4. Build dependency DAG
    RUNNER->>RUNNER: 5. Group steps by level

    loop For each level (parallel execution)
        RUNNER->>EXEC: 6. Execute step
        EXEC->>VAL: 7. Load validation module<br/>(e.g., validate_record_counts.py)

        par Query Source and Target
            VAL->>SQL: 8a. Execute validation query
            SQL-->>VAL: 9a. Source results
        and
            VAL->>SNOW: 8b. Execute validation query
            SNOW-->>VAL: 9b. Target results
        end

        VAL->>VAL: 10. Compare results<br/>Check pass/fail
        VAL-->>EXEC: 11. Return step result
        EXEC-->>RUNNER: 12. Collect result
    end

    RUNNER->>RUNNER: 13. Aggregate all results
    RUNNER->>DB: 14. Save execution results
    DB-->>RUNNER: 15. execution_id
    RUNNER-->>BE: 16. Return execution_id
    BE-->>FE: 17. Return execution_id
    FE->>FE: 18. Navigate to Results Viewer
    FE->>BE: 19. GET /execution/results/{id}
    BE->>DB: 20. Fetch results
    DB-->>BE: 21. Results data
    BE-->>FE: 22. Return results JSON
    FE-->>U: 23. Display results
```

---

## 6. Validation Module Architecture

```mermaid
graph TB
    subgraph "Validation Categories"
        SCHEMA[Schema Validation<br/>3 modules]
        DQ[Data Quality<br/>8 modules]
        RI[Referential Integrity<br/>1 module]
        DIM[Dimension Validation<br/>5 modules]
        FACT[Fact Validation<br/>2 modules]
        METRIC[Metrics Validation<br/>3 modules]
        TS[Time Series<br/>4 modules]
        BIZ[Business Rules<br/>Custom]
    end

    subgraph "Schema Validation"
        S1[validate_schema_columns<br/>Column existence]
        S2[validate_schema_datatypes<br/>Data type matching]
        S3[validate_schema_nullability<br/>NULL constraints]
    end

    subgraph "Data Quality"
        D1[validate_record_counts<br/>Row count comparison]
        D2[validate_nulls<br/>NULL validation]
        D3[validate_uniqueness<br/>Unique constraints]
        D4[validate_statistics<br/>Statistical validation]
        D5[validate_distribution<br/>Distribution analysis]
        D6[validate_outliers<br/>Outlier detection]
        D7[validate_domain_values<br/>Domain validation]
        D8[validate_regex_patterns<br/>Pattern matching]
    end

    subgraph "Referential Integrity"
        R1[validate_foreign_keys<br/>FK constraint validation]
    end

    subgraph "Dimension Validation"
        DM1[validate_dim_business_keys<br/>Business key validation]
        DM2[validate_dim_surrogate_keys<br/>Surrogate key validation]
        DM3[validate_scd1<br/>SCD Type 1]
        DM4[validate_scd2<br/>SCD Type 2]
        DM5[validate_composite_keys<br/>Composite keys]
    end

    subgraph "Fact Validation"
        F1[validate_fact_dim_conformance<br/>Fact-dimension conformance]
        F2[validate_late_arriving_facts<br/>Late arriving facts]
    end

    subgraph "Metrics Validation"
        M1[validate_metric_sums<br/>Sum validation]
        M2[validate_metric_averages<br/>Average validation]
        M3[validate_ratios<br/>Ratio validation]
    end

    subgraph "Time Series"
        T1[validate_ts_continuity<br/>Continuity validation]
        T2[validate_ts_duplicates<br/>Duplicate detection]
        T3[validate_ts_rolling_drift<br/>Drift detection]
        T4[validate_period_over_period<br/>Period comparison]
    end

    SCHEMA --> S1 & S2 & S3
    DQ --> D1 & D2 & D3 & D4 & D5 & D6 & D7 & D8
    RI --> R1
    DIM --> DM1 & DM2 & DM3 & DM4 & DM5
    FACT --> F1 & F2
    METRIC --> M1 & M2 & M3
    TS --> T1 & T2 & T3 & T4

    style SCHEMA fill:#E8F5E9
    style DQ fill:#E3F2FD
    style RI fill:#FFF3E0
    style DIM fill:#F3E5F5
    style FACT fill:#FCE4EC
    style METRIC fill:#E0F2F1
    style TS fill:#FFF9C4
    style BIZ fill:#EFEBE9
```

---

## 7. Security Architecture

```mermaid
graph TB
    subgraph "Security Layers"
        L1[Layer 1: Transport Security<br/>HTTPS/TLS 1.3]
        L2[Layer 2: Authentication<br/>JWT + bcrypt]
        L3[Layer 3: Authorization<br/>RBAC]
        L4[Layer 4: Database Security<br/>Parameterized Queries]
        L5[Layer 5: API Security<br/>CORS + Validation]
        L6[Layer 6: Container Security<br/>Non-root execution]
        L7[Layer 7: Network Security<br/>Firewall + VPN]
    end

    L1 --> L2 --> L3 --> L4 --> L5 --> L6 --> L7

    subgraph "Authentication Flow"
        LOGIN[User Login] --> HASH[Password Hash<br/>bcrypt]
        HASH --> VERIFY{Verify<br/>Password}
        VERIFY -->|Success| JWT[Generate JWT<br/>HS256]
        VERIFY -->|Fail| REJECT[Reject]
        JWT --> TOKEN[Return Token]
        TOKEN --> STORE[Store in<br/>localStorage]
        STORE --> AUTH_REQ[Subsequent Requests<br/>Authorization: Bearer]
        AUTH_REQ --> VALIDATE{Validate<br/>JWT}
        VALIDATE -->|Valid| ALLOW[Allow Access]
        VALIDATE -->|Invalid| DENY[Deny Access]
    end

    subgraph "Secrets Management"
        ENV[.env File<br/>Never commit!]
        SECRET1[SQL Server Password]
        SECRET2[Snowflake Password]
        SECRET3[JWT Secret Key]
        SECRET4[OVS DB Password]

        ENV --> SECRET1 & SECRET2 & SECRET3 & SECRET4
    end

    style L1 fill:#FFEBEE
    style L2 fill:#FCE4EC
    style L3 fill:#F3E5F5
    style L4 fill:#EDE7F6
    style L5 fill:#E8EAF6
    style L6 fill:#E3F2FD
    style L7 fill:#E1F5FE
    style JWT fill:#C8E6C9
    style VERIFY fill:#FFF9C4
    style VALIDATE fill:#FFF9C4
    style ENV fill:#FFCCBC
```

---

## 8. Deployment Architecture - Single VM

```mermaid
graph TB
    subgraph "Ubuntu 22.04 LTS / Windows Server 2022"
        subgraph "Docker Engine"
            subgraph "Docker Compose Network"
                FE[studio-frontend<br/>React + Nginx<br/>Port 3000]
                BE[studio-backend<br/>FastAPI + Uvicorn<br/>Port 8000]
            end
        end

        ENV["/opt/ombudsman-validation-studio/.env<br/>Configuration File"]
        COMPOSE["docker-compose.yml"]
        SYSTEMD["systemd service<br/>ombudsman-studio.service<br/>(Auto-start on boot)"]

        subgraph "Host Network"
            P3000["0.0.0.0:3000"]
            P8000["0.0.0.0:8000"]
        end
    end

    subgraph "External Databases"
        SQL[(SQL Server<br/>Source DW<br/>192.168.1.100:1433)]
        SNOW[(Snowflake<br/>Target DW<br/>xyz.us-east-1.aws:443)]
        OVS[(OVS Studio DB<br/>Application Data<br/>192.168.1.100:1433)]
    end

    subgraph "Users"
        USER1[Browser 1]
        USER2[Browser 2]
        USER3[Browser 3]
    end

    USER1 & USER2 & USER3 -->|HTTPS| P3000
    P3000 --> FE
    FE -->|REST API| P8000
    P8000 --> BE
    BE -.->|Reads config| ENV
    SYSTEMD -.->|Manages| COMPOSE
    COMPOSE -.->|Defines| FE & BE

    BE -->|pyodbc<br/>ODBC Driver 18| SQL
    BE -->|snowflake-connector| SNOW
    BE -->|SQLAlchemy| OVS

    style FE fill:#4CAF50
    style BE fill:#2196F3
    style SQL fill:#E91E63
    style SNOW fill:#00BCD4
    style OVS fill:#9C27B0
    style ENV fill:#FF9800
    style SYSTEMD fill:#795548
```

---

## 9. Intelligent Workload Analysis Flow

```mermaid
flowchart TD
    START[User uploads Query Store data] --> PARSE[Parse SQL queries]
    PARSE --> EXTRACT[Extract tables & columns used]
    EXTRACT --> CLASSIFY[Classify columns<br/>Identifiers vs Measures]

    CLASSIFY --> DETECT[Detect query patterns<br/>SUM, AVG, COUNT, JOINs]
    DETECT --> METADATA[Match with extracted metadata]

    METADATA --> INFER[Infer relationships<br/>FK patterns]
    INFER --> SUGGEST[Generate intelligent suggestions]

    SUGGEST --> SUG1[Validate SUM on Amount columns]
    SUGGEST --> SUG2[Validate FK to Customer]
    SUGGEST --> SUG3[Validate fact-dim conformance]
    SUGGEST --> SUG4[Validate SCD Type 2]

    SUG1 & SUG2 & SUG3 & SUG4 --> DISPLAY[Display suggestions to user]
    DISPLAY --> USER_CLICK{User clicks<br/>'Add to Pipeline'}
    USER_CLICK -->|Yes| ADD[Add step to pipeline builder]
    USER_CLICK -->|No| END[End]
    ADD --> END

    style START fill:#E8F5E9
    style CLASSIFY fill:#E3F2FD
    style INFER fill:#FFF3E0
    style SUGGEST fill:#F3E5F5
    style DISPLAY fill:#E1F5FE
    style ADD fill:#C8E6C9
```

---

## 10. Technology Stack Overview

```mermaid
graph LR
    subgraph "Frontend Stack"
        FE_CORE[React 18.3.1<br/>TypeScript 5.6.2<br/>Vite 5.4.2]
        FE_UI[Material-UI 6.3.0<br/>Emotion CSS-in-JS]
        FE_ROUTE[React Router 7.1.1]
        FE_HTTP[Fetch API]
    end

    subgraph "Backend Stack"
        BE_CORE[FastAPI 0.115.6<br/>Python 3.11<br/>Uvicorn ASGI]
        BE_DB[pyodbc 5.2.0<br/>snowflake-connector<br/>SQLAlchemy]
        BE_AUTH[python-jose JWT<br/>passlib bcrypt]
        BE_UTIL[PyYAML<br/>fuzzywuzzy<br/>pandas]
    end

    subgraph "Core Library"
        CORE_LANG[Python 3.11+]
        CORE_DB[pyodbc<br/>snowflake-connector<br/>psycopg2]
        CORE_DATA[pandas<br/>numpy<br/>scipy]
        CORE_GRAPH[networkx DAG]
    end

    subgraph "Infrastructure"
        INFRA_DOCKER[Docker Engine 24.0+<br/>Docker Compose 2.20+]
        INFRA_SYS[systemd Ubuntu<br/>Task Scheduler Windows]
    end

    FE_CORE --> FE_UI & FE_ROUTE & FE_HTTP
    BE_CORE --> BE_DB & BE_AUTH & BE_UTIL
    CORE_LANG --> CORE_DB & CORE_DATA & CORE_GRAPH
    INFRA_DOCKER --> FE_CORE & BE_CORE
    INFRA_SYS -.->|Manages| INFRA_DOCKER

    style FE_CORE fill:#4CAF50
    style BE_CORE fill:#2196F3
    style CORE_LANG fill:#FF9800
    style INFRA_DOCKER fill:#9C27B0
```

---

## 11. Database Schema - OVS Studio DB

```mermaid
erDiagram
    users ||--o{ projects : creates
    users {
        string user_id PK
        string username UK
        string password_hash
        string email
        datetime created_at
        datetime updated_at
    }

    projects ||--o{ pipelines : contains
    projects ||--o{ mappings : has
    projects ||--o{ executions : runs
    projects {
        string project_id PK
        string project_name
        string user_id FK
        json source_config
        json target_config
        datetime created_at
        datetime updated_at
    }

    pipelines ||--o{ pipeline_steps : contains
    pipelines {
        string pipeline_id PK
        string project_id FK
        string pipeline_name
        json config
        datetime created_at
        datetime updated_at
    }

    pipeline_steps {
        string step_id PK
        string pipeline_id FK
        string step_type
        int step_order
        json parameters
        json dependencies
    }

    mappings {
        string mapping_id PK
        string project_id FK
        string source_schema
        string source_table
        string source_column
        string target_schema
        string target_table
        string target_column
        string mapping_type
    }

    executions ||--o{ execution_results : produces
    executions {
        string execution_id PK
        string pipeline_id FK
        string project_id FK
        datetime started_at
        datetime completed_at
        string status
        json summary
    }

    execution_results {
        string result_id PK
        string execution_id FK
        string step_id FK
        string status
        json details
        int duration_ms
    }
```

---

## 12. CI/CD Pipeline (Future Enhancement)

```mermaid
graph LR
    subgraph "Development"
        DEV[Developer] --> COMMIT[Git Commit]
        COMMIT --> PUSH[Git Push]
    end

    subgraph "CI Pipeline"
        PUSH --> BUILD[Docker Build]
        BUILD --> TEST[Run Tests<br/>pytest]
        TEST --> LINT[Linting<br/>ESLint, Black]
        LINT --> SCAN[Security Scan<br/>Trivy]
    end

    subgraph "CD Pipeline"
        SCAN --> TAG[Tag Image<br/>v1.0.0]
        TAG --> REG[Push to Registry<br/>Docker Hub]
        REG --> DEPLOY{Deploy}
    end

    subgraph "Environments"
        DEPLOY -->|Auto| DEV_ENV[Development]
        DEPLOY -->|Manual| STAGE[Staging]
        DEPLOY -->|Manual| PROD[Production]
    end

    style DEV fill:#E8F5E9
    style BUILD fill:#E3F2FD
    style TEST fill:#FFF3E0
    style DEPLOY fill:#F3E5F5
    style PROD fill:#FFCDD2
```

---

## How to View These Diagrams

### Option 1: GitHub/GitLab
Simply view this file in GitHub or GitLab - they render Mermaid diagrams automatically.

### Option 2: VS Code
Install the "Markdown Preview Mermaid Support" extension:
```bash
code --install-extension bierner.markdown-mermaid
```

### Option 3: Online Viewer
Copy any diagram code block to:
- https://mermaid.live/
- https://mermaid-js.github.io/mermaid-live-editor/

### Option 4: CLI Tool
Install mermaid-cli:
```bash
npm install -g @mermaid-js/mermaid-cli
mmdc -i ARCHITECTURE_DIAGRAM.md -o architecture.pdf
```

---

**Document Version**: 1.0
**Last Updated**: 2025-12-15
**Maintained By**: Ombudsman Development Team
