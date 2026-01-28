from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, List
from core_adapter import get_metadata
import os
import yaml

from config.paths import paths

router = APIRouter()

class MetadataRequest(BaseModel):
    connection: str  # "sqlserver" or "snowflake"
    table: str
    schema: Optional[str] = None

class TablesRequest(BaseModel):
    connection: str  # "sqlserver" or "snowflake"
    schema: Optional[str] = None


@router.post("/extract")
def extract_metadata(payload: MetadataRequest):
    """Extract column metadata for a specific table using pre-configured connections"""
    try:
        conn = payload.connection.lower()
        table = payload.table

        # Use pre-configured connections ("sqlserver" or "snowflake")
        result = get_metadata(conn, table)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tables")
def list_tables(payload: TablesRequest):
    """List all tables in the specified connection"""
    try:
        from ombudsman.core.metadata_loader import MetadataLoader

        conn = payload.connection.lower()

        # Create loader with pre-configured connection
        loader = MetadataLoader(conn)

        # Get tables
        schema = payload.schema
        if not schema:
            if conn == "sqlserver":
                schema = "dbo"
            elif conn == "snowflake":
                import os
                schema = os.getenv("SNOWFLAKE_SCHEMA", "PUBLIC")

        tables = loader.get_tables(schema=schema)

        return {
            "connection": conn,
            "schema": schema,
            "tables": tables
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tables/all")
def list_all_tables():
    """List all tables from both SQL Server and Snowflake, including sample data databases"""
    try:
        import pyodbc
        import snowflake.connector
        import os

        results = {
            "sqlserver": {"databases": {}, "status": "error"},
            "snowflake": {"databases": {}, "status": "error"}
        }

        # Get SQL Server tables from multiple databases
        try:
            conn_str = os.getenv("SQLSERVER_CONN_STR")
            if not conn_str:
                conn_str = (
                    f"DRIVER={{ODBC Driver 18 for SQL Server}};"
                    f"SERVER={os.getenv('MSSQL_HOST', 'localhost')},{os.getenv('MSSQL_PORT', '1433')};"
                    f"DATABASE=master;"
                    f"UID={os.getenv('MSSQL_USER', 'sa')};"
                    f"PWD={os.getenv('MSSQL_PASSWORD', '')};"
                    f"TrustServerCertificate=yes;"
                )

            # Query both master and SampleDW databases
            databases_to_check = ["master", "SampleDW"]

            for db in databases_to_check:
                try:
                    # Update connection string for specific database
                    db_conn_str = conn_str.replace("DATABASE=master", f"DATABASE={db}")
                    if "DATABASE=" not in db_conn_str:
                        # Add database if not present
                        db_conn_str = conn_str.rstrip(";") + f";DATABASE={db};"

                    conn = pyodbc.connect(db_conn_str)
                    cursor = conn.cursor()

                    cursor.execute("""
                        SELECT TABLE_NAME
                        FROM INFORMATION_SCHEMA.TABLES
                        WHERE TABLE_SCHEMA = 'dbo'
                        AND TABLE_TYPE = 'BASE TABLE'
                        ORDER BY TABLE_NAME
                    """)

                    tables = [row[0] for row in cursor.fetchall()]
                    results["sqlserver"]["databases"][db] = {
                        "tables": tables,
                        "schema": "dbo",
                        "count": len(tables)
                    }

                    cursor.close()
                    conn.close()
                except Exception as e:
                    results["sqlserver"]["databases"][db] = {
                        "tables": [],
                        "schema": "dbo",
                        "count": 0,
                        "error": str(e)
                    }

            results["sqlserver"]["status"] = "success"

        except Exception as e:
            results["sqlserver"]["error"] = str(e)

        # Get Snowflake tables from multiple databases
        try:
            conn = snowflake.connector.connect(
                user=os.getenv("SNOWFLAKE_USER"),
                password=os.getenv("SNOWFLAKE_PASSWORD"),
                account=os.getenv("SNOWFLAKE_ACCOUNT"),
                warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
                role=os.getenv("SNOWFLAKE_ROLE"),
            )
            cursor = conn.cursor()

            # Query both DEMO_DB and SAMPLEDW databases
            databases_to_check = [
                os.getenv("SNOWFLAKE_DATABASE", "DEMO_DB"),
                "SAMPLEDW"
            ]
            schema = os.getenv("SNOWFLAKE_SCHEMA", "PUBLIC")

            for db in databases_to_check:
                try:
                    query = f"""
                        SELECT TABLE_NAME
                        FROM {db}.INFORMATION_SCHEMA.TABLES
                        WHERE TABLE_SCHEMA = '{schema}'
                        AND TABLE_TYPE = 'BASE TABLE'
                        ORDER BY TABLE_NAME
                    """
                    cursor.execute(query)
                    tables = [row[0] for row in cursor.fetchall()]

                    results["snowflake"]["databases"][db] = {
                        "tables": tables,
                        "schema": schema,
                        "count": len(tables)
                    }
                except Exception as e:
                    results["snowflake"]["databases"][db] = {
                        "tables": [],
                        "schema": schema,
                        "count": 0,
                        "error": str(e)
                    }

            cursor.close()
            conn.close()
            results["snowflake"]["status"] = "success"

        except Exception as e:
            results["snowflake"]["error"] = str(e)

        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class InferRelationshipsRequest(BaseModel):
    """Request to infer relationships from metadata"""
    project_name: Optional[str] = None  # Project name - if not provided, uses active project
    use_existing_mappings: bool = True  # Load from YAML files
    source_database: str = "sql"  # "sql" or "snow"
    target_database: str = "snow"  # "sql" or "snow"


@router.post("/infer-relationships")
def infer_relationships(request: InferRelationshipsRequest):
    """
    Infer foreign key relationships from table metadata using heuristics.
    Returns predicted relationships with confidence scores.
    """
    try:
        from ombudsman.core.relationship_inferrer import RelationshipInferrer

        # Get project name - use provided or fallback to active project
        project_name = request.project_name
        if not project_name:
            # Try to get active project from session/state
            from projects.context import get_active_project

            active_project = get_active_project()
            if active_project:
                project_name = active_project.get("project_id", "default_project")
            else:
                project_name = "default_project"

        # Load table metadata from project-specific YAML files
        config_dir = str(paths.get_project_config_dir(project_name))
        tables_file = f"{config_dir}/tables.yaml"

        print(f"[INFER] Looking for tables.yaml at: {tables_file}")
        print(f"[INFER] File exists: {os.path.exists(tables_file)}")

        if not os.path.exists(tables_file):
            raise HTTPException(
                status_code=404,
                detail=f"No table metadata found at {tables_file}. Please extract metadata first using Database Mapping."
            )

        # Load tables.yaml
        with open(tables_file, "r") as f:
            tables_data = yaml.safe_load(f) or {}

        # Convert to metadata format expected by inferrer
        # Use source_database to determine which tables to load
        # Skip views as they don't need relationship inference
        metadata = {}
        source_tables = tables_data.get(request.source_database, {})

        for table_name, table_data in source_tables.items():
            # Check if this is a view - skip if so
            if isinstance(table_data, dict) and table_data.get("object_type") == "VIEW":
                print(f"[DEBUG] Skipping view {table_name} from relationship inference")
                continue

            # Handle both old format (just columns dict) and new format (dict with columns/object_type)
            if isinstance(table_data, dict) and "columns" in table_data:
                columns = table_data["columns"]
            else:
                columns = table_data  # Old format: table_data is the columns dict directly

            # Extract schema and table from schema.table format
            if "." in table_name:
                schema, tbl = table_name.rsplit(".", 1)
            else:
                schema = "dbo" if request.source_database == "sql" else "PUBLIC"
                tbl = table_name

            metadata[table_name] = {
                "columns": columns,
                "relationships": {},
                "schema": schema,
                "table": tbl,
                "database": request.source_database
            }

        # Create inferrer and run inference
        inferrer = RelationshipInferrer()
        inferred = inferrer.infer_all_relationships(metadata)

        # Calculate metrics
        total_relationships = len(inferred)
        high_confidence = sum(1 for r in inferred if r["confidence"] == "high")
        medium_confidence = sum(1 for r in inferred if r["confidence"] == "medium")
        low_confidence = sum(1 for r in inferred if r["confidence"] == "low")

        # Group by fact table
        by_fact_table = {}
        for rel in inferred:
            fact = rel["fact_table"]
            if fact not in by_fact_table:
                by_fact_table[fact] = []
            by_fact_table[fact].append(rel)

        # Save relationships to project's relationships.yaml
        relationships_file = f"{config_dir}/relationships.yaml"
        os.makedirs(config_dir, exist_ok=True)

        with open(relationships_file, "w") as f:
            yaml.dump(inferred, f, default_flow_style=False, sort_keys=False)

        print(f"[INFO] Saved {len(inferred)} relationships to {relationships_file}")

        return {
            "status": "success",
            "relationships": inferred,
            "source_database": request.source_database,
            "target_database": request.target_database,
            "saved_to": relationships_file,
            "metrics": {
                "total_relationships": total_relationships,
                "high_confidence": high_confidence,
                "medium_confidence": medium_confidence,
                "low_confidence": low_confidence,
                "fact_tables_analyzed": len(by_fact_table),
                "dimension_tables_referenced": len(set(r["dim_table"] for r in inferred)),
                "source_db_label": "SQL Server" if request.source_database == "sql" else "Snowflake",
                "target_db_label": "SQL Server" if request.target_database == "sql" else "Snowflake"
            },
            "by_fact_table": by_fact_table
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Relationship inference failed: {str(e)}")


class ValidateRelationshipRequest(BaseModel):
    """Request to validate a specific relationship"""
    fact_table: str
    fk_column: str
    dim_table: str
    dim_column: str
    sample_size: int = 1000
    use_snowflake: bool = False


@router.post("/validate-relationship")
def validate_relationship(request: ValidateRelationshipRequest):
    """
    Validate a specific relationship by sampling data and checking FK integrity.
    Returns match rate and confidence score.
    """
    try:
        from ombudsman.core.relationship_inferrer import RelationshipInferrer
        import pyodbc
        import snowflake.connector

        # Create database connection
        conn = None
        if request.use_snowflake:
            conn = snowflake.connector.connect(
                user=os.getenv("SNOWFLAKE_USER"),
                password=os.getenv("SNOWFLAKE_PASSWORD"),
                account=os.getenv("SNOWFLAKE_ACCOUNT"),
                warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
                role=os.getenv("SNOWFLAKE_ROLE"),
                database=os.getenv("SNOWFLAKE_DATABASE", "SAMPLEDW")
            )
        else:
            conn_str = os.getenv("SQLSERVER_CONN_STR", "")
            if not conn_str:
                conn_str = (
                    f"DRIVER={{ODBC Driver 18 for SQL Server}};"
                    f"SERVER={os.getenv('MSSQL_HOST', 'localhost')},{os.getenv('MSSQL_PORT', '1433')};"
                    f"DATABASE={os.getenv('MSSQL_DATABASE', 'SampleDW')};"
                    f"UID={os.getenv('MSSQL_USER', 'sa')};"
                    f"PWD={os.getenv('MSSQL_PASSWORD', '')};"
                    f"TrustServerCertificate=yes;"
                )
            conn = pyodbc.connect(conn_str)

        # Create inferrer with connection
        inferrer = RelationshipInferrer(
            sql_conn=conn if not request.use_snowflake else None,
            snow_conn=conn if request.use_snowflake else None
        )

        # Validate the relationship
        result = inferrer.validate_relationship(
            fact_table=request.fact_table,
            fk_column=request.fk_column,
            dim_table=request.dim_table,
            dim_column=request.dim_column,
            sample_size=request.sample_size,
            use_snowflake=request.use_snowflake
        )

        # Close connection
        if conn:
            conn.close()

        return {
            "status": "success",
            "validation": result
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")


class SaveRelationshipsRequest(BaseModel):
    """Request to save relationships to YAML"""
    relationships: List[Dict]


@router.post("/save-relationships")
def save_relationships(request: SaveRelationshipsRequest):
    """
    Save inferred/edited relationships to relationships.yaml file.
    Creates backup before overwriting.
    """
    try:
        # Get active project's config directory
        from projects.context import get_active_project, get_project_config_dir

        active_project = get_active_project()
        if active_project:
            project_name = active_project.get("project_id", "default_project")
        else:
            project_name = "default_project"

        config_dir = get_project_config_dir()
        os.makedirs(config_dir, exist_ok=True)
        relationships_file = f"{config_dir}/relationships.yaml"

        # Backup existing file
        if os.path.exists(relationships_file):
            import shutil
            from datetime import datetime
            backup_dir = f"{config_dir}/backups"
            os.makedirs(backup_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            shutil.copy2(relationships_file, f"{backup_dir}/relationships.yaml.{timestamp}")

        # Convert to YAML format
        relationships_yaml = []
        for rel in request.relationships:
            relationships_yaml.append({
                "fact_table": rel.get("fact_table"),
                "fk_column": rel.get("fk_column"),
                "dim_reference": f"{rel.get('dim_table')}.{rel.get('dim_column')}"
            })

        # Save to file
        os.makedirs(config_dir, exist_ok=True)
        with open(relationships_file, "w") as f:
            yaml.dump(relationships_yaml, f, default_flow_style=False, sort_keys=False)

        return {
            "status": "success",
            "message": "Relationships saved successfully",
            "file": relationships_file,
            "relationships_count": len(relationships_yaml)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save relationships: {str(e)}")