# Ombudsman Core → Validation Studio Feature Mapping

## 📋 All Ombudsman Core Features

### 1. **CLI Commands** (ombudsman_core/src/ombudsman/cli/)
```bash
ombudsman validate <pipeline.yaml>     # Run validation pipeline
ombudsman user-add <username>          # Add user
ombudsman user-delete <username>       # Delete user
ombudsman user-list                    # List all users
ombudsman user-set-role <user> <role>  # Set user role
ombudsman user-change-password <user>  # Change password
```

### 2. **Scripts** (ombudsman_core/src/ombudsman/scripts/)
- `generate_sample_data.py` - Create synthetic test data
- `generate_ddl.py` - Generate DDL statements
- `test_sqlserver.py` - Test SQL Server connection
- `test_snowflake.py` - Test Snowflake connection

### 3. **Core Libraries** (ombudsman_core/src/ombudsman/core/)
- ✅ `metadata_loader.py` - Extract table metadata (IMPLEMENTED)
- ✅ `mapping_loader.py` - Generate column mappings (IMPLEMENTED)
- `connections.py` - Database connections
- `registry.py` - Validation registry
- `sqlserver_conn.py` - SQL Server operations
- `snowflake_conn.py` - Snowflake operations

### 4. **Pipeline Features** (ombudsman_core/src/ombudsman/pipeline/)
- `pipeline_runner.py` - Execute validation pipelines
- `step_executor.py` - Run individual validation steps
- WebSocket real-time updates
- Store results in Snowflake

### 5. **Validation Features** (ombudsman_core/src/ombudsman/validation/)
- Row count validation
- Null value checks
- Metric sum validation
- Data type validation
- Referential integrity checks
- Custom validation rules

---

## 🔌 Current Studio Backend APIs (Port 8000)

### ✅ Implemented
- `POST /metadata/extract` - Extract table metadata
- `POST /mapping/suggest` - Generate column mappings
- `GET /health` - Health check
- `GET /execution/results` - Fetch validation results

### ❌ Missing (Need to Implement)
- Pipeline execution
- Sample data generation
- DDL generation
- Connection testing
- User management
- Validation rule management
- Real-time WebSocket updates
- Mermaid diagram generation

---

## 🎯 Implementation Plan

### Phase 1: Essential Features
1. **Pipeline Execution API**
   - `POST /pipelines/execute` - Run a validation pipeline
   - `GET /pipelines/list` - List available pipelines
   - `GET /pipelines/{id}/status` - Get pipeline status
   - `GET /pipelines/{id}/results` - Get pipeline results

2. **Sample Data API**
   - `POST /data/generate` - Generate sample data
   - `GET /data/schemas` - List available schemas

3. **Connection Testing API**
   - `POST /connections/test/sqlserver` - Test SQL Server
   - `POST /connections/test/snowflake` - Test Snowflake
   - `GET /connections/status` - Get all connection statuses

### Phase 2: Advanced Features
4. **Validation Rules API**
   - `GET /rules/list` - List all validation rules
   - `POST /rules/create` - Create custom rule
   - `PUT /rules/{id}` - Update rule
   - `DELETE /rules/{id}` - Delete rule

5. **User Management API**
   - `GET /users/list` - List all users
   - `POST /users/create` - Create user
   - `DELETE /users/{username}` - Delete user
   - `PUT /users/{username}/role` - Set user role
   - `PUT /users/{username}/password` - Change password

6. **Real-time Updates**
   - `WS /ws/pipeline/{id}` - WebSocket for pipeline updates
   - `WS /ws/validation` - WebSocket for validation events

### Phase 3: Visualization
7. **Diagram Generation API**
   - `POST /diagrams/mermaid` - Generate Mermaid diagram
   - `POST /diagrams/pipeline` - Generate pipeline flow diagram
   - `GET /diagrams/{id}` - Get diagram by ID

8. **DDL Generation API**
   - `POST /ddl/generate` - Generate DDL for tables
   - `POST /ddl/compare` - Compare schemas

---

## 🚀 Quick Implementation Strategy

### Option A: Wrap CLI Commands
```python
# backend/cli_wrapper.py
import subprocess

def run_validation(pipeline_file):
    result = subprocess.run(
        ["ombudsman", "validate", pipeline_file],
        capture_output=True
    )
    return result.stdout
```

### Option B: Direct Library Import (Better)
```python
# backend/pipeline/execute.py
from ombudsman.pipeline.pipeline_runner import PipelineRunner
from ombudsman.pipeline.step_executor import StepExecutor

def execute_pipeline(pipeline_yaml):
    runner = PipelineRunner(executor, logger)
    results = runner.run(steps)
    return results
```

---

## 📊 Feature Matrix

| Feature | Core Has | Studio Backend | Studio Frontend | Priority |
|---------|----------|----------------|-----------------|----------|
| Metadata Extraction | ✅ | ✅ | ❌ | High |
| Column Mapping | ✅ | ✅ | ❌ | High |
| Pipeline Execution | ✅ | ❌ | ❌ | **Critical** |
| Sample Data Gen | ✅ | ❌ | ❌ | High |
| Connection Test | ✅ | ❌ | ❌ | High |
| User Management | ✅ | ❌ | ❌ | Medium |
| Real-time Updates | ✅ | ❌ | ❌ | Medium |
| Mermaid Diagrams | ✅ | ❌ | ❌ | Low |
| DDL Generation | ✅ | ❌ | ❌ | Low |
| Validation Rules | ✅ | ❌ | ❌ | Medium |

---

## 🎨 Frontend Features Needed

### Dashboard View
- Connection status indicators
- Recent pipeline executions
- Validation statistics
- Quick actions menu

### Pipeline Management
- Upload/create pipelines
- Execute pipelines
- View results
- Real-time progress
- Historical runs

### Data Management
- Generate sample data
- View table schemas
- Test connections
- Import/export data

### Validation Rules
- View available rules
- Create custom rules
- Test rules
- Rule templates

### User Management (Admin)
- List users
- Add/remove users
- Assign roles
- Change passwords

---

## 🔧 Next Steps

1. **Create comprehensive backend API** - Expose all core features
2. **Build frontend components** - UI for each feature
3. **Add WebSocket support** - Real-time updates
4. **Implement authentication** - User login/roles
5. **Add documentation** - API docs with Swagger

---

**Goal:** Make EVERY ombudsman_core feature accessible through the Studio UI!
