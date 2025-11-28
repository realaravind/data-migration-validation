# core_adapter.py

import sys
import os

# Add path to the ombudsman_core/src folder
CORE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "ombudsman_core", "src"))
sys.path.append(CORE_PATH)

# --- METADATA EXTRACTION -------------------------------------------------

def get_metadata(connection_string: str, table_name: str):
    """
    Extract column metadata using Ombudsman Core.
    """
    try:
        from ombudsman.core.metadata_loader import MetadataLoader
        loader = MetadataLoader(connection_string)
        cols = loader.get_columns(table_name)
        return {"columns": cols}
    except Exception as e:
        return {"columns": [], "error": str(e)}


# --- MAPPING SUGGESTIONS -------------------------------------------------

def generate_mapping(source_cols, target_cols):
    """
    Generate column mappings using Ombudsman Core mapping loader.
    """
    try:
        from ombudsman.core.mapping_loader import MappingLoader
        ml = MappingLoader()
        return ml.suggest_mapping(source_cols, target_cols)
    except Exception as e:
        return {"error": str(e)}


# --- VALIDATION RULES -----------------------------------------------------

def run_validations(config: dict):
    """
    Execute all validations using Ombudsman Core engines.
    """
    try:
        from ombudsman.validation.run_validations import run_all_validations
        return run_all_validations(config)
    except Exception as e:
        return {"error": str(e)}


# --- PIPELINE EXECUTION ---------------------------------------------------

def run_pipeline(config_path: str):
    """
    Run YAML-based validation pipelines.
    """
    try:
        from ombudsman.pipeline.pipeline_runner import PipelineRunner
        runner = PipelineRunner(config_path)
        return runner.run()
    except Exception as e:
        return {"error": str(e)}