"""
Intelligent Schema Mapping Module
Auto-maps SQL Server schemas to Snowflake schemas using fuzzy matching and AI
"""
from typing import List, Dict, Tuple
from difflib import SequenceMatcher
import re


def normalize_schema_name(schema: str) -> str:
    """Normalize schema name for comparison"""
    # Remove common prefixes/suffixes
    normalized = schema.lower()
    normalized = re.sub(r'^(sample_|test_|prod_|dev_)', '', normalized)
    normalized = re.sub(r'(_schema|_db)$', '', normalized)
    return normalized


def calculate_similarity(sql_schema: str, snow_schema: str) -> float:
    """
    Calculate similarity score between two schema names.
    Returns a score between 0.0 and 1.0
    """
    # Normalize both names
    norm_sql = normalize_schema_name(sql_schema)
    norm_snow = normalize_schema_name(snow_schema)

    # Direct match after normalization
    if norm_sql == norm_snow:
        return 1.0

    # Check if one contains the other
    if norm_sql in norm_snow or norm_snow in norm_sql:
        return 0.9

    # Use SequenceMatcher for fuzzy matching
    return SequenceMatcher(None, norm_sql, norm_snow).ratio()


def auto_map_schemas(
    sql_schemas: List[str],
    snowflake_schemas: List[str],
    confidence_threshold: float = 0.7
) -> Dict[str, Dict[str, any]]:
    """
    Automatically map SQL Server schemas to Snowflake schemas.

    Args:
        sql_schemas: List of SQL Server schema names
        snowflake_schemas: List of Snowflake schema names
        confidence_threshold: Minimum confidence score (0.0-1.0) to auto-map

    Returns:
        Dict mapping SQL schema to {
            'snowflake_schema': matched schema,
            'confidence': score,
            'alternatives': list of other possible matches
        }
    """
    mappings = {}
    used_snow_schemas = set()

    for sql_schema in sql_schemas:
        # Calculate similarity scores for all Snowflake schemas
        scores = []
        for snow_schema in snowflake_schemas:
            similarity = calculate_similarity(sql_schema, snow_schema)
            scores.append((snow_schema, similarity))

        # Sort by similarity (highest first)
        scores.sort(key=lambda x: x[1], reverse=True)

        # Get best match
        best_match, best_score = scores[0] if scores else (None, 0.0)

        # Get alternative matches (top 3, excluding best match)
        alternatives = [
            {"schema": schema, "confidence": score}
            for schema, score in scores[1:4]
            if score >= 0.5  # Only include reasonable alternatives
        ]

        # Determine if we should auto-map
        auto_mapped = best_score >= confidence_threshold and best_match not in used_snow_schemas

        if auto_mapped:
            used_snow_schemas.add(best_match)

        mappings[sql_schema] = {
            "snowflake_schema": best_match if auto_mapped else None,
            "confidence": round(best_score, 3),
            "auto_mapped": auto_mapped,
            "alternatives": alternatives,
            "suggestions": generate_mapping_suggestions(sql_schema, snowflake_schemas)
        }

    return mappings


def generate_mapping_suggestions(sql_schema: str, snowflake_schemas: List[str]) -> List[str]:
    """Generate human-readable suggestions for why a mapping was chosen"""
    suggestions = []
    norm_sql = normalize_schema_name(sql_schema)

    # Check for exact matches
    for snow_schema in snowflake_schemas:
        if norm_sql == normalize_schema_name(snow_schema):
            suggestions.append(f"Exact match after normalization: '{sql_schema}' → '{snow_schema}'")
            return suggestions

    # Check for partial matches
    for snow_schema in snowflake_schemas:
        norm_snow = normalize_schema_name(snow_schema)
        if norm_sql in norm_snow:
            suggestions.append(f"'{sql_schema}' is contained in '{snow_schema}'")
        elif norm_snow in norm_sql:
            suggestions.append(f"'{snow_schema}' is contained in '{sql_schema}'")

    # Pattern-based suggestions
    if re.match(r'.*(dim|dimension).*', sql_schema, re.IGNORECASE):
        dim_schemas = [s for s in snowflake_schemas if re.match(r'.*(dim|dimension).*', s, re.IGNORECASE)]
        if dim_schemas:
            suggestions.append(f"Both contain 'dimension' pattern, suggesting: {', '.join(dim_schemas)}")

    if re.match(r'.*(fact|metric).*', sql_schema, re.IGNORECASE):
        fact_schemas = [s for s in snowflake_schemas if re.match(r'.*(fact|metric).*', s, re.IGNORECASE)]
        if fact_schemas:
            suggestions.append(f"Both contain 'fact/metric' pattern, suggesting: {', '.join(fact_schemas)}")

    if not suggestions:
        suggestions.append("No strong pattern match found - manual review recommended")

    return suggestions


async def map_schemas_with_llm(
    sql_schemas: List[str],
    snowflake_schemas: List[str]
) -> Dict[str, str]:
    """
    Use a configurable LLM provider to intelligently map schemas.
    This is an enhanced version that can handle complex naming patterns.

    Supports multiple providers via LLM_PROVIDER env var:
    - ollama (default): Local models via Ollama
    - openai: OpenAI API (requires OPENAI_API_KEY)
    - azure_openai: Azure OpenAI Service
    - anthropic: Anthropic Claude API

    Returns: Dict mapping SQL schema to Snowflake schema, or None on failure
    """
    try:
        import json
        import logging
        from backend.llm import get_llm_provider, LLMProviderError

        logger = logging.getLogger(__name__)

        # Prepare the prompt
        prompt = f"""You are a database schema mapping expert. Given these SQL Server schemas and Snowflake schemas, map each SQL Server schema to its most likely Snowflake equivalent.

SQL Server Schemas: {', '.join(sql_schemas)}
Snowflake Schemas: {', '.join(snowflake_schemas)}

Common patterns:
- 'sample_dim' or 'dim' usually maps to 'DIM' (dimension tables)
- 'sample_fact' or 'fact' usually maps to 'FACT' (fact tables)
- 'staging' usually maps to 'STAGING' or 'STG'
- Case differences should be ignored

Return ONLY a JSON object mapping SQL schemas to Snowflake schemas. Example:
{{"dim": "DIM", "fact": "FACT", "staging": "STAGING"}}

Your mapping:"""

        # Get the configured LLM provider
        provider = get_llm_provider()
        logger.info(
            f"[SCHEMA_MAPPER] Using LLM provider: {provider.provider_name} "
            f"(model: {provider.model_name})"
        )

        async with provider:
            response_text = await provider.generate(prompt)

            # Extract JSON from response
            try:
                # Try to find JSON in the response
                start = response_text.find('{')
                end = response_text.rfind('}') + 1
                if start >= 0 and end > start:
                    mappings = json.loads(response_text[start:end])
                    logger.info(f"[SCHEMA_MAPPER] LLM mapping successful: {mappings}")
                    return mappings
            except json.JSONDecodeError as e:
                logger.warning(f"[SCHEMA_MAPPER] Failed to parse LLM response as JSON: {e}")

    except LLMProviderError as e:
        import logging
        logging.getLogger(__name__).warning(
            f"[SCHEMA_MAPPER] LLM mapping failed ({e.provider}): {e}, "
            "falling back to fuzzy matching"
        )
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(
            f"[SCHEMA_MAPPER] LLM mapping failed: {e}, falling back to fuzzy matching"
        )

    # Fallback to fuzzy matching if LLM fails
    return None


# Backwards compatibility alias
async def map_schemas_with_ollama(
    sql_schemas: List[str],
    snowflake_schemas: List[str]
) -> Dict[str, str]:
    """
    Backwards-compatible alias for map_schemas_with_llm.

    Deprecated: Use map_schemas_with_llm instead.
    """
    return await map_schemas_with_llm(sql_schemas, snowflake_schemas)
