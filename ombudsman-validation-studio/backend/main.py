from mapping.suggest import router as mapping_router
app.include_router(mapping_router, prefix="/mapping", tags=["Mapping"])

from mermaid.diagram import router as mermaid_router
app.include_router(mermaid_router, prefix="/mermaid", tags=["Mermaid"])

from rules.builder import router as rules_router
app.include_router(rules_router, prefix="/rules", tags=["Rules"])

from pipeline.suggest import router as pipeline_suggest_router
app.include_router(pipeline_suggest_router, prefix="/pipeline", tags=["Pipeline"])

from execution.run import router as execution_router
app.include_router(execution_router, prefix="/execution", tags=["Execution"])

from metadata.extract import router as metadata_router
app.include_router(metadata_router, prefix="/metadata", tags=["Metadata"])

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from metadata.extract import router as metadata_router
from mapping.suggest import router as mapping_router
from rules.builder import router as rules_router
from pipeline.suggest import router as pipeline_router
from execution.run import router as execution_router

app = FastAPI(title="Ombudsman Validation Studio API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(metadata_router, prefix="/metadata", tags=["Metadata"])
app.include_router(mapping_router, prefix="/mapping", tags=["Mapping"])
app.include_router(rules_router, prefix="/rules", tags=["Rules"])
app.include_router(pipeline_router, prefix="/pipeline", tags=["Pipeline"])
app.include_router(execution_router, prefix="/execution", tags=["Execution"])


@app.get("/health")
def health():
    return {"status": "ok"}