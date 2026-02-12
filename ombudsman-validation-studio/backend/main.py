import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Initialize logging first
from logs.config import setup_logging
setup_logging()

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
from connections.pool_stats import router as pool_stats_router
from data.generate import router as data_router
from mapping.database_mapping import router as database_mapping_router
from mapping.intelligent_router import router as intelligent_mapping_router
from projects.manager import router as projects_router
from queries.custom import router as custom_queries_router
from queries.results_api import router as query_results_router
from workload.api import router as workload_router
from results.history import router as results_history_router
from ws.router import router as websocket_router
from auth.router import router as auth_router
from audit.router import router as audit_router
from audit.middleware import AuditMiddleware
from audit.audit_logger import audit_logger
from notifications.router import router as notifications_router
from batch.router import router as batch_router
from docs.serve import router as docs_router
from automation.auto_setup import router as automation_router
from bugs.router import router as bugs_router
from logs.router import router as logs_router
from alerts.router import router as alerts_router
from oauth.snowflake import router as oauth_snowflake_router

# Error handling
from errors import register_error_handlers

app = FastAPI(
    title="Ombudsman Validation Studio API",
    description="Complete API exposing all Ombudsman Core features - by Plural Insight",
    version="2.0.0"
)

# Register error handlers
register_error_handlers(app)

# Add CORS middleware
# Note: In production, restrict allow_origins to your actual frontend domains
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:3002,http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add audit logging middleware
app.add_middleware(AuditMiddleware)

# Log application startup
audit_logger.log_system_event(
    action="application_startup",
    details={"version": "2.0.0"}
)

# Original routers
app.include_router(metadata_router, prefix="/metadata", tags=["Metadata"])
app.include_router(mapping_router, prefix="/mapping", tags=["Mapping"])
app.include_router(mermaid_router, prefix="/mermaid", tags=["Mermaid"])
app.include_router(rules_router, prefix="/rules", tags=["Rules"])
app.include_router(pipeline_router, prefix="/pipeline", tags=["Pipeline"])
app.include_router(execution_router, prefix="/execution", tags=["Execution"])
app.include_router(results_router, prefix="/results", tags=["Results"])

# Authentication router (must be first for security)
app.include_router(auth_router, tags=["Authentication"])

# Audit logging router
app.include_router(audit_router, tags=["Audit Logs"])

# NEW comprehensive routers
app.include_router(pipeline_execute_router, prefix="/pipelines", tags=["Pipeline Execution"])
app.include_router(intelligent_suggest_router, prefix="/pipelines", tags=["Intelligent Pipeline Suggestions"])
app.include_router(connections_router, prefix="/connections", tags=["Connections"])
app.include_router(pool_stats_router, prefix="/connections", tags=["Connection Pools"])
app.include_router(data_router, prefix="/data", tags=["Sample Data"])
app.include_router(database_mapping_router, prefix="/database-mapping", tags=["Database Mapping"])
app.include_router(intelligent_mapping_router, prefix="/mapping", tags=["Intelligent Mapping"])
app.include_router(projects_router, prefix="/projects", tags=["Projects"])
app.include_router(custom_queries_router, prefix="/custom-queries", tags=["Custom Business Queries"])
app.include_router(query_results_router, prefix="/custom-queries/results", tags=["Query Results Management"])
app.include_router(workload_router, prefix="/workload", tags=["Workload Analysis"])
app.include_router(results_history_router, prefix="/history", tags=["Results History"])
app.include_router(websocket_router, tags=["WebSocket Real-time Updates"])
app.include_router(notifications_router, prefix="/notifications", tags=["Notifications"])
app.include_router(batch_router, prefix="/batch", tags=["Batch Operations"])

# Set up main event loop for WebSocket broadcasts from background threads
@app.on_event("startup")
async def startup_event():
    import asyncio
    from batch.job_manager import set_main_event_loop
    loop = asyncio.get_running_loop()
    set_main_event_loop(loop)
    print(f"[STARTUP] Main event loop registered for WebSocket broadcasts")
app.include_router(bugs_router, tags=["Bug Reports"])
app.include_router(docs_router, prefix="/docs", tags=["Documentation"])
app.include_router(automation_router, tags=["Automation"])
app.include_router(logs_router, prefix="/logs", tags=["Application Logs"])
app.include_router(alerts_router, prefix="/alerts", tags=["System Alerts"])
app.include_router(oauth_snowflake_router, prefix="/oauth/snowflake", tags=["OAuth - Snowflake"])


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