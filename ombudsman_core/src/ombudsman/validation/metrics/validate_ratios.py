# src/ombudsman/validation/metrics/validate_ratios.py
from ombudsman.validation.sql_utils import escape_sql_server_identifier, escape_snowflake_identifier

def validate_ratios(sql_conn, snow_conn, table, ratio_defs, mapping):
    sql_table = escape_sql_server_identifier(mapping[table]["sql"])
    snow_table = escape_snowflake_identifier(mapping[table]["snow"])

    issues = []
    details = []
    explain_data = {}  # ALWAYS generate explain data

    # Handle both list and dict formats for ratio_defs
    if isinstance(ratio_defs, list):
        # Convert list format: [{"numerator": col, "denominator": col}, ...]
        # to dict format: {"ratio_name": (num, den), ...}
        ratio_dict = {}
        for idx, ratio_def in enumerate(ratio_defs):
            if isinstance(ratio_def, dict):
                num = ratio_def.get("numerator")
                den = ratio_def.get("denominator")
                name = f"{num}/{den}" if num and den else f"ratio_{idx}"
                ratio_dict[name] = (num, den)
        ratio_defs = ratio_dict

    for name, (num, den) in ratio_defs.items():
        sql_ratio = sql_conn.fetch_one(
            f"SELECT SUM({num}) / NULLIF(SUM({den}), 0) FROM {sql_table}"
        )

        snow_ratio = snow_conn.fetch_one(
            f"SELECT SUM({num}) / NULLIF(SUM({den}), 0) FROM {snow_table}"
        )

        if sql_ratio is None or snow_ratio is None:
            continue

        difference = abs(sql_ratio - snow_ratio) if sql_ratio and snow_ratio else 0
        match = difference <= 0.001

        details.append({
            "ratio": name,
            "sql_ratio": round(float(sql_ratio), 2) if sql_ratio else 0,
            "snow_ratio": round(float(snow_ratio), 2) if snow_ratio else 0,
            "difference": round(float(difference), 4),
            "match": match
        })

        if not match:
            issues.append({
                "ratio": name,
                "sql_ratio": round(float(sql_ratio), 2),
                "snow_ratio": round(float(snow_ratio), 2),
                "difference": round(float(difference), 4)
            })

        # ALWAYS collect explain data - for both passing and failing ratios
        try:
            # Get individual components (numerator and denominator)
            sql_num = sql_conn.fetch_one(f"SELECT SUM({num}) FROM {sql_table}")
            sql_den = sql_conn.fetch_one(f"SELECT SUM({den}) FROM {sql_table}")
            snow_num = sql_conn.fetch_one(f"SELECT SUM({num}) FROM {snow_table}")
            snow_den = sql_conn.fetch_one(f"SELECT SUM({den}) FROM {snow_table}")

            # Get sample rows showing numerator and denominator values
            sql_samples = sql_conn.fetch_dicts(f"SELECT TOP 20 {num}, {den} FROM {sql_table}")
            snow_samples = snow_conn.fetch_dicts(f"SELECT {num}, {den} FROM {snow_table} LIMIT 20")

            if match:
                interpretation = f"Ratio '{name}' = {num} / {den} matches. SQL: {round(float(sql_num), 2) if sql_num else 0}/{round(float(sql_den), 2) if sql_den else 0} = {round(float(sql_ratio), 2) if sql_ratio else 0}. Snow: {round(float(snow_num), 2) if snow_num else 0}/{round(float(snow_den), 2) if snow_den else 0} = {round(float(snow_ratio), 2) if snow_ratio else 0}"
            else:
                interpretation = f"Ratio '{name}' = {num} / {den} mismatch. SQL: {round(float(sql_num), 2) if sql_num else 0}/{round(float(sql_den), 2) if sql_den else 0} = {round(float(sql_ratio), 2) if sql_ratio else 0}. Snow: {round(float(snow_num), 2) if snow_num else 0}/{round(float(snow_den), 2) if snow_den else 0} = {round(float(snow_ratio), 2) if snow_ratio else 0}"

            explain_data[name] = {
                "numerator_column": num,
                "denominator_column": den,
                "sql_numerator": round(float(sql_num), 2) if sql_num else 0,
                "sql_denominator": round(float(sql_den), 2) if sql_den else 0,
                "snow_numerator": round(float(snow_num), 2) if snow_num else 0,
                "snow_denominator": round(float(snow_den), 2) if snow_den else 0,
                "sql_samples": sql_samples[:20],
                "snow_samples": snow_samples[:20],
                "interpretation": interpretation,
                "queries": {
                    "sql_ratio": f"SELECT SUM({num}) / NULLIF(SUM({den}), 0) FROM {sql_table}",
                    "snow_ratio": f"SELECT SUM({num}) / NULLIF(SUM({den}), 0) FROM {snow_table}",
                    "sql_components": f"SELECT SUM({num}) as numerator, SUM({den}) as denominator FROM {sql_table}",
                    "snow_components": f"SELECT SUM({num}) as numerator, SUM({den}) as denominator FROM {snow_table}",
                    "sql_samples": f"SELECT TOP 20 {num}, {den} FROM {sql_table}",
                    "snow_samples": f"SELECT {num}, {den} FROM {snow_table} LIMIT 20"
                }
            }
        except Exception as e:
            # If explain fails, provide basic info
            if match:
                interpretation = f"Ratio '{name}' matches: SQL={round(float(sql_ratio), 2) if sql_ratio else 0}, Snow={round(float(snow_ratio), 2) if snow_ratio else 0}"
            else:
                interpretation = f"Ratio '{name}' mismatch: SQL={round(float(sql_ratio), 2) if sql_ratio else 0}, Snow={round(float(snow_ratio), 2) if snow_ratio else 0}"

            explain_data[name] = {
                "numerator_column": num,
                "denominator_column": den,
                "sql_ratio": round(float(sql_ratio), 2) if sql_ratio else 0,
                "snow_ratio": round(float(snow_ratio), 2) if sql_ratio else 0,
                "interpretation": interpretation,
                "error": f"Could not fetch detailed breakdown: {str(e)}"
            }

    return {
        "status": "FAIL" if issues else "PASS",
        "severity": "MEDIUM" if issues else "NONE",
        "issues": issues,
        "details": details,
        "explain": explain_data  # Always include explain data
    }
