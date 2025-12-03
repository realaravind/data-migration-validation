from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
import pyodbc
import snowflake.connector
import os
import yaml

router = APIRouter()


class DatabaseMappingRequest(BaseModel):
    """Request to map databases and extract metadata"""
    sql_server_database: str
    sql_server_schema: str = "dbo"
    snowflake_database: str
    snowflake_schema: str = "PUBLIC"
    table_patterns: List[str] = ["dim_%", "fact_%"]  # SQL LIKE patterns
    specific_tables: Optional[List[str]] = None  # Override patterns with specific tables
    schema_mappings: Optional[Dict[str, str]] = None  # SQL schema -> Snowflake schema mappings


class SchemaMappingUpdate(BaseModel):
    """Request to update schema mappings"""
    mappings: Dict[str, str]  # sql_schema -> snowflake_schema


class ColumnMappingUpdate(BaseModel):
    """Request to update column mappings for a specific table"""
    sql_table: str
    snow_table: str
    column_mappings: List[Dict[str, Any]]  # List of {source, target, confidence, auto_mapped}


class TableMapping(BaseModel):
    """Mapping of a single table between SQL Server and Snowflake"""
    sql_server_table: str
    snowflake_table: str
    columns: Dict[str, str]  # column_name -> data_type
    relationships: Dict[str, str]  # fk_column -> "parent_table.parent_column"


@router.post("/extract")
async def extract_and_map_metadata(request: DatabaseMappingRequest):
    """
    Extract metadata from both SQL Server and Snowflake databases,
    then create mappings and generate YAML files for the core engine.
    Supports schema mappings for multi-schema extraction.
    """
    try:
        # Load or use provided schema mappings
        schema_mappings = request.schema_mappings
        if not schema_mappings:
            # Try to load from file
            config_dir = "/core/src/ombudsman/config"
            schema_mappings_file = f"{config_dir}/schema_mappings.yaml"
            if os.path.exists(schema_mappings_file):
                with open(schema_mappings_file, "r") as f:
                    schema_mappings = yaml.safe_load(f) or {}
            else:
                # Default: single schema mapping
                schema_mappings = {request.sql_server_schema: request.snowflake_schema}

        # Extract from all mapped schemas
        all_sql_metadata = {}
        all_snow_metadata = {}
        schema_extraction_results = []

        for sql_schema, snow_schema in schema_mappings.items():
            print(f"[DEBUG] Extracting from SQL Server schema: {sql_schema} -> Snowflake schema: {snow_schema}")

            # Extract from SQL Server schema
            sql_metadata = extract_sqlserver_tables(
                database=request.sql_server_database,
                schema=sql_schema,
                patterns=request.table_patterns,
                specific_tables=request.specific_tables
            )
            print(f"[DEBUG] SQL Server extraction found {len(sql_metadata)} tables in {sql_schema}")

            # Extract from Snowflake schema
            snow_metadata = extract_snowflake_tables(
                database=request.snowflake_database,
                schema=snow_schema,
                patterns=request.table_patterns,
                specific_tables=request.specific_tables
            )
            print(f"[DEBUG] Snowflake extraction found {len(snow_metadata)} tables in {snow_schema}")

            # Prefix table names with schema to avoid conflicts
            for table_name, table_data in sql_metadata.items():
                all_sql_metadata[f"{sql_schema}.{table_name}"] = {
                    **table_data,
                    "schema": sql_schema,
                    "table": table_name
                }

            for table_name, table_data in snow_metadata.items():
                all_snow_metadata[f"{snow_schema}.{table_name}"] = {
                    **table_data,
                    "schema": snow_schema,
                    "table": table_name
                }

            schema_extraction_results.append({
                "sql_schema": sql_schema,
                "snowflake_schema": snow_schema,
                "sql_tables_found": len(sql_metadata),
                "snowflake_tables_found": len(snow_metadata)
            })

        # Create mappings
        mappings = create_table_mappings(all_sql_metadata, all_snow_metadata)

        # Generate YAML files for core engine
        yaml_output = generate_yaml_files(mappings, request, schema_mappings)

        return {
            "status": "success",
            "sql_server": {
                "database": request.sql_server_database,
                "total_tables_found": len(all_sql_metadata)
            },
            "snowflake": {
                "database": request.snowflake_database,
                "total_tables_found": len(all_snow_metadata)
            },
            "schema_mappings": schema_mappings,
            "schema_results": schema_extraction_results,
            "mappings": mappings,
            "yaml_generated": yaml_output
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Metadata extraction failed: {str(e)}")


def extract_sqlserver_tables(database: str, schema: str, patterns: List[str], specific_tables: Optional[List[str]]) -> Dict:
    """Extract table metadata from SQL Server"""
    conn_str = os.getenv("SQLSERVER_CONN_STR", "")

    # Replace database in connection string
    if "DATABASE=" in conn_str:
        parts = conn_str.split(";")
        for i, part in enumerate(parts):
            if part.startswith("DATABASE="):
                parts[i] = f"DATABASE={database}"
        conn_str = ";".join(parts)
    else:
        conn_str = (
            f"DRIVER={{ODBC Driver 18 for SQL Server}};"
            f"SERVER={os.getenv('MSSQL_HOST', 'localhost')},{os.getenv('MSSQL_PORT', '1433')};"
            f"DATABASE={database};"
            f"UID={os.getenv('MSSQL_USER', 'sa')};"
            f"PWD={os.getenv('MSSQL_PASSWORD', '')};"
            f"TrustServerCertificate=yes;"
        )

    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()

    tables = {}

    # Get tables and views based on patterns or specific list
    if specific_tables:
        table_list = [(t, 'TABLE') for t in specific_tables]  # Assume tables if specific list provided
    else:
        # Build query with LIKE patterns - include both BASE TABLE and VIEW
        pattern_conditions = " OR ".join([f"TABLE_NAME LIKE '{p}'" for p in patterns])
        query = f"""
            SELECT TABLE_NAME, TABLE_TYPE
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = '{schema}'
            AND TABLE_TYPE IN ('BASE TABLE', 'VIEW')
            AND ({pattern_conditions})
            ORDER BY TABLE_NAME
        """
        cursor.execute(query)
        table_list = [(row[0], row[1]) for row in cursor.fetchall()]

    # Get columns for each table/view
    for table_name, table_type in table_list:
        cursor.execute(f"""
            SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH,
                   NUMERIC_PRECISION, NUMERIC_SCALE, IS_NULLABLE
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = '{schema}' AND TABLE_NAME = '{table_name}'
            ORDER BY ORDINAL_POSITION
        """)

        columns = {}
        for row in cursor.fetchall():
            col_name = row[0]
            data_type = row[1]
            max_len = row[2]
            precision = row[3]
            scale = row[4]

            # Format data type with size
            if max_len:
                data_type = f"{data_type}({max_len})"
            elif precision and scale:
                data_type = f"{data_type}({precision},{scale})"

            columns[col_name] = data_type.upper()

        # Get foreign keys - only for tables, not views
        relationships = {}
        if table_type == 'BASE TABLE':
            cursor.execute(f"""
                SELECT
                    FK_COL.COLUMN_NAME as FK_Column,
                    PK_TAB.TABLE_NAME as PK_Table,
                    PK_COL.COLUMN_NAME as PK_Column
                FROM INFORMATION_SCHEMA.REFERENTIAL_CONSTRAINTS RC
                JOIN INFORMATION_SCHEMA.TABLE_CONSTRAINTS FK_TAB
                    ON RC.CONSTRAINT_NAME = FK_TAB.CONSTRAINT_NAME
                JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE FK_COL
                    ON RC.CONSTRAINT_NAME = FK_COL.CONSTRAINT_NAME
                JOIN INFORMATION_SCHEMA.TABLE_CONSTRAINTS PK_TAB
                    ON RC.UNIQUE_CONSTRAINT_NAME = PK_TAB.CONSTRAINT_NAME
                JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE PK_COL
                    ON RC.UNIQUE_CONSTRAINT_NAME = PK_COL.CONSTRAINT_NAME
                WHERE FK_TAB.TABLE_SCHEMA = '{schema}'
                AND FK_TAB.TABLE_NAME = '{table_name}'
            """)

            for row in cursor.fetchall():
                fk_col, pk_table, pk_col = row
                relationships[fk_col] = f"{pk_table}.{pk_col}"

        tables[table_name] = {
            "columns": columns,
            "relationships": relationships,
            "object_type": "VIEW" if table_type == 'VIEW' else "TABLE"
        }

    cursor.close()
    conn.close()

    return tables


def extract_snowflake_tables(database: str, schema: str, patterns: List[str], specific_tables: Optional[List[str]]) -> Dict:
    """Extract table metadata from Snowflake"""
    try:
        conn = snowflake.connector.connect(
            user=os.getenv("SNOWFLAKE_USER"),
            password=os.getenv("SNOWFLAKE_PASSWORD"),
            account=os.getenv("SNOWFLAKE_ACCOUNT"),
            warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
            role=os.getenv("SNOWFLAKE_ROLE"),
            database=database.upper(),  # Snowflake uses uppercase
            schema=schema.upper()  # Snowflake uses uppercase
        )
        cursor = conn.cursor()

        tables = {}

        # Get tables and views based on patterns or specific list
        if specific_tables:
            table_list = [(t, 'TABLE') for t in specific_tables]  # Assume tables if specific list provided
        else:
            # Build query with LIKE patterns (case-insensitive using UPPER) - include both BASE TABLE and VIEW
            pattern_conditions = " OR ".join([f"UPPER(TABLE_NAME) LIKE UPPER('{p}')" for p in patterns])
            query = f"""
                SELECT TABLE_NAME, TABLE_TYPE
                FROM {database.upper()}.INFORMATION_SCHEMA.TABLES
                WHERE UPPER(TABLE_SCHEMA) = UPPER('{schema}')
                AND TABLE_TYPE IN ('BASE TABLE', 'VIEW')
                AND ({pattern_conditions})
                ORDER BY TABLE_NAME
            """
            print(f"[DEBUG] Snowflake query: {query}")
            cursor.execute(query)
            table_list = [(row[0], row[1]) for row in cursor.fetchall()]
            print(f"[DEBUG] Snowflake found {len(table_list)} objects in {schema}: {table_list[:5]}")

        # Get columns for each table/view
        for table_name, table_type in table_list:
            cursor.execute(f"DESCRIBE TABLE {database.upper()}.{schema.upper()}.{table_name}")

            columns = {}
            for row in cursor.fetchall():
                col_name = row[0]
                data_type = row[1].split("(")[0].upper()  # Remove size info for now
                columns[col_name] = data_type

            # Get foreign keys (if any) - only for tables, not views
            # Note: Snowflake FK constraints might not be enforced
            relationships = {}

            tables[table_name] = {
                "columns": columns,
                "relationships": relationships,
                "object_type": "VIEW" if table_type == 'VIEW' else "TABLE"
            }

        cursor.close()
        conn.close()

        print(f"[DEBUG] Snowflake extraction complete: {len(tables)} tables extracted from {schema}")
        return tables

    except Exception as e:
        print(f"[ERROR] Snowflake extraction failed for {database}.{schema}: {str(e)}")
        import traceback
        traceback.print_exc()
        return {}


def create_table_mappings(sql_metadata: Dict, snow_metadata: Dict) -> List[TableMapping]:
    """Create mappings between SQL Server and Snowflake tables with column-level mappings"""
    mappings = []

    # Import MappingLoader for column suggestions
    import sys
    sys.path.insert(0, "/core/src")
    from ombudsman.core.mapping_loader import MappingLoader

    mapper = MappingLoader()

    # Create case-insensitive lookup for Snowflake tables
    snow_lookup = {table.upper(): table for table in snow_metadata.keys()}
    matched_snow_tables = set()

    # Find matching tables (case-insensitive)
    for sql_table in sql_metadata:
        snow_table_upper = sql_table.upper()

        if snow_table_upper in snow_lookup:
            snow_table_actual = snow_lookup[snow_table_upper]
            matched_snow_tables.add(snow_table_actual)

            # Generate column mappings
            sql_cols = [{"name": col, "data_type": dtype} for col, dtype in sql_metadata[sql_table]["columns"].items()]
            snow_cols = [{"name": col, "data_type": dtype} for col, dtype in snow_metadata[snow_table_actual]["columns"].items()]

            column_mapping_result = mapper.suggest_mapping(sql_cols, snow_cols)

            mappings.append({
                "sql_server_table": sql_table,
                "snowflake_table": snow_table_actual,
                "sql_columns": sql_metadata[sql_table]["columns"],
                "snowflake_columns": snow_metadata[snow_table_actual]["columns"],
                "column_mappings": column_mapping_result,
                "relationships": sql_metadata[sql_table]["relationships"],
                "match_status": "found_in_both",
                "schema": sql_metadata[sql_table].get("schema", "dbo"),
                "sql_object_type": sql_metadata[sql_table].get("object_type", "TABLE"),
                "snow_object_type": snow_metadata[snow_table_actual].get("object_type", "TABLE")
            })
        else:
            mappings.append({
                "sql_server_table": sql_table,
                "snowflake_table": None,
                "sql_columns": sql_metadata[sql_table]["columns"],
                "snowflake_columns": {},
                "column_mappings": {"mappings": [], "unmatched_source": [], "unmatched_target": [], "stats": {}},
                "relationships": sql_metadata[sql_table]["relationships"],
                "match_status": "only_in_sql_server",
                "schema": sql_metadata[sql_table].get("schema", "dbo"),
                "sql_object_type": sql_metadata[sql_table].get("object_type", "TABLE")
            })

    # Find Snowflake-only tables
    for snow_table in snow_metadata:
        if snow_table not in matched_snow_tables:
            mappings.append({
                "sql_server_table": None,
                "snowflake_table": snow_table,
                "sql_columns": {},
                "snowflake_columns": snow_metadata[snow_table]["columns"],
                "column_mappings": {"mappings": [], "unmatched_source": [], "unmatched_target": [], "stats": {}},
                "relationships": {},
                "match_status": "only_in_snowflake",
                "schema": snow_metadata[snow_table].get("schema", "PUBLIC"),
                "snow_object_type": snow_metadata[snow_table].get("object_type", "TABLE")
            })

    return mappings


def generate_yaml_files(mappings: List[Dict], request: DatabaseMappingRequest, schema_mappings: Dict[str, str] = None) -> Dict:
    """Generate YAML files that the core engine expects"""

    # Create tables.yaml structure
    tables_yaml = {
        "sql": {},
        "snow": {}
    }

    # Create relationships.yaml structure
    relationships_yaml = []

    # Create column_mappings.yaml structure
    column_mappings_yaml = {}

    for mapping in mappings:
        sql_table = mapping.get("sql_server_table")
        snow_table = mapping.get("snowflake_table")

        # Add ALL SQL Server tables (including SQL-only) with object_type
        if sql_table and mapping.get("sql_columns"):
            tables_yaml["sql"][sql_table] = {
                "columns": mapping["sql_columns"],
                "object_type": mapping.get("sql_object_type", "TABLE")
            }

        # Add ALL Snowflake tables (including Snowflake-only) with object_type
        if snow_table and mapping.get("snowflake_columns"):
            tables_yaml["snow"][snow_table] = {
                "columns": mapping["snowflake_columns"],
                "object_type": mapping.get("snow_object_type", "TABLE")
            }

        # Add column mappings and relationships only for matched tables
        if mapping["match_status"] == "found_in_both" and sql_table and snow_table:
            # Add column mappings
            if mapping.get("column_mappings"):
                column_mappings_yaml[sql_table] = {
                    "target_table": snow_table,
                    "mappings": mapping["column_mappings"]["mappings"],
                    "unmatched_source": mapping["column_mappings"]["unmatched_source"],
                    "unmatched_target": mapping["column_mappings"]["unmatched_target"],
                    "stats": mapping["column_mappings"]["stats"]
                }

            # Add relationships
            for fk_col, ref in mapping.get("relationships", {}).items():
                relationships_yaml.append({
                    "fact_table": sql_table,
                    "fk_column": fk_col,
                    "dim_reference": ref
                })

    # Save to core's config directory
    try:
        import sys
        sys.path.insert(0, "/core/src")

        config_dir = "/core/src/ombudsman/config"
        os.makedirs(config_dir, exist_ok=True)

        with open(f"{config_dir}/tables.yaml", "w") as f:
            yaml.dump(tables_yaml, f, default_flow_style=False)

        with open(f"{config_dir}/relationships.yaml", "w") as f:
            yaml.dump(relationships_yaml, f, default_flow_style=False)

        with open(f"{config_dir}/column_mappings.yaml", "w") as f:
            yaml.dump(column_mappings_yaml, f, default_flow_style=False)

        # Save schema mappings if provided
        if schema_mappings:
            with open(f"{config_dir}/schema_mappings.yaml", "w") as f:
                yaml.dump(schema_mappings, f, default_flow_style=False)

        # Calculate total column mappings
        total_column_mappings = sum(len(cm["mappings"]) for cm in column_mappings_yaml.values())
        total_unmapped_columns = sum(len(cm["unmatched_source"]) for cm in column_mappings_yaml.values())

        return {
            "tables_yaml": f"{config_dir}/tables.yaml",
            "relationships_yaml": f"{config_dir}/relationships.yaml",
            "column_mappings_yaml": f"{config_dir}/column_mappings.yaml",
            "schema_mappings_yaml": f"{config_dir}/schema_mappings.yaml" if schema_mappings else None,
            "sql_tables_count": len(tables_yaml["sql"]),
            "snow_tables_count": len(tables_yaml["snow"]),
            "matched_tables_count": len([m for m in mappings if m["match_status"] == "found_in_both"]),
            "relationships_count": len(relationships_yaml),
            "column_mappings_count": total_column_mappings,
            "unmapped_columns_count": total_unmapped_columns,
            "schema_mappings_count": len(schema_mappings) if schema_mappings else 0
        }
    except Exception as e:
        return {
            "error": f"Failed to save YAML files: {str(e)}"
        }


@router.get("/mappings")
async def get_existing_mappings():
    """
    Read existing mappings from YAML files.
    Returns the current state of tables.yaml and relationships.yaml.
    Uses active project's config if available, otherwise falls back to core config.
    """
    try:
        # Try to get active project's config directory
        import sys
        sys.path.insert(0, "/app/projects")
        from context import get_active_project, get_project_config_dir, set_active_project
        import json as json_lib

        active_project = get_active_project()

        # If no active project, try to load the most recent project
        if not active_project:
            try:
                import glob
                project_dirs = glob.glob("/data/projects/*/project.json")
                if project_dirs:
                    # Sort by modification time, get most recent
                    latest_project = max(project_dirs, key=os.path.getmtime)
                    with open(latest_project, 'r') as f:
                        metadata = json_lib.load(f)
                        project_id = metadata.get('project_id')
                        set_active_project(project_id, metadata)
                        active_project = get_active_project()
                        print(f"[DEBUG] Auto-loaded most recent project: {project_id}")
            except Exception as e:
                print(f"[DEBUG] Failed to auto-load project: {e}")

        config_dir = get_project_config_dir()

        print(f"[DEBUG] Getting mappings from config_dir: {config_dir}")
        print(f"[DEBUG] Active project: {active_project.get('project_id') if active_project else 'None'}")

        tables_file = f"{config_dir}/tables.yaml"
        relationships_file = f"{config_dir}/relationships.yaml"
        overrides_file = f"{config_dir}/mapping_overrides.yaml"
        column_mappings_file = f"{config_dir}/column_mappings.yaml"

        # Check if files exist
        if not os.path.exists(tables_file):
            # Return project's database config if available
            if active_project:
                return {
                    "status": "no_mappings",
                    "message": "No mappings found. Please run extraction first.",
                    "project_config": {
                        "sql_database": active_project.get("sql_database"),
                        "sql_schemas": active_project.get("sql_schemas", []),
                        "snowflake_database": active_project.get("snowflake_database"),
                        "snowflake_schemas": active_project.get("snowflake_schemas", []),
                        "schema_mappings": active_project.get("schema_mappings", {})
                    }
                }
            return {
                "status": "no_mappings",
                "message": "No mappings found. Please run extraction first."
            }

        # Load YAML files
        with open(tables_file, "r") as f:
            tables_data = yaml.safe_load(f) or {"sql": {}, "snow": {}}

        with open(relationships_file, "r") as f:
            relationships_data = yaml.safe_load(f) or []

        # Load overrides if they exist
        overrides = {}
        if os.path.exists(overrides_file):
            with open(overrides_file, "r") as f:
                overrides = yaml.safe_load(f) or {}

        # Load column mappings if they exist
        column_mappings_data = {}
        if os.path.exists(column_mappings_file):
            with open(column_mappings_file, "r") as f:
                column_mappings_data = yaml.safe_load(f) or {}

        # Convert YAML structure to mappings format
        mappings = []
        sql_tables = tables_data.get("sql", {})
        snow_tables = tables_data.get("snow", {})

        # Create reverse lookup for relationships
        table_relationships = {}
        for rel in relationships_data:
            fact_table = rel.get("fact_table")
            if fact_table not in table_relationships:
                table_relationships[fact_table] = {}
            table_relationships[fact_table][rel.get("fk_column")] = rel.get("dim_reference")

        # Build mappings from SQL tables
        matched_snow_tables = set()
        for sql_table, sql_columns in sql_tables.items():
            # Check if there's a custom override
            if sql_table in overrides:
                snow_table = overrides[sql_table]
            else:
                # Default matching: schema.table -> schema.TABLE (only uppercase table name)
                if '.' in sql_table:
                    schema, table = sql_table.rsplit('.', 1)
                    snow_table = f"{schema}.{table.upper()}"
                else:
                    snow_table = sql_table.upper()

            if snow_table in snow_tables:
                matched_snow_tables.add(snow_table)

                # Get column mappings for this table
                col_mapping_info = column_mappings_data.get(sql_table, {
                    "mappings": [],
                    "unmatched_source": [],
                    "unmatched_target": [],
                    "stats": {}
                })

                mappings.append({
                    "sql_server_table": sql_table,
                    "snowflake_table": snow_table,
                    "sql_columns": sql_columns,
                    "snowflake_columns": snow_tables[snow_table],
                    "column_mappings": col_mapping_info,
                    "relationships": table_relationships.get(sql_table, {}),
                    "match_status": "found_in_both",
                    "is_custom_mapping": sql_table in overrides
                })
            else:
                mappings.append({
                    "sql_server_table": sql_table,
                    "snowflake_table": None,
                    "sql_columns": sql_columns,
                    "snowflake_columns": {},
                    "column_mappings": {"mappings": [], "unmatched_source": [], "unmatched_target": [], "stats": {}},
                    "relationships": table_relationships.get(sql_table, {}),
                    "match_status": "only_in_sql_server",
                    "is_custom_mapping": False
                })

        # Add Snowflake-only tables
        for snow_table, snow_columns in snow_tables.items():
            if snow_table not in matched_snow_tables:
                mappings.append({
                    "sql_server_table": None,
                    "snowflake_table": snow_table,
                    "sql_columns": {},
                    "snowflake_columns": snow_columns,
                    "column_mappings": {"mappings": [], "unmatched_source": [], "unmatched_target": [], "stats": {}},
                    "relationships": {},
                    "match_status": "only_in_snowflake",
                    "is_custom_mapping": False
                })

        # Calculate column mapping stats
        total_col_mappings = sum(
            len(m.get("column_mappings", {}).get("mappings", []))
            for m in mappings
        )

        response = {
            "status": "success",
            "mappings": mappings,
            "overrides": overrides,
            "total_mappings": len(mappings),
            "column_mappings_count": total_col_mappings,
            "files": {
                "tables_yaml": tables_file,
                "relationships_yaml": relationships_file,
                "overrides_yaml": overrides_file if os.path.exists(overrides_file) else None,
                "column_mappings_yaml": column_mappings_file if os.path.exists(column_mappings_file) else None
            }
        }

        # Include project config if active
        if active_project:
            response["project_config"] = {
                "project_id": active_project.get("project_id"),
                "project_name": active_project.get("name"),
                "sql_database": active_project.get("sql_database"),
                "sql_schemas": active_project.get("sql_schemas", []),
                "snowflake_database": active_project.get("snowflake_database"),
                "snowflake_schemas": active_project.get("snowflake_schemas", []),
                "schema_mappings": active_project.get("schema_mappings", {})
            }

        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load mappings: {str(e)}")


class MappingUpdate(BaseModel):
    """Request to update table name mappings"""
    overrides: Dict[str, str]  # sql_table -> snow_table custom mappings
    mappings: List[Dict]  # Full mappings list to save


@router.put("/mappings")
async def update_mappings(update: MappingUpdate):
    """
    Save edited mappings back to YAML files.
    Supports custom table name overrides (e.g., dim_1 -> customer).
    """
    try:
        config_dir = "/core/src/ombudsman/config"
        os.makedirs(config_dir, exist_ok=True)

        # Backup existing files
        import shutil
        from datetime import datetime
        backup_dir = f"{config_dir}/backups"
        os.makedirs(backup_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        for filename in ["tables.yaml", "relationships.yaml", "mapping_overrides.yaml"]:
            src = f"{config_dir}/{filename}"
            if os.path.exists(src):
                dst = f"{backup_dir}/{filename}.{timestamp}"
                shutil.copy2(src, dst)

        # Load MappingLoader for column mapping generation
        import sys
        sys.path.insert(0, "/core/src")
        from ombudsman.core.mapping_loader import MappingLoader
        mapper = MappingLoader()

        # Load existing column mappings
        column_mappings_file = f"{config_dir}/column_mappings.yaml"
        column_mappings_yaml = {}
        if os.path.exists(column_mappings_file):
            with open(column_mappings_file, "r") as f:
                column_mappings_yaml = yaml.safe_load(f) or {}

        # Load existing tables.yaml to get column info for newly mapped tables
        existing_tables = {"sql": {}, "snow": {}}
        tables_file = f"{config_dir}/tables.yaml"
        if os.path.exists(tables_file):
            with open(tables_file, "r") as f:
                existing_tables = yaml.safe_load(f) or {"sql": {}, "snow": {}}

        # Rebuild YAML structures from mappings
        tables_yaml = {"sql": {}, "snow": {}}
        relationships_yaml = []

        for mapping in update.mappings:
            sql_table = mapping.get("sql_server_table")
            snow_table = mapping.get("snowflake_table")

            # Handle all tables (not just found_in_both)
            if sql_table and mapping.get("sql_columns"):
                tables_yaml["sql"][sql_table] = mapping.get("sql_columns", {})

            if snow_table and mapping.get("snowflake_columns"):
                tables_yaml["snow"][snow_table] = mapping.get("snowflake_columns", {})

            # Generate column mappings for found_in_both tables
            if mapping.get("match_status") == "found_in_both" and sql_table and snow_table:
                # Check if column mappings already exist
                if sql_table not in column_mappings_yaml:
                    # Get columns (from mapping or existing tables.yaml)
                    sql_columns = mapping.get("sql_columns", {}) or existing_tables.get("sql", {}).get(sql_table, {})
                    snow_columns = mapping.get("snowflake_columns", {}) or existing_tables.get("snow", {}).get(snow_table, {})

                    # Generate new column mappings
                    sql_cols = [{"name": col, "data_type": dtype} for col, dtype in sql_columns.items()]
                    snow_cols = [{"name": col, "data_type": dtype} for col, dtype in snow_columns.items()]

                    if sql_cols and snow_cols:
                        column_mapping_result = mapper.suggest_mapping(sql_cols, snow_cols)
                        column_mappings_yaml[sql_table] = {
                            "target_table": snow_table,
                            "mappings": column_mapping_result["mappings"],
                            "unmatched_source": column_mapping_result["unmatched_source"],
                            "unmatched_target": column_mapping_result["unmatched_target"],
                            "stats": column_mapping_result["stats"]
                        }

                # Add relationships
                for fk_col, ref in mapping.get("relationships", {}).items():
                    relationships_yaml.append({
                        "fact_table": sql_table,
                        "fk_column": fk_col,
                        "dim_reference": ref
                    })

        # Save YAML files
        with open(f"{config_dir}/tables.yaml", "w") as f:
            yaml.dump(tables_yaml, f, default_flow_style=False, sort_keys=False)

        with open(f"{config_dir}/relationships.yaml", "w") as f:
            yaml.dump(relationships_yaml, f, default_flow_style=False, sort_keys=False)

        # Save column mappings
        with open(f"{config_dir}/column_mappings.yaml", "w") as f:
            yaml.dump(column_mappings_yaml, f, default_flow_style=False, sort_keys=False)

        # Save overrides
        with open(f"{config_dir}/mapping_overrides.yaml", "w") as f:
            yaml.dump(update.overrides, f, default_flow_style=False, sort_keys=False)

        return {
            "status": "success",
            "message": "Mappings saved successfully",
            "backup_timestamp": timestamp,
            "files_updated": {
                "tables_yaml": f"{config_dir}/tables.yaml",
                "relationships_yaml": f"{config_dir}/relationships.yaml",
                "column_mappings_yaml": f"{config_dir}/column_mappings.yaml",
                "overrides_yaml": f"{config_dir}/mapping_overrides.yaml"
            },
            "tables_count": len([m for m in update.mappings if m.get("match_status") == "found_in_both"]),
            "relationships_count": len(relationships_yaml),
            "column_mappings_count": len(column_mappings_yaml),
            "custom_overrides_count": len(update.overrides)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save mappings: {str(e)}")


@router.get("/available-schemas")
async def get_available_schemas(sql_database: str = "SampleDW", snowflake_database: str = "SAMPLEDW"):
    """Get list of available schemas from both SQL Server and Snowflake databases"""
    try:
        result = {
            "sql_server": [],
            "snowflake": []
        }

        # Get SQL Server schemas
        try:
            conn_str = os.getenv("SQLSERVER_CONN_STR", "")
            # Replace database in connection string
            if "DATABASE=" in conn_str:
                parts = conn_str.split(";")
                for i, part in enumerate(parts):
                    if part.startswith("DATABASE="):
                        parts[i] = f"DATABASE={sql_database}"
                conn_str = ";".join(parts)

            conn = pyodbc.connect(conn_str)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT SCHEMA_NAME
                FROM INFORMATION_SCHEMA.SCHEMATA
                WHERE SCHEMA_NAME NOT IN ('sys', 'INFORMATION_SCHEMA', 'guest', 'db_owner', 'db_accessadmin',
                                           'db_securityadmin', 'db_ddladmin', 'db_backupoperator', 'db_datareader',
                                           'db_datawriter', 'db_denydatareader', 'db_denydatawriter')
                ORDER BY SCHEMA_NAME
            """)
            result["sql_server"] = [row[0] for row in cursor.fetchall()]
            cursor.close()
            conn.close()
        except Exception as e:
            result["sql_server_error"] = str(e)

        # Get Snowflake schemas
        try:
            conn = snowflake.connector.connect(
                user=os.getenv("SNOWFLAKE_USER"),
                password=os.getenv("SNOWFLAKE_PASSWORD"),
                account=os.getenv("SNOWFLAKE_ACCOUNT"),
                warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
                role=os.getenv("SNOWFLAKE_ROLE"),
                database=snowflake_database
            )
            cursor = conn.cursor()
            cursor.execute("SHOW SCHEMAS")
            result["snowflake"] = [row[1] for row in cursor.fetchall() if row[1] not in ['INFORMATION_SCHEMA']]
            cursor.close()
            conn.close()
        except Exception as e:
            result["snowflake_error"] = str(e)

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/schema-mappings")
async def get_schema_mappings():
    """Get existing schema mappings"""
    try:
        config_dir = "/core/src/ombudsman/config"
        schema_mappings_file = f"{config_dir}/schema_mappings.yaml"

        # Load schema mappings if they exist
        if os.path.exists(schema_mappings_file):
            with open(schema_mappings_file, "r") as f:
                mappings = yaml.safe_load(f) or {}
        else:
            mappings = {}

        return {
            "status": "success",
            "mappings": mappings,
            "file": schema_mappings_file if os.path.exists(schema_mappings_file) else None
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load schema mappings: {str(e)}")


@router.put("/schema-mappings")
async def update_schema_mappings(update: SchemaMappingUpdate):
    """Save schema mappings"""
    try:
        config_dir = "/core/src/ombudsman/config"
        os.makedirs(config_dir, exist_ok=True)
        schema_mappings_file = f"{config_dir}/schema_mappings.yaml"

        # Backup existing file
        if os.path.exists(schema_mappings_file):
            import shutil
            from datetime import datetime
            backup_dir = f"{config_dir}/backups"
            os.makedirs(backup_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            shutil.copy2(schema_mappings_file, f"{backup_dir}/schema_mappings.yaml.{timestamp}")

        # Save new mappings
        with open(schema_mappings_file, "w") as f:
            yaml.dump(update.mappings, f, default_flow_style=False, sort_keys=False)

        return {
            "status": "success",
            "message": "Schema mappings saved successfully",
            "file": schema_mappings_file,
            "mappings_count": len(update.mappings)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save schema mappings: {str(e)}")


@router.put("/column-mappings")
async def update_column_mappings(update: ColumnMappingUpdate):
    """Save column-level mappings for a specific table"""
    try:
        config_dir = "/core/src/ombudsman/config"
        os.makedirs(config_dir, exist_ok=True)
        column_mappings_file = f"{config_dir}/column_mappings.yaml"

        # Load existing column mappings
        column_mappings = {}
        if os.path.exists(column_mappings_file):
            with open(column_mappings_file, "r") as f:
                column_mappings = yaml.safe_load(f) or {}

        # Backup existing file
        if os.path.exists(column_mappings_file):
            import shutil
            from datetime import datetime
            backup_dir = f"{config_dir}/backups"
            os.makedirs(backup_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            shutil.copy2(column_mappings_file, f"{backup_dir}/column_mappings.yaml.{timestamp}")

        # Update mappings for this table
        column_mappings[update.sql_table] = {
            "target_table": update.snow_table,
            "mappings": update.column_mappings
        }

        # Save updated mappings
        with open(column_mappings_file, "w") as f:
            yaml.dump(column_mappings, f, default_flow_style=False, sort_keys=False)

        return {
            "status": "success",
            "message": f"Column mappings for {update.sql_table} saved successfully",
            "file": column_mappings_file,
            "mappings_count": len(update.column_mappings)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save column mappings: {str(e)}")


@router.get("/available-databases")
async def get_available_databases():
    """Get list of available databases from both SQL Server and Snowflake"""
    try:
        result = {
            "sql_server": [],
            "snowflake": []
        }

        # Get SQL Server databases
        try:
            conn_str = os.getenv("SQLSERVER_CONN_STR", "")
            if "DATABASE=" in conn_str:
                conn_str = conn_str.replace(f"DATABASE={os.getenv('MSSQL_DATABASE', 'master')}", "DATABASE=master")

            conn = pyodbc.connect(conn_str)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sys.databases WHERE name NOT IN ('master', 'tempdb', 'model', 'msdb') ORDER BY name")
            result["sql_server"] = [row[0] for row in cursor.fetchall()]
            # Add common databases
            result["sql_server"].insert(0, "master")
            cursor.close()
            conn.close()
        except Exception as e:
            result["sql_server_error"] = str(e)

        # Get Snowflake databases
        try:
            conn = snowflake.connector.connect(
                user=os.getenv("SNOWFLAKE_USER"),
                password=os.getenv("SNOWFLAKE_PASSWORD"),
                account=os.getenv("SNOWFLAKE_ACCOUNT"),
                warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
                role=os.getenv("SNOWFLAKE_ROLE")
            )
            cursor = conn.cursor()
            cursor.execute("SHOW DATABASES")
            result["snowflake"] = [row[1] for row in cursor.fetchall()]
            cursor.close()
            conn.close()
        except Exception as e:
            result["snowflake_error"] = str(e)

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
