"""
FastAPI Router for Intelligent Mapping System

Provides endpoints for:
- ML-based mapping suggestions
- Learning from user feedback
- Pattern insights and statistics
- Mapping history management
"""

from fastapi import APIRouter, HTTPException, Depends, Body
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

from auth.dependencies import require_user_or_admin, optional_authentication
from auth.models import UserInDB
from .ml_mapper import IntelligentMapper


router = APIRouter()

# Initialize intelligent mapper (singleton)
intelligent_mapper = IntelligentMapper()


# ==================== Request/Response Models ====================

class ColumnMetadata(BaseModel):
    """Column metadata for mapping"""
    name: str = Field(..., description="Column name")
    data_type: Optional[str] = Field(None, description="Data type")
    is_nullable: Optional[bool] = Field(None, description="Is nullable")
    is_primary_key: Optional[bool] = Field(None, description="Is primary key")
    is_foreign_key: Optional[bool] = Field(None, description="Is foreign key")


class MappingRequest(BaseModel):
    """Request for intelligent mapping suggestions"""
    source_columns: List[ColumnMetadata] = Field(..., description="Source columns")
    target_columns: List[ColumnMetadata] = Field(..., description="Target columns")
    context: Optional[Dict[str, Any]] = Field(None, description="Optional context (project, schema, etc.)")


class LearnMappingRequest(BaseModel):
    """Request to learn from a mapping"""
    source_column: str = Field(..., description="Source column name")
    target_column: str = Field(..., description="Target column name")
    source_type: Optional[str] = Field(None, description="Source data type")
    target_type: Optional[str] = Field(None, description="Target data type")
    transformation: Optional[str] = Field(None, description="Transformation rule")
    context: Optional[Dict[str, Any]] = Field(None, description="Context information")


class CorrectionRequest(BaseModel):
    """Request to learn from a correction"""
    suggested_mapping: Dict[str, Any] = Field(..., description="Original suggested mapping")
    corrected_target: str = Field(..., description="Corrected target column")
    reason: Optional[str] = Field(None, description="Reason for correction")


class BatchLearnRequest(BaseModel):
    """Request to learn from batch of mappings"""
    mappings: List[Dict[str, Any]] = Field(..., description="List of confirmed mappings")
    context: Optional[Dict[str, Any]] = Field(None, description="Context information")


# ==================== Endpoints ====================

@router.post("/intelligent/suggest")
async def suggest_intelligent_mappings(
    request: MappingRequest,
    current_user: Optional[UserInDB] = Depends(optional_authentication)
):
    """
    Generate intelligent mapping suggestions using ML algorithms.

    This endpoint uses multiple algorithms:
    - Levenshtein distance for string similarity
    - Jaro-Winkler for short string matching
    - Token-based matching for word similarities
    - Semantic similarity using predefined mappings
    - Pattern recognition from naming conventions
    - Historical pattern matching from learned mappings
    - Type compatibility scoring

    All scores are combined using an ensemble approach with weighted averaging.
    """
    try:
        # Convert Pydantic models to dicts
        source_cols = [col.dict() for col in request.source_columns]
        target_cols = [col.dict() for col in request.target_columns]

        # Get intelligent suggestions
        result = intelligent_mapper.suggest_mappings(
            source_columns=source_cols,
            target_columns=target_cols,
            context=request.context
        )

        return {
            "status": "success",
            "result": result,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate suggestions: {str(e)}")


@router.post("/intelligent/learn")
async def learn_from_mapping(
    request: LearnMappingRequest,
    current_user: UserInDB = Depends(require_user_or_admin)
):
    """
    Learn from a confirmed mapping (user accepted or manually created).

    This helps the system improve future suggestions by:
    - Extracting naming patterns
    - Building pattern confidence
    - Tracking usage statistics
    - Storing transformation rules

    Requires: User or Admin role
    """
    try:
        intelligent_mapper.learn_from_mapping(
            source_column=request.source_column,
            target_column=request.target_column,
            source_type=request.source_type,
            target_type=request.target_type,
            transformation=request.transformation,
            context=request.context
        )

        return {
            "status": "success",
            "message": f"Learned mapping: {request.source_column} → {request.target_column}",
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to learn mapping: {str(e)}")


@router.post("/intelligent/learn/batch")
async def learn_from_batch(
    request: BatchLearnRequest,
    current_user: UserInDB = Depends(require_user_or_admin)
):
    """
    Learn from a batch of confirmed mappings.

    Use this when importing existing mappings or after completing a project.

    Requires: User or Admin role
    """
    try:
        learned_count = 0

        for mapping in request.mappings:
            intelligent_mapper.learn_from_mapping(
                source_column=mapping.get("source_column"),
                target_column=mapping.get("target_column"),
                source_type=mapping.get("source_type"),
                target_type=mapping.get("target_type"),
                transformation=mapping.get("transformation"),
                context=request.context
            )
            learned_count += 1

        return {
            "status": "success",
            "message": f"Learned {learned_count} mappings",
            "learned_count": learned_count,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to learn batch: {str(e)}")


@router.post("/intelligent/correct")
async def learn_from_correction(
    request: CorrectionRequest,
    current_user: UserInDB = Depends(require_user_or_admin)
):
    """
    Learn from a user correction of a suggested mapping.

    This is important for improving the ML model. When users correct
    a suggestion, the system learns:
    - What patterns were incorrectly matched
    - What the correct pattern should be
    - How to adjust confidence scores

    Requires: User or Admin role
    """
    try:
        intelligent_mapper.learn_from_correction(
            suggested_mapping=request.suggested_mapping,
            corrected_target=request.corrected_target,
            reason=request.reason
        )

        return {
            "status": "success",
            "message": "Learned from correction",
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to learn correction: {str(e)}")


@router.get("/intelligent/patterns")
async def get_pattern_insights(
    current_user: Optional[UserInDB] = Depends(optional_authentication)
):
    """
    Get insights about learned patterns.

    Returns:
    - Total number of learned patterns
    - Top patterns by usage
    - Average confidence scores
    - Pattern statistics
    """
    try:
        insights = intelligent_mapper.get_pattern_insights()

        return {
            "status": "success",
            "insights": insights,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get insights: {str(e)}")


@router.get("/intelligent/statistics")
async def get_mapping_statistics(
    current_user: Optional[UserInDB] = Depends(optional_authentication)
):
    """
    Get overall mapping statistics.

    Returns statistics about:
    - Total mappings generated
    - User corrections
    - Learned patterns
    - Algorithm performance
    """
    try:
        stats = intelligent_mapper.statistics

        return {
            "status": "success",
            "statistics": stats,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get statistics: {str(e)}")


@router.delete("/intelligent/patterns/reset")
async def reset_learned_patterns(
    current_user: UserInDB = Depends(require_user_or_admin)
):
    """
    Reset all learned patterns (use with caution).

    This will clear all learned patterns and start fresh.
    Useful for testing or when patterns become outdated.

    Requires: User or Admin role
    """
    try:
        # Reinitialize mapper (clears patterns)
        global intelligent_mapper
        intelligent_mapper = IntelligentMapper()

        return {
            "status": "success",
            "message": "All learned patterns have been reset",
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reset patterns: {str(e)}")


@router.post("/intelligent/export-patterns")
async def export_learned_patterns(
    current_user: UserInDB = Depends(require_user_or_admin)
):
    """
    Export learned patterns for backup or sharing.

    Requires: User or Admin role
    """
    try:
        patterns = {
            key: {
                "source_pattern": pattern.source_pattern,
                "target_pattern": pattern.target_pattern,
                "confidence": pattern.confidence,
                "usage_count": pattern.usage_count,
                "last_used": pattern.last_used,
                "source_type": pattern.source_type,
                "target_type": pattern.target_type,
                "transformation": pattern.transformation,
            }
            for key, pattern in intelligent_mapper.patterns.items()
        }

        return {
            "status": "success",
            "patterns": patterns,
            "total_patterns": len(patterns),
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to export patterns: {str(e)}")


@router.post("/intelligent/import-patterns")
async def import_learned_patterns(
    patterns: Dict[str, Any] = Body(...),
    current_user: UserInDB = Depends(require_user_or_admin)
):
    """
    Import learned patterns from backup or another system.

    Requires: User or Admin role
    """
    try:
        from .ml_mapper import MappingPattern

        imported_count = 0

        for key, pattern_data in patterns.items():
            pattern = MappingPattern(
                source_pattern=pattern_data["source_pattern"],
                target_pattern=pattern_data["target_pattern"],
                confidence=pattern_data["confidence"],
                usage_count=pattern_data["usage_count"],
                last_used=pattern_data["last_used"],
                source_type=pattern_data.get("source_type"),
                target_type=pattern_data.get("target_type"),
                transformation=pattern_data.get("transformation"),
            )
            intelligent_mapper.patterns[key] = pattern
            imported_count += 1

        # Save patterns
        intelligent_mapper._save_patterns()

        return {
            "status": "success",
            "message": f"Imported {imported_count} patterns",
            "imported_count": imported_count,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to import patterns: {str(e)}")


@router.get("/intelligent/health")
async def health_check():
    """
    Health check for intelligent mapping service.

    Returns system status and configuration.
    """
    return {
        "status": "healthy",
        "service": "Intelligent Mapping System",
        "version": "1.0.0",
        "features": [
            "ML-based similarity scoring",
            "Pattern recognition",
            "Historical learning",
            "User correction learning",
            "Ensemble confidence scoring",
            "Type compatibility analysis"
        ],
        "algorithms": [
            "Exact match",
            "Levenshtein distance",
            "Jaro-Winkler similarity",
            "Token-based matching",
            "Semantic similarity",
            "Pattern matching",
            "Type compatibility",
            "Affix matching",
            "Learned patterns"
        ],
        "learned_patterns": len(intelligent_mapper.patterns),
        "total_corrections": intelligent_mapper.statistics.get("total_corrections", 0),
        "timestamp": datetime.now().isoformat()
    }
