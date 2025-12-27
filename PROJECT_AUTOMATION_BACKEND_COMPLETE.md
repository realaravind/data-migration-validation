# Project Automation Backend - Implementation Complete

## Overview

The backend automation system is now fully implemented. This document describes the complete workflow, API endpoints, and frontend integration requirements.

## Backend Components Implemented

### 1. Project Automation Module
**File**: `backend/projects/automation.py`

Core automation logic that handles:
- Metadata extraction for all tables (reuses `MetadataLoader`)
- Relationship inference (reuses `RelationshipInferrer`)
- Data persistence to project directory
- Status tracking

**Key Methods**:
- `extract_all_metadata(connection, schema)` - Extract metadata from SQL Server or Snowflake
- `infer_relationships(metadata)` - Infer FK relationships from metadata
- `get_metadata()` / `get_relationships()` - Retrieve saved data
- `save_relationships(relationships)` - Save user-edited relationships
- `get_setup_status()` - Check if project is ready for automation

### 2. Project API Endpoints
**File**: `backend/projects/manager.py`

Four new endpoints added:

#### POST `/projects/{project_id}/setup`
Extract metadata and infer relationships for a project.

**Request Body**:
```json
{
  "connection": "sqlserver",  // or "snowflake"
  "schema": "dbo"  // optional
}
```

**Response**:
```json
{
  "status": "success",
  "message": "Metadata extracted and relationships inferred for Project Name",
  "table_count": 15,
  "relationship_count": 23,
  "metadata": {
    "schema.table1": {
      "columns": {"col1": "INT", "col2": "VARCHAR"},
      "schema": "dbo",
      "table": "table1",
      "object_type": "TABLE"
    },
    ...
  },
  "relationships": [
    {
      "fact_table": "fact_sales",
      "fk_column": "customer_id",
      "dim_table": "dim_customer",
      "dim_column": "customer_id",
      "confidence": "high",
      "reason": "Column name match + fact/dim pattern"
    },
    ...
  ]
}
```

#### GET `/projects/{project_id}/relationships`
Get inferred relationships for a project.

**Response**:
```json
{
  "status": "success",
  "relationship_count": 23,
  "relationships": [ /* array of relationships */ ]
}
```

#### PUT `/projects/{project_id}/relationships`
Update relationships after user validation/editing.

**Request Body**:
```json
[
  {
    "fact_table": "fact_sales",
    "fk_column": "customer_id",
    "dim_table": "dim_customer",
    "dim_column": "customer_id",
    "confidence": "high",
    "reason": "User validated"
  },
  ...
]
```

**Response**:
```json
{
  "status": "success",
  "message": "Relationships updated for Project Name",
  "relationship_count": 23
}
```

#### GET `/projects/{project_id}/status`
Check project setup status.

**Response**:
```json
{
  "status": "success",
  "project_name": "My Project",
  "has_metadata": true,
  "has_relationships": true,
  "table_count": 15,
  "relationship_count": 23,
  "ready_for_automation": true
}
```

#### POST `/projects/{project_id}/automate`
**THE KEY ENDPOINT** - Automate pipeline creation for all tables.

This endpoint:
1. Loads metadata and relationships from project
2. Generates intelligent pipelines for ALL tables using `intelligent_suggest` logic
3. Prefixes all pipelines with `{project_name}_`
4. Creates batch file with `{project_name}_batch` naming
5. Saves everything to project directory

**Response**:
```json
{
  "status": "success",
  "message": "Automation completed for project 'My Project'",
  "batch_name": "my_project_batch",
  "batch_file": "/data/projects/my_project/my_project_batch.yaml",
  "pipelines_created": 15,
  "pipelines": [
    {
      "pipeline_name": "my_project_fact_sales",
      "table": "fact_sales",
      "schema": "dbo",
      "file": "/data/projects/my_project/pipelines/my_project_fact_sales.yaml"
    },
    ...
  ]
}
```

## Complete Workflow

### Backend Workflow (COMPLETED)

```
1. Create Project
   POST /projects/create
   → Creates project directory: /data/projects/{project_id}/
   → Saves project.json with metadata

2. Extract Metadata & Infer Relationships
   POST /projects/{project_id}/setup
   → Extracts metadata for ALL tables
   → Infers FK relationships
   → Saves to {project_id}/metadata.json and relationships.json

3. Get Relationships for User Review
   GET /projects/{project_id}/relationships
   → Returns inferred relationships

4. User Validates/Edits Relationships (Frontend)
   → User reviews relationships in UI
   → User can edit, add, delete relationships

5. Save Updated Relationships
   PUT /projects/{project_id}/relationships
   → Saves user-validated relationships

6. Trigger Automation
   POST /projects/{project_id}/automate
   → Generates pipelines for ALL tables
   → Creates batch file
   → Prefixes everything with project name
   → Returns list of created pipelines

7. Execute Batch (Existing endpoint)
   POST /pipelines/execute
   → Execute pipelines from batch file
```

## Frontend Integration Requirements

### 1. ProjectManager or DatabaseMapping Page

Add these functions to call the backend:

```typescript
// Call after project is created
const setupProject = async (projectId: string) => {
  const response = await fetch(`http://localhost:8000/projects/${projectId}/setup`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify({
      connection: 'sqlserver',
      schema: 'dbo'  // or get from user input
    })
  });

  const data = await response.json();

  if (data.status === 'success') {
    // Show success message
    // Display metadata and relationships for review
    setMetadata(data.metadata);
    setRelationships(data.relationships);
  }
};

// Load relationships for editing
const loadRelationships = async (projectId: string) => {
  const response = await fetch(`http://localhost:8000/projects/${projectId}/relationships`, {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });

  const data = await response.json();
  setRelationships(data.relationships);
};

// Save edited relationships
const saveRelationships = async (projectId: string, relationships: any[]) => {
  const response = await fetch(`http://localhost:8000/projects/${projectId}/relationships`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify(relationships)
  });

  const data = await response.json();

  if (data.status === 'success') {
    // Show success message
    alert('Relationships saved successfully!');
  }
};

// THE KEY FUNCTION - Trigger automation
const proceedToAutomation = async (projectId: string) => {
  setLoading(true);

  try {
    const response = await fetch(`http://localhost:8000/projects/${projectId}/automate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      }
    });

    const data = await response.json();

    if (data.status === 'success') {
      alert(`Success! Created ${data.pipelines_created} pipelines.\nBatch: ${data.batch_name}`);

      // Show list of created pipelines
      console.log('Created pipelines:', data.pipelines);

      // Optional: Navigate to pipeline execution page
      // navigate('/pipeline-execution');
    }
  } catch (error) {
    alert(`Error: ${error.message}`);
  } finally {
    setLoading(false);
  }
};
```

### 2. UI Components Needed

#### Relationship Table (for validation/editing)
```tsx
<TableContainer component={Paper}>
  <Table>
    <TableHead>
      <TableRow>
        <TableCell>Fact Table</TableCell>
        <TableCell>FK Column</TableCell>
        <TableCell>Dim Table</TableCell>
        <TableCell>Dim Column</TableCell>
        <TableCell>Confidence</TableCell>
        <TableCell>Reason</TableCell>
        <TableCell>Actions</TableCell>
      </TableRow>
    </TableHead>
    <TableBody>
      {relationships.map((rel, idx) => (
        <TableRow key={idx}>
          <TableCell>{rel.fact_table}</TableCell>
          <TableCell>{rel.fk_column}</TableCell>
          <TableCell>{rel.dim_table}</TableCell>
          <TableCell>{rel.dim_column}</TableCell>
          <TableCell>
            <Chip
              label={rel.confidence}
              color={rel.confidence === 'high' ? 'success' : 'warning'}
              size="small"
            />
          </TableCell>
          <TableCell>{rel.reason}</TableCell>
          <TableCell>
            <IconButton onClick={() => deleteRelationship(idx)}>
              <DeleteIcon />
            </IconButton>
          </TableCell>
        </TableRow>
      ))}
    </TableBody>
  </Table>
</TableContainer>
```

#### "Proceed to Intelligence Automation" Button
```tsx
<Button
  variant="contained"
  color="primary"
  size="large"
  onClick={() => proceedToAutomation(currentProject.project_id)}
  disabled={!readyForAutomation || loading}
  startIcon={loading ? <CircularProgress size={20} /> : <PlayArrowIcon />}
  sx={{ mt: 2, mb: 2 }}
>
  {loading ? 'Creating Pipelines...' : 'Proceed to Intelligence Automation'}
</Button>
```

## Data Storage Structure

```
/data/projects/{project_id}/
├── project.json                    # Project metadata
├── metadata.json                   # Table metadata (from extraction)
├── relationships.json              # Inferred relationships (user-editable)
├── {project_name}_batch.yaml       # Batch file (after automation)
└── pipelines/                      # Generated pipelines (after automation)
    ├── {project_name}_table1.yaml
    ├── {project_name}_table1.meta.json
    ├── {project_name}_table2.yaml
    ├── {project_name}_table2.meta.json
    ...
```

## Example: Complete Flow

```bash
# 1. Create project
curl -X POST http://localhost:8000/projects/create \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "name": "Sales Analytics",
    "description": "Sales data migration validation",
    "sql_database": "SampleDW",
    "sql_schemas": ["dbo", "fact", "dim"],
    "snowflake_database": "SAMPLEDW",
    "snowflake_schemas": ["PUBLIC", "FACT", "DIM"]
  }'

# 2. Extract metadata and infer relationships
curl -X POST http://localhost:8000/projects/sales_analytics/setup \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "connection": "sqlserver",
    "schema": "dbo"
  }'

# 3. Get relationships for user review
curl http://localhost:8000/projects/sales_analytics/relationships \
  -H "Authorization: Bearer $TOKEN"

# 4. User reviews and edits relationships in UI, then saves
curl -X PUT http://localhost:8000/projects/sales_analytics/relationships \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '[
    {
      "fact_table": "fact_sales",
      "fk_column": "customer_id",
      "dim_table": "dim_customer",
      "dim_column": "customer_id",
      "confidence": "high",
      "reason": "User validated"
    }
  ]'

# 5. Trigger automation (THE KEY STEP)
curl -X POST http://localhost:8000/projects/sales_analytics/automate \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN"

# Response:
{
  "status": "success",
  "message": "Automation completed for project 'Sales Analytics'",
  "batch_name": "sales_analytics_batch",
  "pipelines_created": 15,
  "pipelines": [
    {
      "pipeline_name": "sales_analytics_fact_sales",
      "table": "fact_sales",
      "schema": "dbo",
      "file": "/data/projects/sales_analytics/pipelines/sales_analytics_fact_sales.yaml"
    },
    ...
  ]
}

# 6. Execute batch (using existing endpoint)
# Load the batch file and execute pipelines
curl -X POST http://localhost:8000/pipelines/execute \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "pipeline_yaml": "<batch file contents>",
    "pipeline_name": "sales_analytics_batch"
  }'
```

## Key Implementation Notes

### No Code Duplication (As Requested)
✅ Reuses existing `MetadataLoader` from ombudsman_core
✅ Reuses existing `RelationshipInferrer` from ombudsman_core
✅ Reuses existing `intelligent_suggest` logic for pipeline generation
✅ Reuses existing pipeline execution infrastructure

### Project Name Prefixing (As Requested)
✅ All pipelines prefixed with `{project_name}_`
✅ Batch file named `{project_name}_batch`
✅ Clean naming convention: spaces replaced with underscores, lowercase

### Complete Automation (As Requested)
✅ Generates pipelines for ALL tables (not just selected ones)
✅ Creates batch file automatically
✅ Ready for execution

## Next Steps (Frontend)

1. **Add Automation Button to DatabaseMapping.tsx**
   - Add button below relationship table
   - Wire up to `/automate` endpoint
   - Show progress/success message

2. **Display Relationships for Validation**
   - Load relationships from `/relationships` endpoint
   - Show in editable table
   - Allow user to add/edit/delete
   - Save button calls PUT `/relationships`

3. **Show Automation Results**
   - After automation completes, show list of created pipelines
   - Optionally navigate to pipeline execution page

## Testing

```bash
# Check if backend is running
curl http://localhost:8000/health

# Test the complete flow (see example above)
```

## Summary

✅ **Backend is 100% complete**:
- Project automation module
- 4 new API endpoints
- Batch generation logic
- All code reuse as requested
- Project name prefixing as requested
- Automation for ALL tables as requested

⏳ **Frontend remaining**:
- Wire up automation button
- Display relationships for editing
- Handle automation results

The heavy lifting is done. Frontend integration should be straightforward using the examples above.
