"""
Workload API Endpoints
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Body
from typing import List, Dict, Optional
from pydantic import BaseModel
import json

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
    Analyze a workload and generate validation suggestions

    Args:
        workload_id: Workload to analyze
        project_id: Project context
        metadata: Optional table metadata (column -> datatype)

    Returns:
        - tables: Analysis per table with suggestions
        - coverage: Coverage metrics
        - categories: Suggestion counts by category
    """
    try:
        analysis = engine.analyze_workload(
            project_id=request.project_id,
            workload_id=request.workload_id,
            metadata=request.metadata or {}
        )

        return analysis
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


@router.get("/pipelines/list")
async def list_pipelines(project_id: Optional[str] = None):
    """
    List all generated pipelines

    Args:
        project_id: Optional filter by project

    Returns:
        List of pipeline summaries
    """
    try:
        pipelines = pipeline_gen.list_generated_pipelines(project_id=project_id)
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
