# src/ombudsman/validation/facts/validate_fact_dim_conformance.py
from ombudsman.validation.sql_utils import escape_sql_server_identifier, escape_snowflake_identifier
from collections import Counter


def _get_orphan_issue_description(sql_count, snow_count, exists_in_sql_dim, exists_in_snow_dim):
    """Generate a human-readable description of the orphan issue"""
    issues = []

    if sql_count > 0 and not exists_in_sql_dim:
        issues.append(f"SQL: {sql_count} fact records reference non-existent dimension key")
    if snow_count > 0 and not exists_in_snow_dim:
        issues.append(f"Snowflake: {snow_count} fact records reference non-existent dimension key")

    if not issues:
        return "OK"

    return "; ".join(issues)


def validate_fact_dim_conformance(sql_conn, snow_conn, fact, dim, mapping, metadata, **kwargs):
    """Validate fact-dimension conformance (no orphaned foreign keys)

    Extra kwargs like 'table' are accepted but ignored for compatibility with pipeline executor.
    """
    # Check if required metadata exists
    if fact not in metadata:
        return {
            "status": "SKIPPED",
            "severity": "NONE",
            "message": f"Fact table '{fact}' not found in metadata"
        }

    if "foreign_keys" not in metadata[fact]:
        return {
            "status": "SKIPPED",
            "severity": "NONE",
            "message": f"No foreign_keys defined for fact table '{fact}'. Please configure relationships in relationships.yaml"
        }

    if dim not in metadata[fact]["foreign_keys"]:
        return {
            "status": "SKIPPED",
            "severity": "NONE",
            "message": f"No foreign key relationship defined between '{fact}' and '{dim}'"
        }

    if dim not in metadata:
        return {
            "status": "SKIPPED",
            "severity": "NONE",
            "message": f"Dimension table '{dim}' not found in metadata"
        }

    if "business_key" not in metadata[dim]:
        return {
            "status": "SKIPPED",
            "severity": "NONE",
            "message": f"No business_key defined for dimension '{dim}'. Please configure in metadata"
        }

    fk = metadata[fact]["foreign_keys"][dim]["column"]
    dim_bk = metadata[dim]["business_key"]

    fact_sql = escape_sql_server_identifier(mapping[fact]["sql"])
    fact_snow = mapping[fact]["snow"]
    dim_sql = escape_sql_server_identifier(mapping[dim]["sql"])
    dim_snow = escape_snowflake_identifier(mapping[dim]["snow"])

    # Get all foreign keys from fact tables
    sql_fkeys_all = [r[0] for r in sql_conn.fetch_many(f"SELECT [{fk}] FROM {fact_sql}")]
    snow_fkeys_all = [r[0] for r in snow_conn.fetch_many(f"SELECT {fk} FROM {fact_snow}")]

    # Get unique foreign keys
    sql_fkeys = set(sql_fkeys_all)
    snow_fkeys = set(snow_fkeys_all)

    # Get dimension keys
    sql_dim_keys = {r[0] for r in sql_conn.fetch_many(f"SELECT [{dim_bk}] FROM {dim_sql}")}
    snow_dim_keys = {r[0] for r in snow_conn.fetch_many(f"SELECT {dim_bk} FROM {dim_snow}")}

    # Calculate orphans
    sql_orphans = list(sql_fkeys - sql_dim_keys)
    snow_orphans = list(snow_fkeys - snow_dim_keys)

    # Count occurrences of each orphaned key
    sql_orphan_counts = Counter([k for k in sql_fkeys_all if k in sql_orphans])
    snow_orphan_counts = Counter([k for k in snow_fkeys_all if k in snow_orphans])

    # Build comparison table with detailed information about each orphaned key
    comparison_table = []

    # Get all unique orphaned keys from both systems
    all_orphan_keys = sorted(set(sql_orphans + snow_orphans))

    for orphan_key in all_orphan_keys[:50]:  # Limit to first 50 for display
        sql_count = sql_orphan_counts.get(orphan_key, 0)
        snow_count = snow_orphan_counts.get(orphan_key, 0)

        # Check if key exists in dimension tables
        exists_in_sql_dim = orphan_key in sql_dim_keys
        exists_in_snow_dim = orphan_key in snow_dim_keys

        comparison_table.append({
            "foreign_key_value": orphan_key,
            "sql_fact_occurrences": sql_count,
            "snow_fact_occurrences": snow_count,
            "exists_in_sql_dimension": exists_in_sql_dim,
            "exists_in_snow_dimension": exists_in_snow_dim,
            "status": "ORPHANED" if (sql_count > 0 and not exists_in_sql_dim) or (snow_count > 0 and not exists_in_snow_dim) else "OK",
            "issue": _get_orphan_issue_description(sql_count, snow_count, exists_in_sql_dim, exists_in_snow_dim)
        })

    # Get sample rows for orphaned keys (limit to first 5 orphans)
    sql_orphan_samples = []
    if sql_orphans:
        sample_limit = min(5, len(sql_orphans))
        for orphan_key in sql_orphans[:sample_limit]:
            sql_orphan_samples.append({
                "fk_value": orphan_key,
                "occurrences": sql_orphan_counts[orphan_key]
            })

    snow_orphan_samples = []
    if snow_orphans:
        sample_limit = min(5, len(snow_orphans))
        for orphan_key in snow_orphans[:sample_limit]:
            snow_orphan_samples.append({
                "fk_value": orphan_key,
                "occurrences": snow_orphan_counts[orphan_key]
            })

    # Calculate statistics
    total_sql_facts = len(sql_fkeys_all)
    total_snow_facts = len(snow_fkeys_all)

    sql_orphan_count = sum(sql_orphan_counts.values())
    snow_orphan_count = sum(snow_orphan_counts.values())

    sql_orphan_pct = (sql_orphan_count / total_sql_facts * 100) if total_sql_facts > 0 else 0
    snow_orphan_pct = (snow_orphan_count / total_snow_facts * 100) if total_snow_facts > 0 else 0

    sql_conformance_rate = 100 - sql_orphan_pct
    snow_conformance_rate = 100 - snow_orphan_pct

    status = "FAIL" if sql_orphans or snow_orphans else "PASS"

    # Build recommendations
    recommendations = []
    if sql_orphans:
        recommendations.append(f"SQL Server: {len(sql_orphans)} unique orphaned keys found ({sql_orphan_count} total fact records affected)")
        recommendations.append(f"Verify if these {len(sql_orphans)} dimension keys should exist in {dim}")
        recommendations.append("Consider adding missing dimension records or correcting fact table foreign keys")
    if snow_orphans:
        recommendations.append(f"Snowflake: {len(snow_orphans)} unique orphaned keys found ({snow_orphan_count} total fact records affected)")
        recommendations.append(f"Verify if these {len(snow_orphans)} dimension keys should exist in {dim}")
        recommendations.append("Consider adding missing dimension records or correcting fact table foreign keys")

    result = {
        "status": status,
        "severity": "HIGH" if status == "FAIL" else "NONE",
        "comparison": comparison_table,  # Detailed comparison table for UI display
        "sql_orphans": {
            "total_affected_rows": sql_orphan_count,
            "unique_missing_keys": len(sql_orphans),
            "samples": sql_orphan_samples,
            "all_missing_keys": sql_orphans[:20]  # Limit to first 20 for display
        },
        "snow_orphans": {
            "total_affected_rows": snow_orphan_count,
            "unique_missing_keys": len(snow_orphans),
            "samples": snow_orphan_samples,
            "all_missing_keys": snow_orphans[:20]  # Limit to first 20 for display
        },
        "summary": {
            "fact_table": fact,
            "dim_table": dim,
            "foreign_key_column": fk,
            "dimension_key_column": dim_bk,
            "total_sql_facts": total_sql_facts,
            "total_snow_facts": total_snow_facts,
            "sql_conformance_rate": f"{sql_conformance_rate:.2f}%",
            "snow_conformance_rate": f"{snow_conformance_rate:.2f}%",
            "sql_orphan_percentage": f"{sql_orphan_pct:.2f}%",
            "snow_orphan_percentage": f"{snow_orphan_pct:.2f}%"
        },
        "recommendations": recommendations,
        "message": f"Fact-Dimension Conformance: SQL {sql_conformance_rate:.2f}%, Snowflake {snow_conformance_rate:.2f}%"
    }

    return result