"""
AI-powered SQL Server to Snowflake type compatibility checker.

Uses LLM to determine if data types are compatible during migration validation.
Falls back to rule-based checking if LLM is unavailable.
"""

import asyncio
import logging
from functools import lru_cache
from typing import Optional, Dict, Tuple

logger = logging.getLogger(__name__)

# Cache for AI type compatibility results
_type_cache: Dict[Tuple[str, str], bool] = {}


def get_ai_type_checker():
    """
    Returns a type checker function that uses AI.
    The returned function is synchronous for easy integration with validators.
    """
    def check_type_compatibility(sql_type: str, snow_type: str) -> bool:
        """
        Check if SQL Server type is compatible with Snowflake type using AI.
        Results are cached to avoid repeated LLM calls for same type pairs.
        """
        cache_key = (sql_type.lower(), snow_type.lower())

        # Check cache first
        if cache_key in _type_cache:
            return _type_cache[cache_key]

        # Try AI check
        try:
            result = _check_with_ai_sync(sql_type, snow_type)
            _type_cache[cache_key] = result
            return result
        except Exception as e:
            logger.warning(f"AI type check failed for {sql_type} -> {snow_type}: {e}")
            # Don't cache failures - might work next time
            raise

    return check_type_compatibility


def _check_with_ai_sync(sql_type: str, snow_type: str) -> bool:
    """Synchronous wrapper for async AI check."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # We're in an async context, need to use run_coroutine_threadsafe
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, _check_with_ai(sql_type, snow_type))
                return future.result(timeout=10)
        else:
            return loop.run_until_complete(_check_with_ai(sql_type, snow_type))
    except RuntimeError:
        # No event loop, create one
        return asyncio.run(_check_with_ai(sql_type, snow_type))


async def _check_with_ai(sql_type: str, snow_type: str) -> bool:
    """
    Use LLM to determine type compatibility.
    """
    from backend.llm import get_llm_provider, LLMProviderError

    prompt = f"""You are a database migration expert. Determine if the SQL Server data type can be safely migrated to the Snowflake data type.

SQL Server type: {sql_type}
Snowflake type: {snow_type}

Consider:
- Data precision and scale preservation
- String length compatibility
- Numeric range compatibility
- Date/time format compatibility

Answer with ONLY "yes" or "no" (lowercase, no explanation)."""

    provider = get_llm_provider()

    async with provider:
        response = await provider.generate(prompt)
        response = response.strip().lower()

        logger.info(f"[AI_TYPE_CHECK] {sql_type} -> {snow_type}: {response}")

        return response.startswith("yes")


async def batch_check_types(type_pairs: list) -> Dict[Tuple[str, str], bool]:
    """
    Check multiple type pairs in a single LLM call for efficiency.

    Args:
        type_pairs: List of (sql_type, snow_type) tuples

    Returns:
        Dict mapping each pair to its compatibility result
    """
    from backend.llm import get_llm_provider, LLMProviderError

    # Check cache first, collect uncached pairs
    results = {}
    uncached = []

    for sql_type, snow_type in type_pairs:
        cache_key = (sql_type.lower(), snow_type.lower())
        if cache_key in _type_cache:
            results[cache_key] = _type_cache[cache_key]
        else:
            uncached.append((sql_type, snow_type))

    if not uncached:
        return results

    # Build prompt for batch check
    pairs_text = "\n".join([f"- {sql} -> {snow}" for sql, snow in uncached])

    prompt = f"""You are a database migration expert. For each SQL Server to Snowflake type mapping below, determine if the migration is compatible (data won't be lost or corrupted).

Type mappings to check:
{pairs_text}

For each mapping, respond with the format:
sql_type -> snow_type: yes/no

Only respond with the mappings and yes/no, no explanations."""

    try:
        provider = get_llm_provider()

        async with provider:
            response = await provider.generate(prompt)

            # Parse response
            for line in response.strip().split("\n"):
                line = line.strip()
                if "->" in line and ":" in line:
                    try:
                        mapping_part, result = line.rsplit(":", 1)
                        sql_part, snow_part = mapping_part.split("->")
                        sql_type = sql_part.strip().lower()
                        snow_type = snow_part.strip().lower()
                        is_compatible = result.strip().lower().startswith("yes")

                        cache_key = (sql_type, snow_type)
                        results[cache_key] = is_compatible
                        _type_cache[cache_key] = is_compatible

                        logger.info(f"[AI_TYPE_CHECK] {sql_type} -> {snow_type}: {is_compatible}")
                    except Exception as e:
                        logger.warning(f"Failed to parse AI response line: {line}, error: {e}")

    except Exception as e:
        logger.warning(f"Batch AI type check failed: {e}")
        raise

    return results


def clear_type_cache():
    """Clear the type compatibility cache."""
    global _type_cache
    _type_cache = {}
    logger.info("[AI_TYPE_CHECK] Cache cleared")
