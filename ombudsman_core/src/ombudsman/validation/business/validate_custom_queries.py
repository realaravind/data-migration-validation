# src/ombudsman/validation/business/validate_custom_queries.py
'''
Validates custom business queries with complex joins, dimensions, and analytical logic.
Supports:
- Multi-table joins (fact + dimension tables)
- Date-based filtering and grouping
- Dimension filtering (customers, products, etc.)
- Top N queries
- Random sampling
- Complex aggregations
'''

from datetime import datetime, date
import random

def validate_custom_queries(sql_conn, snow_conn, query_definitions, mapping):
    """
    Execute and validate custom business queries.

    Args:
        sql_conn: SQL Server connection
        snow_conn: Snowflake connection
        query_definitions: List of query definitions with sql_query and snow_query
        mapping: Table mapping dictionary

    Query definition format:
    {
        "name": "Query description",
        "sql_query": "SELECT ...",
        "snow_query": "SELECT ...",
        "comparison_type": "aggregation|rowset|count",
        "tolerance": 0.01,  # For numeric comparisons
        "order_by": ["col1", "col2"],  # For rowset comparisons
        "limit": 100  # Optional limit for rowset comparisons
    }
    """
    issues = []
    details = []
    explain_data = {}  # ALWAYS generate explain data

    for query_def in query_definitions:
        name = query_def.get("name", "Unnamed Query")
        sql_query = query_def.get("sql_query")
        snow_query = query_def.get("snow_query")
        comparison_type = query_def.get("comparison_type", "aggregation")
        tolerance = query_def.get("tolerance", 0.01)
        order_by = query_def.get("order_by", [])
        limit = query_def.get("limit", 100)

        if not sql_query or not snow_query:
            continue

        try:
            # Execute queries
            sql_start = datetime.now()
            sql_results = sql_conn.fetch_dicts(sql_query)
            sql_duration = (datetime.now() - sql_start).total_seconds()

            snow_start = datetime.now()
            snow_results = snow_conn.fetch_dicts(snow_query)
            snow_duration = (datetime.now() - snow_start).total_seconds()

            # Compare based on type
            match = False
            difference_details = {}

            if comparison_type == "count":
                # Single count comparison
                sql_count = len(sql_results) if isinstance(sql_results, list) else (sql_results[0].get('count', 0) if sql_results else 0)
                snow_count = len(snow_results) if isinstance(snow_results, list) else (snow_results[0].get('count', 0) if snow_results else 0)

                # Handle case where results are dicts with count key
                if sql_results and isinstance(sql_results, list) and len(sql_results) > 0:
                    if 'count' in sql_results[0] or 'COUNT' in sql_results[0]:
                        sql_count = sql_results[0].get('count') or sql_results[0].get('COUNT') or 0
                if snow_results and isinstance(snow_results, list) and len(snow_results) > 0:
                    if 'count' in snow_results[0] or 'COUNT' in snow_results[0]:
                        snow_count = snow_results[0].get('count') or snow_results[0].get('COUNT') or 0

                match = sql_count == snow_count
                difference_details = {
                    "sql_count": int(sql_count),
                    "snow_count": int(snow_count),
                    "difference": abs(int(sql_count) - int(snow_count))
                }

            elif comparison_type == "aggregation":
                # Aggregation comparison (single or multiple metrics)
                if not sql_results or not snow_results:
                    match = False
                    difference_details = {"error": "One or both queries returned no results"}
                else:
                    sql_row = sql_results[0] if isinstance(sql_results, list) else sql_results
                    snow_row = snow_results[0] if isinstance(snow_results, list) else snow_results

                    # Compare each column
                    mismatches = []
                    for key in sql_row.keys():
                        sql_val = sql_row.get(key)
                        snow_val = snow_row.get(key)

                        # Convert to float if possible
                        try:
                            sql_num = float(sql_val) if sql_val is not None else 0
                            snow_num = float(snow_val) if snow_val is not None else 0

                            if abs(sql_num - snow_num) > tolerance:
                                mismatches.append({
                                    "column": key,
                                    "sql_value": round(sql_num, 2),
                                    "snow_value": round(snow_num, 2),
                                    "difference": round(abs(sql_num - snow_num), 4)
                                })
                        except (TypeError, ValueError):
                            # String comparison
                            if str(sql_val) != str(snow_val):
                                mismatches.append({
                                    "column": key,
                                    "sql_value": str(sql_val),
                                    "snow_value": str(snow_val)
                                })

                    match = len(mismatches) == 0
                    difference_details = {
                        "sql_result": {k: (round(float(v), 2) if isinstance(v, (int, float)) else str(v)) for k, v in sql_row.items()},
                        "snow_result": {k: (round(float(v), 2) if isinstance(v, (int, float)) else str(v)) for k, v in snow_row.items()},
                        "mismatches": mismatches
                    }

            elif comparison_type == "rowset":
                # Row-by-row comparison
                sql_count = len(sql_results)
                snow_count = len(snow_results)

                if sql_count != snow_count:
                    match = False
                    difference_details = {
                        "row_count_mismatch": True,
                        "sql_rows": sql_count,
                        "snow_rows": snow_count
                    }
                else:
                    # Compare rows
                    row_mismatches = []
                    for i, (sql_row, snow_row) in enumerate(zip(sql_results[:limit], snow_results[:limit])):
                        for key in sql_row.keys():
                            sql_val = sql_row.get(key)
                            snow_val = snow_row.get(key)

                            # Numeric comparison
                            try:
                                sql_num = float(sql_val) if sql_val is not None else 0
                                snow_num = float(snow_val) if snow_val is not None else 0

                                if abs(sql_num - snow_num) > tolerance:
                                    row_mismatches.append({
                                        "row_index": i,
                                        "column": key,
                                        "sql_value": round(sql_num, 2),
                                        "snow_value": round(snow_num, 2)
                                    })
                            except (TypeError, ValueError):
                                # String/date comparison
                                if str(sql_val) != str(snow_val):
                                    row_mismatches.append({
                                        "row_index": i,
                                        "column": key,
                                        "sql_value": str(sql_val),
                                        "snow_value": str(snow_val)
                                    })

                    match = len(row_mismatches) == 0
                    difference_details = {
                        "total_rows": sql_count,
                        "rows_compared": min(sql_count, limit),
                        "row_mismatches": row_mismatches[:20]  # Limit to first 20 mismatches
                    }

            # Add to details
            detail_entry = {
                "query_name": name,
                "comparison_type": comparison_type,
                "match": match,
                "sql_execution_time": round(sql_duration, 3),
                "snow_execution_time": round(snow_duration, 3),
                **difference_details
            }
            details.append(detail_entry)

            # Add to issues if mismatch
            if not match:
                issues.append(detail_entry)

            # ALWAYS collect explain data
            if match:
                interpretation = f"Query '{name}' results match between SQL Server and Snowflake. Type: {comparison_type}, Execution time: SQL={round(sql_duration, 2)}s, Snowflake={round(snow_duration, 2)}s"
            else:
                interpretation = f"Query '{name}' results MISMATCH between SQL Server and Snowflake. Type: {comparison_type}, {len(difference_details.get('mismatches', []))} differences found"

            explain_data[name] = {
                "query_name": name,
                "comparison_type": comparison_type,
                "sql_query": sql_query,
                "snow_query": snow_query,
                "sql_execution_time": round(sql_duration, 3),
                "snow_execution_time": round(snow_duration, 3),
                "sql_row_count": len(sql_results) if isinstance(sql_results, list) else 1,
                "snow_row_count": len(snow_results) if isinstance(snow_results, list) else 1,
                "sql_sample_results": sql_results[:10] if isinstance(sql_results, list) else [sql_results],
                "snow_sample_results": snow_results[:10] if isinstance(snow_results, list) else [snow_results],
                "match": match,
                "difference_details": difference_details,
                "interpretation": interpretation
            }

        except Exception as e:
            # Add error to issues and explain
            error_entry = {
                "query_name": name,
                "error": str(e),
                "sql_query": sql_query,
                "snow_query": snow_query
            }
            issues.append(error_entry)

            explain_data[name] = {
                "query_name": name,
                "error": str(e),
                "interpretation": f"Query '{name}' failed to execute: {str(e)}",
                "sql_query": sql_query,
                "snow_query": snow_query
            }

    return {
        "status": "FAIL" if issues else "PASS",
        "severity": "HIGH" if issues else "NONE",
        "issues": issues,
        "details": details,
        "explain": explain_data  # Always include explain data
    }
