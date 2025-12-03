"""
Custom Business Query Validation API
Enables validation of complex SQL queries with joins, date dimensions, and business logic
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
import sys
import os

# Add ombudsman_core to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../ombudsman_core/src'))

from ombudsman.validation.business import (
    validate_custom_queries,
    load_user_queries,
    load_example_queries,
    get_query_suggestions
)
from ombudsman.validation.business.intelligent_suggest import (
    suggest_queries_from_metadata,
    format_suggestions_for_display,
    save_suggestions_to_yaml
)
from ombudsman.core.metadata_loader import load_metadata
from ombudsman.core.mapping_loader import load_mapping
from ombudsman.core.connections import get_sql_conn, get_snow_conn

router = APIRouter()


class QueryDefinition(BaseModel):
    name: str
    comparison_type: str = "aggregation"  # aggregation, rowset, count
    tolerance: float = 0.01
    limit: Optional[int] = 100
    sql_query: str
    snow_query: str


class ValidateQueriesRequest(BaseModel):
    queries: List[QueryDefinition]
    sql_server_config: Optional[Dict[str, str]] = None
    snowflake_config: Optional[Dict[str, str]] = None


@router.get("/examples")
def get_examples():
    """
    Get all 12 example query templates

    Returns ready-to-use query examples for:
    - Multi-table joins
    - Date-based analytics
    - Top N queries
    - Random sampling
    - And more...
    """
    try:
        examples = load_example_queries()
        return {
            "status": "success",
            "count": len(examples),
            "examples": examples
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/user-queries")
def get_user_queries():
    """
    Get user-defined queries from config/custom_queries.yaml
    """
    try:
        queries = load_user_queries()
        return {
            "status": "success",
            "count": len(queries),
            "queries": queries
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/suggestions")
def get_suggestions():
    """
    Get query pattern suggestions to help users create their own queries

    Returns categorized patterns like:
    - Aggregation patterns
    - Date patterns
    - Top N patterns
    - Join patterns
    - Filter patterns
    - Advanced patterns
    """
    try:
        suggestions = get_query_suggestions()
        return {
            "status": "success",
            "suggestions": suggestions
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/validate")
def validate_queries(request: ValidateQueriesRequest):
    """
    Validate custom business queries

    Compares query results between SQL Server and Snowflake.
    Supports:
    - Single aggregation values (totals, averages)
    - Multiple rows (grouped data, time series)
    - Simple counts

    Always returns detailed explain data with:
    - Sample results
    - Execution times
    - Interpretation messages
    - Debug queries
    """
    try:
        # Convert Pydantic models to dicts
        queries = [q.model_dump() for q in request.queries]

        # Set up connections (using environment variables or provided config)
        sql_config = request.sql_server_config or {}
        snow_config = request.snowflake_config or {}

        # Create config dicts for get_sql_conn and get_snow_conn
        sql_cfg = {
            'server': sql_config.get('server', os.getenv('SQL_SERVER_HOST', 'localhost')),
            'database': sql_config.get('database', os.getenv('SQL_SERVER_DATABASE', 'SampleDW')),
            'username': sql_config.get('username', os.getenv('SQL_SERVER_USER', 'sa')),
            'password': sql_config.get('password', os.getenv('SQL_SERVER_PASSWORD', 'YourStrong@Password123'))
        }

        snow_cfg = {
            'account': snow_config.get('account', os.getenv('SNOWFLAKE_ACCOUNT', 'your-account')),
            'user': snow_config.get('user', os.getenv('SNOWFLAKE_USER', 'your-user')),
            'password': snow_config.get('password', os.getenv('SNOWFLAKE_PASSWORD', 'your-password')),
            'warehouse': snow_config.get('warehouse', os.getenv('SNOWFLAKE_WAREHOUSE', 'COMPUTE_WH')),
            'database': snow_config.get('database', os.getenv('SNOWFLAKE_DATABASE', 'SAMPLEDW')),
            'schema': snow_config.get('schema', os.getenv('SNOWFLAKE_SCHEMA', 'PUBLIC'))
        }

        # Get connections
        sql_conn = get_sql_conn(sql_cfg)
        snow_conn = get_snow_conn(snow_cfg)

        # Run validation
        result = validate_custom_queries(
            sql_conn=sql_conn,
            snow_conn=snow_conn,
            query_definitions=queries,
            mapping={}
        )

        return {
            "status": "success",
            "validation_result": result
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")


@router.post("/validate-user-queries")
def validate_user_defined_queries():
    """
    Validate queries from config/custom_queries.yaml

    Convenience endpoint that loads user queries from config
    and validates them automatically.
    """
    try:
        # Load user queries
        queries = load_user_queries()

        if not queries:
            return {
                "status": "no_queries",
                "message": "No queries found in config/custom_queries.yaml"
            }

        # Set up connections from environment
        sql_cfg = {
            'server': os.getenv('SQL_SERVER_HOST', 'localhost'),
            'database': os.getenv('SQL_SERVER_DATABASE', 'SampleDW'),
            'username': os.getenv('SQL_SERVER_USER', 'sa'),
            'password': os.getenv('SQL_SERVER_PASSWORD', 'YourStrong@Password123')
        }

        snow_cfg = {
            'account': os.getenv('SNOWFLAKE_ACCOUNT', 'your-account'),
            'user': os.getenv('SNOWFLAKE_USER', 'your-user'),
            'password': os.getenv('SNOWFLAKE_PASSWORD', 'your-password'),
            'warehouse': os.getenv('SNOWFLAKE_WAREHOUSE', 'COMPUTE_WH'),
            'database': os.getenv('SNOWFLAKE_DATABASE', 'SAMPLEDW'),
            'schema': os.getenv('SNOWFLAKE_SCHEMA', 'PUBLIC')
        }

        sql_conn = get_sql_conn(sql_cfg)
        snow_conn = get_snow_conn(snow_cfg)

        # Run validation
        result = validate_custom_queries(
            sql_conn=sql_conn,
            snow_conn=snow_conn,
            query_definitions=queries,
            mapping={}
        )

        return {
            "status": "success",
            "queries_validated": len(queries),
            "validation_result": result
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")


@router.get("/config-location")
def get_config_location():
    """
    Get the file path where users should add their custom queries
    """
    import os
    from pathlib import Path

    config_dir = Path(__file__).parent.parent.parent.parent / 'ombudsman_core' / 'src' / 'ombudsman' / 'config'

    return {
        "user_queries_file": str(config_dir / 'custom_queries.yaml'),
        "examples_file": str(config_dir / 'custom_query_examples.yaml'),
        "readme": str(Path(__file__).parent.parent.parent.parent / 'ombudsman_core' / 'src' / 'ombudsman' / 'validation' / 'business' / 'README.md')
    }


class IntelligentSuggestRequest(BaseModel):
    fact_table: Optional[str] = None  # Optional: focus suggestions on this fact table


@router.post("/intelligent-suggest")
def intelligent_suggest_queries(request: IntelligentSuggestRequest = None):
    """
    **INTELLIGENT QUERY SUGGESTION** 🧠

    Automatically generate custom query suggestions based on your actual database schema!

    This endpoint:
    1. Loads your metadata (tables, columns, types)
    2. Analyzes star schema patterns (fact & dimension tables)
    3. Infers foreign key relationships automatically
    4. Generates multi-dimensional analytical queries

    Returns suggested queries for:
    - Single dimension aggregations (Sales by Category)
    - Multi-dimensional aggregations (Sales by Category AND Region)
    - Fact-dimension conformance checks (orphaned foreign keys)
    - Time-based analytics (if date dimensions detected)
    - All with proper JOINs and GROUP BY clauses

    **Thinks like a data analyst! 🎯**
    """
    try:
        # Use the new intelligent query generator
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../pipelines'))
        from intelligent_query_generator import IntelligentQueryGenerator

        # Initialize generator
        generator = IntelligentQueryGenerator()

        # Generate queries for Snowflake (since that's target system)
        intelligent_queries = generator.generate_intelligent_queries(database="snow")

        if not intelligent_queries:
            return {
                "status": "warning",
                "message": "No fact tables found with proper foreign key relationships. Please ensure:\n"
                          "1. Metadata has been extracted (Database Mapping page)\n"
                          "2. Tables follow naming conventions (fact_*, dim_*)\n"
                          "3. Foreign keys follow patterns (dim_<table>_key)",
                "total_suggestions": 0,
                "suggestions": []
            }

        # Group by pattern for display
        categorized = {}
        for query in intelligent_queries:
            pattern = query.get('pattern', 'other')
            category = {
                'single_dimension_aggregation': 'Single Dimension Analysis',
                'multi_dimension_aggregation': 'Multi-Dimensional Analysis',
                'fact_dimension_conformance': 'Referential Integrity Checks'
            }.get(pattern, 'Other Queries')

            if category not in categorized:
                categorized[category] = []

            # Format for display
            categorized[category].append({
                'name': query['name'],
                'description': query['description'],
                'sql_server_query': query['sql_server_query'],
                'snowflake_query': query['snowflake_query'],
                'complexity': query.get('complexity', 'medium'),
                'analytical_value': query.get('analytical_value', 'high'),
                'fact_table': query.get('fact_table', ''),
                'dimension_tables': query.get('dimension_tables', []),
                'measures': query.get('measures', []),
                'group_by': query.get('group_by', [])
            })

        return {
            "status": "success",
            "total_suggestions": len(intelligent_queries),
            "suggestions_by_category": categorized,
            "all_suggestions": intelligent_queries,
            "message": f"Generated {len(intelligent_queries)} intelligent query suggestions based on star schema analysis!",
            "intelligence_applied": [
                "✓ Detected fact and dimension tables",
                "✓ Inferred foreign key relationships",
                "✓ Identified measures vs identifiers",
                "✓ Generated multi-dimensional JOINs",
                "✓ Created conformance checks",
                "✓ Suggested analytical aggregations"
            ],
            "next_steps": [
                "1. Review the suggestions below - they're ready to use!",
                "2. Copy queries to your validation pipeline",
                "3. Or use /custom-queries/save-suggestions to auto-save them",
                "4. Run validations to compare SQL Server vs Snowflake"
            ]
        }

    except Exception as e:
        import traceback
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate intelligent suggestions: {str(e)}\n{traceback.format_exc()}"
        )


@router.post("/save-suggestions")
def save_intelligent_suggestions():
    """
    Save intelligently generated suggestions directly to custom_queries.yaml

    This is a convenience endpoint that:
    1. Generates intelligent suggestions (like /intelligent-suggest)
    2. Automatically saves them to your custom_queries.yaml file
    3. You can then validate them immediately!
    """
    try:
        # Load metadata and mapping (same as above)
        metadata_path = os.path.join(
            os.path.dirname(__file__),
            '../../ombudsman_core/data/metadata.json'
        )

        if not os.path.exists(metadata_path):
            return {
                "status": "error",
                "message": "No metadata found. Please extract metadata first"
            }

        metadata = load_metadata(metadata_path)

        mapping_path = os.path.join(
            os.path.dirname(__file__),
            '../../ombudsman_core/data/mapping.json'
        )

        if not os.path.exists(mapping_path):
            return {
                "status": "error",
                "message": "No mapping found. Please generate mapping first"
            }

        mapping = load_mapping(mapping_path)

        # Load relationships
        relationships = None
        relationships_path = os.path.join(
            os.path.dirname(__file__),
            '../../ombudsman_core/src/ombudsman/config/relationships.yaml'
        )

        if os.path.exists(relationships_path):
            import yaml
            with open(relationships_path, 'r') as f:
                relationships = yaml.safe_load(f)

        # Generate suggestions
        suggestions = suggest_queries_from_metadata(metadata, mapping, relationships)

        # Save to file
        output_path = os.path.join(
            os.path.dirname(__file__),
            '../../ombudsman_core/src/ombudsman/config/custom_queries.yaml'
        )

        count = save_suggestions_to_yaml(suggestions, output_path)

        return {
            "status": "success",
            "saved_count": count,
            "saved_to": output_path,
            "message": f"Saved {count} intelligent query suggestions to custom_queries.yaml!",
            "next_steps": [
                "1. View them: GET /custom-queries/user-queries",
                "2. Validate them: POST /custom-queries/validate-user-queries"
            ]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save suggestions: {str(e)}")
