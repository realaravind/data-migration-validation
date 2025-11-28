from fastapi import APIRouter
import os
import json

router = APIRouter()

RESULTS_DIR = "results"

@router.get("/results")
def fetch_results():
    entries = []
    for file in os.listdir(RESULTS_DIR):
        if file.endswith(".json"):
            with open(os.path.join(RESULTS_DIR, file)) as f:
                entries.append(json.load(f))
    return {"results": entries}