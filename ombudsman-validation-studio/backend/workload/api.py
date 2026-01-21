"""
Workload API Endpoints
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Body
from fastapi.responses import FileResponse
from typing import List, Dict, Optional
from pydantic import BaseModel
import json
from pathlib import Path

from .storage import WorkloadStorage
from .engine import WorkloadEngine
from .pipeline_generator import PipelineGenerator


router = APIRouter()
storage = WorkloadStorage()
engine = WorkloadEngine(storage=storage)
pipeline_gen = PipelineGenerator()


class WorkloadAnalyzeRequest(BaseModel):
    workload_id: str
    project_id: str
    metadata: Optional[Dict[str, Dict[str, str]]] = None  # table -> column -> datatype


class WorkloadSummary(BaseModel):
    workload_id: str
    upload_date: str
    query_count: int
    total_executions: int
    tables_count: int


@router.post("/upload")
async def upload_workload(
    file: UploadFile = File(...),
    project_id: str = Body(...)
):
    """
    Upload a Query Store JSON workload file

    Returns:
        - workload_id: Unique identifier
        - summary: Basic workload statistics
    """
    try:
        # Read and parse JSON
        content = await file.read()
        queries_data = json.loads(content)

        # Ensure it's a list
        if not isinstance(queries_data, list):
            raise HTTPException(status_code=400, detail="Expected a JSON array of queries")

        # Process workload
        workload_data = engine.process_query_store_json(queries_data)

        # Save to storage
        workload_id = storage.save_workload(project_id, workload_data)

        # Return summary
        return {
            "workload_id": workload_id,
            "summary": {
                "total_queries": workload_data['query_count'],
                "total_executions": workload_data['total_executions'],
                "tables_found": len(workload_data.get('table_usage', {})),
                "date_range": workload_data.get('date_range', {}),
                "upload_date": workload_data.get('upload_date')
            }
        }

    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON format: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing workload: {str(e)}")


@router.get("/list/{project_id}")
async def list_workloads(project_id: str):
    """
    List all workloads for a project

    Returns:
        List of workload summaries
    """
    try:
        workloads = storage.list_workloads(project_id)
        return {"workloads": workloads}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing workloads: {str(e)}")


# ==================== Pipeline Management Routes ====================
# IMPORTANT: These routes must come BEFORE the generic /{project_id}/{workload_id} route
# to avoid the parameterized route from matching URLs like /pipelines/list

@router.get("/pipelines/list")
async def list_pipelines(project_id: Optional[str] = None, active_only: bool = False):
    """
    List all generated pipelines

    Args:
        project_id: Optional filter by project
        active_only: If True, return only active pipelines

    Returns:
        List of pipeline summaries
    """
    try:
        pipelines = pipeline_gen.list_generated_pipelines(project_id=project_id, active_only=active_only)
        return {
            "pipelines": pipelines,
            "total": len(pipelines)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing pipelines: {str(e)}")


@router.get("/pipelines/{filename}")
async def get_pipeline_content(filename: str):
    """
    Get content of a specific pipeline file

    Args:
        filename: Pipeline filename

    Returns:
        Pipeline YAML content
    """
    try:
        filepath = pipeline_gen.pipelines_dir / filename

        if not filepath.exists():
            raise HTTPException(status_code=404, detail=f"Pipeline file not found: {filename}")

        content = pipeline_gen.get_pipeline_content(str(filepath))

        return {
            "filename": filename,
            "content": content
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading pipeline: {str(e)}")


@router.patch("/pipelines/{filename}/active")
async def update_pipeline_active_status(filename: str, active: bool):
    """
    Update the active status of a pipeline

    Args:
        filename: Pipeline filename
        active: New active status (True/False)

    Returns:
        Success status and message
    """
    try:
        success = pipeline_gen.update_pipeline_active_status(filename, active)

        if not success:
            raise HTTPException(status_code=404, detail=f"Pipeline file not found: {filename}")

        return {
            "success": True,
            "filename": filename,
            "active": active,
            "message": f"Pipeline {filename} marked as {'active' if active else 'inactive'}"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating pipeline status: {str(e)}")


# ==================== Batch Management Routes ====================

class BatchSaveRequest(BaseModel):
    filename: str
    content: Dict  # Batch YAML structure


@router.get("/batch/{batch_name}")
async def get_batch(batch_name: str, project_id: Optional[str] = None):
    """
    Get a specific batch file by name

    Args:
        batch_name: Batch filename (with or without .yaml extension)
        project_id: Optional project filter

    Returns:
        Batch file content
    """
    try:
        from pathlib import Path
        import yaml

        # Ensure .yaml extension
        if not batch_name.endswith('.yaml') and not batch_name.endswith('.yml'):
            batch_name = f"{batch_name}.yaml"

        # Search in project directory first, then global
        search_paths = []
        if project_id:
            search_paths.append(Path(f"/data/projects/{project_id}/pipelines"))
        search_paths.append(Path("/data/pipelines"))
        search_paths.append(Path("/data/batch_jobs"))

        for search_path in search_paths:
            batch_file = search_path / batch_name
            if batch_file.exists():
                with open(batch_file, 'r') as f:
                    content = yaml.safe_load(f)
                return {
                    "filename": batch_name,
                    "path": str(batch_file),
                    **content
                }

        raise HTTPException(status_code=404, detail=f"Batch file '{batch_name}' not found")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading batch file: {str(e)}")


@router.post("/batch/save")
async def save_batch(request: BatchSaveRequest, project_id: Optional[str] = None):
    """
    Save a batch configuration file

    Args:
        request: Batch save request with filename and content
        project_id: Optional project to save to (defaults to active project)

    Returns:
        Success status and file path
    """
    try:
        from pathlib import Path
        import yaml

        # Determine save location
        if project_id:
            batch_dir = Path(f"/data/projects/{project_id}/pipelines")
        else:
            # Try to get active project
            from projects.context import get_active_project
            active = get_active_project()
            if active and active.get("project_id"):
                batch_dir = Path(f"/data/projects/{active['project_id']}/pipelines")
            else:
                batch_dir = Path("/data/batch_jobs")

        batch_dir.mkdir(parents=True, exist_ok=True)

        # Ensure .yaml extension
        filename = request.filename
        if not filename.endswith('.yaml') and not filename.endswith('.yml'):
            filename = f"{filename}.yaml"

        # Save the file
        file_path = batch_dir / filename
        with open(file_path, 'w') as f:
            yaml.dump(request.content, f, default_flow_style=False, sort_keys=False)

        return {
            "status": "success",
            "message": f"Batch file saved successfully",
            "filename": filename,
            "path": str(file_path)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving batch file: {str(e)}")


# ==================== Batch Template Management Routes ====================
# ==================== Workload Management Routes ====================
# Generic parameterized route - must come AFTER specific routes

@router.get("/{project_id}/{workload_id}")
async def get_workload(project_id: str, workload_id: str):
    """
    Get a specific workload by ID

    Returns:
        Complete workload data
    """
    try:
        workload = storage.get_workload(project_id, workload_id)

        if not workload:
            raise HTTPException(status_code=404, detail=f"Workload {workload_id} not found")

        return workload
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving workload: {str(e)}")


@router.delete("/batch/{batch_name}")
async def delete_batch(batch_name: str, project_id: Optional[str] = None, delete_pipelines: bool = False):
    """
    Delete a batch file and optionally its associated pipeline files

    Args:
        batch_name: Batch filename (with or without .yaml extension)
        project_id: Optional project filter
        delete_pipelines: If True, also delete all pipeline files referenced in the batch

    Returns:
        Success status with details of deleted files
    """
    try:
        from pathlib import Path
        import yaml

        print(f"[DELETE_BATCH] Starting batch deletion for: {batch_name}")
        print(f"[DELETE_BATCH] project_id: {project_id}")
        print(f"[DELETE_BATCH] delete_pipelines: {delete_pipelines}")

        # Ensure .yaml extension
        if not batch_name.endswith('.yaml') and not batch_name.endswith('.yml'):
            batch_name = f"{batch_name}.yaml"
            print(f"[DELETE_BATCH] Added .yaml extension, batch_name is now: {batch_name}")

        # Search for batch file in project directory first, then global
        search_paths = []
        if project_id:
            search_paths.append(Path(f"/data/projects/{project_id}/pipelines"))
        search_paths.append(Path("/data/pipelines"))
        search_paths.append(Path("/data/batch_jobs"))

        print(f"[DELETE_BATCH] Will search in these paths:")
        for sp in search_paths:
            print(f"[DELETE_BATCH]   - {sp} (exists: {sp.exists()})")

        batch_file = None
        for search_path in search_paths:
            potential_file = search_path / batch_name
            exists = potential_file.exists()
            print(f"[DELETE_BATCH] Checking: {potential_file} -> exists: {exists}")
            if exists:
                batch_file = potential_file
                print(f"[DELETE_BATCH] ✓ Found batch file at: {batch_file}")
                break

        if not batch_file:
            print(f"[DELETE_BATCH] ✗ Batch file '{batch_name}' not found in any search path")
            raise HTTPException(status_code=404, detail=f"Batch file '{batch_name}' not found")

        deleted_files = []
        deleted_pipelines = []

        # If delete_pipelines is True, read batch file and delete referenced pipelines
        if delete_pipelines:
            try:
                with open(batch_file, 'r') as f:
                    batch_content = yaml.safe_load(f)

                # Extract pipeline references from batch
                pipeline_files = []
                if 'batch' in batch_content and 'pipelines' in batch_content['batch']:
                    pipeline_files = [p.get('file') for p in batch_content['batch']['pipelines'] if p.get('file')]

                # Delete each pipeline file
                batch_dir = batch_file.parent
                for pipeline_file in pipeline_files:
                    pipeline_path = batch_dir / pipeline_file
                    if pipeline_path.exists():
                        pipeline_path.unlink()
                        deleted_pipelines.append(str(pipeline_path))
            except Exception as e:
                print(f"Warning: Could not delete pipeline files: {str(e)}")

        # Delete the batch file
        batch_file.unlink()
        deleted_files.append(str(batch_file))

        return {
            "status": "success",
            "message": f"Batch '{batch_name}' deleted successfully",
            "deleted_batch": str(batch_file),
            "deleted_pipelines": deleted_pipelines,
            "total_deleted": len(deleted_files) + len(deleted_pipelines)
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting batch: {str(e)}")


@router.delete("/pipeline/{pipeline_name}")
async def delete_pipeline(pipeline_name: str, project_id: Optional[str] = None):
    """
    Delete a single pipeline file

    Args:
        pipeline_name: Pipeline filename (with or without .yaml extension)
        project_id: Optional project filter

    Returns:
        Success status
    """
    try:
        from pathlib import Path

        # Ensure .yaml extension
        if not pipeline_name.endswith('.yaml') and not pipeline_name.endswith('.yml'):
            pipeline_name = f"{pipeline_name}.yaml"

        # Search for pipeline file in project directory first, then global
        search_paths = []
        if project_id:
            search_paths.append(Path(f"/data/projects/{project_id}/pipelines"))
        search_paths.append(Path("/data/pipelines"))

        pipeline_file = None
        for search_path in search_paths:
            potential_file = search_path / pipeline_name
            if potential_file.exists():
                pipeline_file = potential_file
                break

        if not pipeline_file:
            raise HTTPException(status_code=404, detail=f"Pipeline file '{pipeline_name}' not found")

        # Delete the pipeline file
        pipeline_file.unlink()

        return {
            "status": "success",
            "message": f"Pipeline '{pipeline_name}' deleted successfully",
            "deleted_file": str(pipeline_file)
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting pipeline: {str(e)}")


@router.delete("/{project_id}/{workload_id}")
async def delete_workload(project_id: str, workload_id: str):
    """
    Delete a workload

    Returns:
        Success status
    """
    try:
        success = storage.delete_workload(project_id, workload_id)

        if not success:
            raise HTTPException(status_code=404, detail=f"Workload {workload_id} not found")

        return {"message": "Workload deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting workload: {str(e)}")


@router.post("/analyze")
async def analyze_workload(request: WorkloadAnalyzeRequest):
    """
    Generate validations from workload queries (PROPER IMPLEMENTATION).

    This creates one validation per unique query using the original SQL from Query Store.
    Deduplicates queries and groups them by table.

    Args:
        workload_id: Workload to analyze
        project_id: Project context

    Returns:
        - tables: Validations grouped by table
        - total_unique_queries: Number of unique queries found
        - deduplication_ratio: Ratio of unique to total queries
    """
    try:
        # Use the new query-based approach (proper implementation)
        result = engine.generate_query_based_validations(
            project_id=request.project_id,
            workload_id=request.workload_id
        )

        # Add coverage object for frontend compatibility
        total_validations = len(result.get('validations', []))
        result['coverage'] = {
            'total_queries': result.get('total_queries', 0),
            'queries_covered': result.get('total_unique_queries', 0),
            'coverage_percentage': result.get('deduplication_ratio', 1.0) * 100,
            'total_executions_covered': sum(v.get('total_executions', 0) for v in result.get('validations', [])),
            'validation_count': total_validations,
            'high_confidence_count': sum(1 for v in result.get('validations', []) if v.get('confidence', 0) >= 0.8),
            'medium_confidence_count': sum(1 for v in result.get('validations', []) if 0.5 <= v.get('confidence', 0) < 0.8),
            'low_confidence_count': sum(1 for v in result.get('validations', []) if v.get('confidence', 0) < 0.5)
        }

        # Add categories for frontend compatibility
        # For workload queries, we just have one category: workload_query
        result['categories'] = {
            'workload_query': total_validations
        }

        return {
            "status": "success",
            "data": result
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing workload: {str(e)}")


@router.get("/coverage/{project_id}/{workload_id}")
async def get_workload_coverage(project_id: str, workload_id: str):
    """
    Get workload coverage metrics

    Returns:
        Coverage statistics
    """
    try:
        workload = storage.get_workload(project_id, workload_id)

        if not workload:
            raise HTTPException(status_code=404, detail=f"Workload {workload_id} not found")

        analysis = workload.get('analysis', {})
        coverage = analysis.get('coverage', {})

        return {
            "workload_id": workload_id,
            "coverage": coverage,
            "analyzed_at": analysis.get('analyzed_at')
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving coverage: {str(e)}")


class PipelineGenerateRequest(BaseModel):
    project_id: str
    workload_id: str
    validations: List[Dict]  # Selected validations from frontend


@router.post("/generate-pipelines")
async def generate_pipelines(request: PipelineGenerateRequest):
    """
    Generate YAML pipeline files from selected validations

    Args:
        project_id: Project identifier
        workload_id: Workload identifier
        validations: List of selected validation suggestions

    Returns:
        - pipeline_files: Dictionary of generated pipelines by table
        - total_tables: Number of tables with pipelines
        - total_validations: Total validations in pipelines
        - file_paths: List of generated file paths
    """
    try:
        if not request.validations:
            raise HTTPException(status_code=400, detail="No validations selected")

        result = pipeline_gen.generate_pipelines(
            validations=request.validations,
            project_id=request.project_id,
            workload_id=request.workload_id
        )

        return {
            "status": "success",
            "message": f"Generated {result['total_tables']} pipeline(s) with {result['total_validations']} validations",
            **result
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating pipelines: {str(e)}")


class ComparativePipelineGenerateRequest(BaseModel):
    project_id: str
    workload_id: str
    schema_mapping: Optional[Dict[str, str]] = None  # SQL Server -> Snowflake schema mapping


@router.post("/generate-comparative-pipelines")
async def generate_comparative_pipelines(request: ComparativePipelineGenerateRequest):
    """
    Generate comparative validation pipelines from Query Store queries.

    This endpoint converts uploaded Query Store queries into comparative validations
    that run the same query on both SQL Server and Snowflake and compare the results.

    Args:
        project_id: Project identifier
        workload_id: Workload identifier
        schema_mapping: Optional SQL Server to Snowflake schema mapping
                       (default: {"dim": "DIM", "fact": "FACT", "dbo": "PUBLIC"})

    Returns:
        - pipeline_files: Dictionary of generated pipelines by table
        - total_tables: Number of tables with pipelines
        - total_validations: Total validations in pipelines
        - file_paths: List of generated file paths
    """
    try:
        # Get the workload data
        workload = storage.get_workload(request.project_id, request.workload_id)
        if not workload:
            raise HTTPException(status_code=404, detail=f"Workload {request.workload_id} not found")

        # Extract queries from workload
        queries = workload.get('queries', [])
        if not queries:
            raise HTTPException(status_code=400, detail="No queries found in workload")

        # Generate comparative pipelines
        result = pipeline_gen.generate_comparative_pipelines(
            queries=queries,
            project_id=request.project_id,
            workload_id=request.workload_id,
            schema_mapping=request.schema_mapping
        )

        return {
            "status": "success",
            "message": f"Generated {result['total_tables']} comparative pipeline(s) with {result['total_validations']} query validations",
            **result
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating comparative pipelines: {str(e)}")


class SavePipelinesToProjectRequest(BaseModel):
    project_id: str
    pipeline_files: Dict[str, Dict]  # table_name -> pipeline info with yaml_content


@router.post("/save-pipelines-to-project")
async def save_pipelines_to_project(request: SavePipelinesToProjectRequest):
    """
    Save generated pipelines directly to a project's pipelines directory.

    This endpoint saves pipeline YAML files to the project without requiring download/upload.

    Args:
        project_id: Project identifier
        pipeline_files: Dictionary of pipeline files to save (from generate-pipelines response)

    Returns:
        - saved_count: Number of pipelines saved
        - saved_files: List of saved filenames
    """
    try:
        from pathlib import Path

        # Define project pipelines directory
        project_pipelines_dir = Path(f"/data/projects/{request.project_id}/pipelines")
        project_pipelines_dir.mkdir(parents=True, exist_ok=True)

        saved_files = []

        for table_name, pipeline_info in request.pipeline_files.items():
            filename = pipeline_info.get('filename')
            yaml_content = pipeline_info.get('yaml_content')

            if not filename or not yaml_content:
                continue

            # Save to project directory
            file_path = project_pipelines_dir / filename
            with open(file_path, 'w') as f:
                f.write(yaml_content)

            saved_files.append(filename)

        return {
            "status": "success",
            "message": f"Saved {len(saved_files)} pipeline(s) to project {request.project_id}",
            "saved_count": len(saved_files),
            "saved_files": saved_files,
            "project_id": request.project_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving pipelines to project: {str(e)}")



class BatchTemplateSaveRequest(BaseModel):
    template_name: str
    description: str
    tags: List[str] = []
    batch_config: Dict  # The actual batch configuration


@router.get("/batch/templates/list")
async def list_batch_templates():
    """
    List all available batch templates

    Returns:
        List of template summaries with metadata
    """
    try:
        from pathlib import Path
        import yaml
        from datetime import datetime

        templates_dir = Path("/data/batch_templates")
        templates_dir.mkdir(parents=True, exist_ok=True)

        templates = []

        for template_file in templates_dir.glob("*.yaml"):
            try:
                with open(template_file, 'r') as f:
                    template_data = yaml.safe_load(f)

                template_meta = template_data.get('template', {})
                batch_config = template_data.get('batch', {})

                # Get file stats
                stat = template_file.stat()

                templates.append({
                    "template_id": template_file.stem,
                    "filename": template_file.name,
                    "name": template_meta.get('name', template_file.stem),
                    "description": template_meta.get('description', ''),
                    "tags": template_meta.get('tags', []),
                    "created_at": template_meta.get('created_at', datetime.fromtimestamp(stat.st_ctime).isoformat()),
                    "pipeline_count": len(batch_config.get('pipelines', [])),
                    "batch_type": batch_config.get('type', 'sequential')
                })
            except Exception as e:
                print(f"Error reading template {template_file}: {e}")
                continue

        # Sort by created_at (newest first)
        templates.sort(key=lambda x: x.get('created_at', ''), reverse=True)

        return {
            "templates": templates,
            "total": len(templates)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing templates: {str(e)}")


@router.get("/batch/templates/{template_id}")
async def get_batch_template(template_id: str):
    """
    Get a specific batch template by ID

    Args:
        template_id: Template identifier (filename without .yaml)

    Returns:
        Template metadata and batch configuration
    """
    try:
        from pathlib import Path
        import yaml

        templates_dir = Path("/data/batch_templates")
        template_file = templates_dir / f"{template_id}.yaml"

        if not template_file.exists():
            raise HTTPException(status_code=404, detail=f"Template '{template_id}' not found")

        with open(template_file, 'r') as f:
            template_data = yaml.safe_load(f)

        return {
            "template_id": template_id,
            "filename": template_file.name,
            **template_data
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading template: {str(e)}")


@router.post("/batch/templates/save")
async def save_batch_template(request: BatchTemplateSaveRequest):
    """
    Save a batch configuration as a reusable template

    Args:
        request: Template save request with name, description, tags, and batch config

    Returns:
        Success status and template ID
    """
    try:
        from pathlib import Path
        import yaml
        from datetime import datetime

        templates_dir = Path("/data/batch_templates")
        templates_dir.mkdir(parents=True, exist_ok=True)

        # Generate template ID from name (slugify)
        template_id = request.template_name.lower().replace(' ', '_').replace('-', '_')
        template_id = ''.join(c for c in template_id if c.isalnum() or c == '_')

        # Create template structure
        template_data = {
            "template": {
                "name": request.template_name,
                "description": request.description,
                "tags": request.tags,
                "created_at": datetime.now().isoformat()
            },
            "batch": request.batch_config
        }

        # Save template file
        template_file = templates_dir / f"{template_id}.yaml"
        with open(template_file, 'w') as f:
            yaml.dump(template_data, f, default_flow_style=False, sort_keys=False)

        return {
            "status": "success",
            "message": f"Template '{request.template_name}' saved successfully",
            "template_id": template_id,
            "filename": template_file.name,
            "path": str(template_file)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving template: {str(e)}")


@router.delete("/batch/templates/{template_id}")
async def delete_batch_template(template_id: str):
    """
    Delete a batch template

    Args:
        template_id: Template identifier

    Returns:
        Success status
    """
    try:
        from pathlib import Path

        templates_dir = Path("/data/batch_templates")
        template_file = templates_dir / f"{template_id}.yaml"

        if not template_file.exists():
            raise HTTPException(status_code=404, detail=f"Template '{template_id}' not found")

        template_file.unlink()

        return {
            "status": "success",
            "message": f"Template '{template_id}' deleted successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting template: {str(e)}")


@router.get("/download-query-generator")
async def download_query_generator():
    """
    Download SQL Server Query Store workload JSON generator script

    This endpoint serves a SQL script that users can run on their SQL Server database
    to generate workload JSON data from Query Store for upload to the Workload Analysis feature.

    Returns:
        SQL file for download
    """
    try:
        file_path = Path(__file__).parent.parent / "queries" / "generate_workload_json.sql"

        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Query generator script not found")

        return FileResponse(
            path=str(file_path),
            filename="generate_workload_json.sql",
            media_type="application/sql"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error serving query generator: {str(e)}")
