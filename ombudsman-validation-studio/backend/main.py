from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Original routers
from metadata.extract import router as metadata_router
from mapping.suggest import router as mapping_router
from mermaid.diagram import router as mermaid_router
from rules.builder import router as rules_router
from pipelines.suggest import router as pipeline_router
from execution.run import router as execution_router
from execution.results import router as results_router

# NEW comprehensive routers
from pipelines.execute import router as pipeline_execute_router
from pipelines.intelligent_suggest import router as intelligent_suggest_router
from connections.test import router as connections_router
from data.generate import router as data_router
from mapping.database_mapping import router as database_mapping_router
from projects.manager import router as projects_router
from queries.custom import router as custom_queries_router
from workload.api import router as workload_router
from results.history import router as results_history_router
from ws.router import router as websocket_router

# Error handling
from errors import register_error_handlers

app = FastAPI(
    title="Ombudsman Validation Studio API",
    description="Complete API exposing all Ombudsman Core features - by Plural Insight",
    version="2.0.0"
)

# Register error handlers
register_error_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Original routers
app.include_router(metadata_router, prefix="/metadata", tags=["Metadata"])
app.include_router(mapping_router, prefix="/mapping", tags=["Mapping"])
app.include_router(mermaid_router, prefix="/mermaid", tags=["Mermaid"])
app.include_router(rules_router, prefix="/rules", tags=["Rules"])
app.include_router(pipeline_router, prefix="/pipeline", tags=["Pipeline"])
app.include_router(execution_router, prefix="/execution", tags=["Execution"])
app.include_router(results_router, prefix="/results", tags=["Results"])

# NEW comprehensive routers
app.include_router(pipeline_execute_router, prefix="/pipelines", tags=["Pipeline Execution"])
app.include_router(intelligent_suggest_router, prefix="/pipelines", tags=["Intelligent Pipeline Suggestions"])
app.include_router(connections_router, prefix="/connections", tags=["Connections"])
app.include_router(data_router, prefix="/data", tags=["Sample Data"])
app.include_router(database_mapping_router, prefix="/database-mapping", tags=["Database Mapping"])
app.include_router(projects_router, prefix="/projects", tags=["Projects"])
app.include_router(custom_queries_router, prefix="/custom-queries", tags=["Custom Business Queries"])
app.include_router(workload_router, prefix="/workload", tags=["Workload Analysis"])
app.include_router(results_history_router, prefix="/history", tags=["Results History"])
app.include_router(websocket_router, tags=["WebSocket Real-time Updates"])


@app.get("/")
def root():
    """Root endpoint - lists all available features"""
    return {
        "message": "Ombudsman Validation Studio API",
        "version": "2.0.0",
        "docs": "/docs",
        "all_features": "/features"
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/features")
def list_all_features():
    """List ALL available features from ombudsman_core"""
    return {
        "ombudsman_core_features": {
            "1_metadata_extraction": {
                "endpoint": "POST /metadata/extract",
                "description": "Extract table schemas from SQL Server/Snowflake",
                "returns": "Column names, data types, constraints, primary keys"
            },
            "2_intelligent_mapping": {
                "endpoint": "POST /mapping/suggest",
                "description": "Auto-generate column mappings with AI",
                "features": ["Fuzzy matching", "Prefix normalization", "Type compatibility", "Confidence scoring"]
            },
            "3_pipeline_execution": {
                "execute": "POST /pipelines/execute",
                "list": "GET /pipelines/list",
                "status": "GET /pipelines/status/{run_id}",
                "templates": "GET /pipelines/templates",
                "description": "Execute validation pipelines from YAML"
            },
            "4_connection_testing": {
                "test_sql": "POST /connections/sqlserver",
                "test_snowflake": "POST /connections/snowflake",
                "all_status": "GET /connections/status",
                "description": "Test and monitor database connections"
            },
            "5_sample_data_generation": {
                "generate": "POST /data/generate",
                "status": "GET /data/status/{job_id}",
                "schemas": "GET /data/schemas",
                "clear": "DELETE /data/clear",
                "description": "Generate synthetic test data for dimensions and facts"
            },
            "6_validation_results": {
                "get_results": "GET /execution/results",
                "run_validation": "POST /execution/run",
                "description": "Execute validations and view results"
            },
            "7_mermaid_diagrams": {
                "endpoint": "POST /mermaid/generate",
                "description": "Generate Mermaid diagrams for pipelines"
            },
            "8_rules_builder": {
                "endpoint": "POST /rules/build",
                "description": "Build custom validation rules"
            },
            "9_custom_business_queries": {
                "examples": "GET /custom-queries/examples",
                "suggestions": "GET /custom-queries/suggestions",
                "validate": "POST /custom-queries/validate",
                "user_queries": "GET /custom-queries/user-queries",
                "validate_user": "POST /custom-queries/validate-user-queries",
                "config_location": "GET /custom-queries/config-location",
                "description": "Validate complex business queries with multi-table joins, date dimensions, Top N, and more",
                "features": ["12 ready-to-use templates", "Multi-table joins", "Date-based analytics", "Top N queries", "Random sampling", "Always-on explain data"]
            }
        },
        "total_feature_groups": 9,
        "total_endpoints": 31,
        "interactive_docs": "/docs",
        "status": "All ombudsman_core features now accessible via Studio!"
    }