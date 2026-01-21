# src/ombudsman/validation/facts/validate_late_arriving_facts.py
from ombudsman.validation.sql_utils import escape_sql_server_identifier, escape_snowflake_identifier

def validate_late_arriving_facts(sql_conn, snow_conn, fact, dim, mapping, metadata, **kwargs):
    """Validate late-arriving facts (facts with transaction dates before dimension effective dates)

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

    if "effective_date" not in metadata[dim]:
        return {
            "status": "SKIPPED",
            "severity": "NONE",
            "message": f"No effective_date defined for dimension '{dim}'. This validator requires SCD2 dimensions with effective dates"
        }

    sql_fact = escape_sql_server_identifier(mapping[fact]["sql"])
    snow_fact = escape_snowflake_identifier(mapping[fact]["snow"])
    sql_dim = escape_sql_server_identifier(mapping[dim]["sql"])
    snow_dim = escape_snowflake_identifier(mapping[dim]["snow"])

    fk = metadata[fact]["foreign_keys"][dim]["column"]
    bk = metadata[dim]["business_key"]
    eff = metadata[dim]["effective_date"]

    # Escape column names to handle reserved keywords
    sql_q = f"""
        SELECT f.[{fk}], d.[{eff}]
        FROM {sql_fact} f
        LEFT JOIN {sql_dim} d
        ON f.[{fk}] = d.[{bk}]
        WHERE f.[transaction_date] < d.[{eff}]
    """

    snow_q = f"""
        SELECT f.{fk}, d.{eff}
        FROM {snow_fact} f
        LEFT JOIN {snow_dim} d
        ON f.{fk} = d.{bk}
        WHERE f.transaction_date < d.{eff}
    """

    sql_issues = sql_conn.fetch_many(sql_q)
    snow_issues = snow_conn.fetch_many(snow_q)

    status = "FAIL" if sql_issues or snow_issues else "PASS"

    # Build detailed output
    sql_late_count = len(sql_issues)
    snow_late_count = len(snow_issues)

    # Build comparison table
    comparison_table = []

    # Combine all late-arriving keys from both systems
    sql_issues_dict = {row[0]: str(row[1]) for row in sql_issues}
    snow_issues_dict = {row[0]: str(row[1]) for row in snow_issues}

    all_late_keys = sorted(set(list(sql_issues_dict.keys()) + list(snow_issues_dict.keys())))

    for late_key in all_late_keys[:50]:  # Limit to first 50
        sql_eff_date = sql_issues_dict.get(late_key, "N/A")
        snow_eff_date = snow_issues_dict.get(late_key, "N/A")

        has_sql_issue = late_key in sql_issues_dict
        has_snow_issue = late_key in snow_issues_dict

        issue_desc = []
        if has_sql_issue:
            issue_desc.append(f"SQL: Fact transaction before dim effective date ({sql_eff_date})")
        if has_snow_issue:
            issue_desc.append(f"Snowflake: Fact transaction before dim effective date ({snow_eff_date})")

        comparison_table.append({
            "foreign_key_value": late_key,
            "sql_dimension_effective_date": sql_eff_date,
            "snow_dimension_effective_date": snow_eff_date,
            "has_sql_late_arrival": has_sql_issue,
            "has_snow_late_arrival": has_snow_issue,
            "status": "LATE_ARRIVAL" if has_sql_issue or has_snow_issue else "OK",
            "issue": "; ".join(issue_desc) if issue_desc else "OK"
        })

    # Get sample late-arriving facts (first 5)
    sql_samples = [
        {"fk_value": row[0], "dim_effective_date": str(row[1])}
        for row in sql_issues[:5]
    ] if sql_issues else []

    snow_samples = [
        {"fk_value": row[0], "dim_effective_date": str(row[1])}
        for row in snow_issues[:5]
    ] if snow_issues else []

    # Build recommendations
    recommendations = []
    if sql_late_count > 0:
        recommendations.append(f"SQL Server: {sql_late_count} late-arriving fact records found")
        recommendations.append(f"These facts have transaction dates before their dimension's effective date")
        recommendations.append("Review ETL logic to ensure dimension records are loaded before related facts")
    if snow_late_count > 0:
        recommendations.append(f"Snowflake: {snow_late_count} late-arriving fact records found")
        recommendations.append(f"These facts have transaction dates before their dimension's effective date")
        recommendations.append("Review ETL logic to ensure dimension records are loaded before related facts")

    return {
        "status": status,
        "severity": "MEDIUM" if status == "FAIL" else "NONE",
        "comparison": comparison_table,  # Detailed comparison table for UI display
        "sql_late_facts": {
            "total_count": sql_late_count,
            "samples": sql_samples,
            "all_issues": [{"fk": row[0], "effective_date": str(row[1])} for row in sql_issues[:20]]
        },
        "snow_late_facts": {
            "total_count": snow_late_count,
            "samples": snow_samples,
            "all_issues": [{"fk": row[0], "effective_date": str(row[1])} for row in snow_issues[:20]]
        },
        "summary": {
            "fact_table": fact,
            "dim_table": dim,
            "foreign_key_column": fk,
            "effective_date_column": eff,
            "sql_late_count": sql_late_count,
            "snow_late_count": snow_late_count
        },
        "recommendations": recommendations,
        "message": f"Late-Arriving Facts: SQL {sql_late_count}, Snowflake {snow_late_count}"
    }