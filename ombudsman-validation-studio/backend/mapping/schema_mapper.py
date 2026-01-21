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


async def map_schemas_with_ollama(
    sql_schemas: List[str],
    snowflake_schemas: List[str]
) -> Dict[str, str]:
    """
    Use Ollama AI to intelligently map schemas.
    This is an enhanced version that can handle complex naming patterns.

    Returns: Dict mapping SQL schema to Snowflake schema
    """
    try:
        import aiohttp
        import json
        import os

        # Get Ollama base URL from environment (supports both Docker and native Linux)
        ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
        ollama_model = os.getenv("OLLAMA_MODEL", "llama2")

        # Prepare the prompt for Ollama
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

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{ollama_base_url}/api/generate",
                json={
                    "model": ollama_model,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    response_text = result.get("response", "")

                    # Extract JSON from response
                    import json
                    try:
                        # Try to find JSON in the response
                        start = response_text.find('{')
                        end = response_text.rfind('}') + 1
                        if start >= 0 and end > start:
                            mappings = json.loads(response_text[start:end])
                            return mappings
                    except:
                        pass
    except Exception as e:
        print(f"[SCHEMA_MAPPER] Ollama mapping failed: {e}, falling back to fuzzy matching")

    # Fallback to fuzzy matching if Ollama fails
    return None
