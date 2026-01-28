from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
from pathlib import Path
import os
import json

from .workload_generator import WorkloadGenerator

router = APIRouter()
workload_gen = WorkloadGenerator()

class SampleDataRequest(BaseModel):
    num_dimensions: int = 3
    num_facts: int = 2
    rows_per_dim: int = 50
    rows_per_fact: int = 200
    broken_fk_rate: float = 0.05
    target: str = "both"  # sqlserver, snowflake, or both
    seed: int = 12345


generation_status = {}


@router.post("/generate")
async def generate_sample_data(request: SampleDataRequest, background_tasks: BackgroundTasks):
    """Generate sample data in SQL Server or Snowflake"""
    try:
        # Start generation in background
        job_id = f"datagen_{request.target}_{request.seed}"

        generation_status[job_id] = {
            "job_id": job_id,
            "status": "pending",
            "message": "Sample data generation started"
        }

        background_tasks.add_task(generate_data_async, job_id, request)

        return {
            "job_id": job_id,
            "status": "pending",
            "message": "Sample data generation started in background"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start data generation: {str(e)}")


async def generate_data_async(job_id: str, request: SampleDataRequest):
    """Generate sample data asynchronously with progress tracking"""
    try:
        generation_status[job_id]["status"] = "running"
        generation_status[job_id]["progress"] = 0
        generation_status[job_id]["stage"] = "initializing"

        # Progress callback to update status
        def progress_callback(stage, progress, message):
            """Update generation status with progress"""
            generation_status[job_id]["stage"] = stage
            generation_status[job_id]["progress"] = progress
            generation_status[job_id]["message"] = message
            print(f"[{job_id}] {stage} {progress}%: {message}")

        # Set common environment variables
        os.environ["SAMPLE_DIM_COUNT"] = str(request.num_dimensions)
        os.environ["SAMPLE_FACT_COUNT"] = str(request.num_facts)
        os.environ["SAMPLE_DIM_ROWS"] = str(request.rows_per_dim)
        os.environ["SAMPLE_FACT_ROWS"] = str(request.rows_per_fact)
        os.environ["BROKEN_FK_RATE"] = str(request.broken_fk_rate)
        os.environ["SAMPLE_SEED"] = str(request.seed)

        # Import the generator
        from ombudsman.scripts.generate_sample_data import main as generate_main

        targets = []
        if request.target == "both":
            targets = ["sqlserver", "snowflake"]
        else:
            targets = [request.target]

        results = []
        for target in targets:
            try:
                os.environ["SAMPLE_SOURCE"] = target
                progress_callback("starting", 0, f"Starting generation for {target.upper()}")

                # Call with progress callback
                generate_main(progress_callback=progress_callback)

                results.append(f"{target.upper()}: Success")
                progress_callback("completed", 100, f"{target.upper()} generation complete")
            except Exception as e:
                results.append(f"{target.upper()}: Failed - {str(e)}")
                progress_callback("error", 0, f"{target.upper()} failed: {str(e)}")
                print(f"Generation error for {target}: {e}")

        generation_status[job_id]["status"] = "completed"
        generation_status[job_id]["progress"] = 100
        generation_status[job_id]["stage"] = "complete"
        generation_status[job_id]["message"] = (
            f"Generated {request.num_dimensions} dimensions with {request.rows_per_dim} rows each, "
            f"and {request.num_facts} facts with {request.rows_per_fact} rows each. "
            f"Results: {', '.join(results)}"
        )
        generation_status[job_id]["results"] = results

    except Exception as e:
        generation_status[job_id]["status"] = "failed"
        generation_status[job_id]["progress"] = 0
        generation_status[job_id]["stage"] = "error"
        generation_status[job_id]["message"] = f"Data generation failed: {str(e)}"
        generation_status[job_id]["error"] = str(e)
        print(f"Data generation error: {e}")
        import traceback
        traceback.print_exc()


@router.get("/status/{job_id}")
async def get_generation_status(job_id: str):
    """Get status of sample data generation"""
    if job_id not in generation_status:
        raise HTTPException(status_code=404, detail="Job not found")

    return generation_status[job_id]


@router.get("/schemas")
async def list_available_schemas():
    """List available sample data schemas"""
    return {
        "schemas": [
            {
                "name": "Retail",
                "description": "E-commerce retail data model",
                "dimensions": ["Customer", "Product", "Store"],
                "facts": ["Sales", "Inventory"]
            },
            {
                "name": "Finance",
                "description": "Financial transaction data model",
                "dimensions": ["Account", "Transaction Type", "Merchant"],
                "facts": ["Transactions", "Balances"]
            },
            {
                "name": "Healthcare",
                "description": "Healthcare patient data model",
                "dimensions": ["Patient", "Provider", "Diagnosis"],
                "facts": ["Visits", "Medications"]
            }
        ]
    }


@router.delete("/clear")
async def clear_sample_data():
    """Clear all generated sample data"""
    try:
        import pyodbc
        import os

        # Connect to SQL Server
        conn_str = (
            f"DRIVER={{ODBC Driver 18 for SQL Server}};"
            f"SERVER={os.getenv('MSSQL_HOST', 'sqlserver')},{os.getenv('MSSQL_PORT', '1433')};"
            f"DATABASE={os.getenv('MSSQL_DATABASE', 'master')};"
            f"UID={os.getenv('MSSQL_USER', 'sa')};"
            f"PWD={os.getenv('MSSQL_PASSWORD', '')};"
            f"TrustServerCertificate=yes;"
        )

        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()

        # Get list of sample tables (tables starting with dim_ or fact_)
        cursor.execute("""
            SELECT TABLE_NAME
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_TYPE = 'BASE TABLE'
            AND (TABLE_NAME LIKE 'dim_%' OR TABLE_NAME LIKE 'fact_%')
        """)

        tables = [row[0] for row in cursor.fetchall()]

        # Drop tables
        for table in tables:
            cursor.execute(f"DROP TABLE IF EXISTS dbo.{table}")

        conn.commit()
        cursor.close()
        conn.close()

        return {
            "status": "success",
            "message": f"Cleared {len(tables)} sample tables",
            "tables_dropped": tables
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear sample data: {str(e)}")


@router.get("/download-sample-workload")
async def download_sample_workload(schema: str = Query(default="Retail", description="Schema template: Retail, Finance, or Healthcare")):
    """Download a dynamically generated sample workload JSON file based on selected schema"""
    try:
        # Validate schema
        if schema not in ["Retail", "Finance", "Healthcare"]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid schema '{schema}'. Must be one of: Retail, Finance, Healthcare"
            )

        # Generate workload for the selected schema
        workload = workload_gen.generate_workload(schema)

        # Return as JSON response with proper filename
        return JSONResponse(
            content=workload,
            headers={
                "Content-Disposition": f'attachment; filename="{schema.lower()}_sample_workload.json"'
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate sample workload: {str(e)}"
        )
