"""
Custom SQL Validator for Comparative Validations.

Executes arbitrary SQL queries on both SQL Server and Snowflake,
then compares the results.
"""
from typing import Dict, Any
import pandas as pd


def _generate_comparison_details(sql_df: pd.DataFrame, snow_df: pd.DataFrame, max_rows: int = 100) -> Dict[str, Any]:
    """
    Generate comparison details for UI rendering.

    Returns structured data with side-by-side comparison of all rows (up to max_rows).
    """
    comparison_rows = []

    # Limit the number of rows to include in comparison details
    num_rows = min(len(sql_df), len(snow_df), max_rows)

    for idx in range(num_rows):
        if idx < len(sql_df) and idx < len(snow_df):
            sql_row = sql_df.iloc[idx]
            snow_row = snow_df.iloc[idx]

            row_data = {
                'row_index': int(idx),
                'sql_values': {},
                'snowflake_values': {},
                'differing_columns': []
            }

            for col in sql_df.columns:
                if col in snow_df.columns:
                    sql_val = sql_row[col]
                    snow_val = snow_row[col]

                    sql_val_str = str(sql_val) if sql_val is not None else None
                    snow_val_str = str(snow_val) if snow_val is not None else None

                    row_data['sql_values'][col] = sql_val_str
                    row_data['snowflake_values'][col] = snow_val_str

                    if sql_val_str != snow_val_str:
                        row_data['differing_columns'].append(col)

            comparison_rows.append(row_data)

    return {
        'columns': list(sql_df.columns),
        'rows': comparison_rows
    }


def _generate_shape_mismatch_comparison(sql_df: pd.DataFrame, snow_df: pd.DataFrame, max_rows: int = 100) -> Dict[str, Any]:
    """
    Generate comparison details for shape mismatch cases.

    Shows all rows from both datasets side-by-side, marking rows that only exist in one system.
    """
    comparison_rows = []

    # Get all columns from both dataframes
    all_columns = list(set(list(sql_df.columns) + list(snow_df.columns)))

    # Process rows from both dataframes
    max_length = max(len(sql_df), len(snow_df))
    num_rows = min(max_length, max_rows)

    for idx in range(num_rows):
        row_data = {
            'row_index': int(idx),
            'sql_values': {},
            'snowflake_values': {},
            'differing_columns': [],
            'only_in': None  # Will be 'sql', 'snowflake', or None
        }

        # Get SQL Server row if it exists
        if idx < len(sql_df):
            sql_row = sql_df.iloc[idx]
            for col in all_columns:
                if col in sql_df.columns:
                    sql_val = sql_row[col]
                    row_data['sql_values'][col] = str(sql_val) if sql_val is not None else None
                else:
                    row_data['sql_values'][col] = None
        else:
            # This row only exists in Snowflake
            row_data['only_in'] = 'snowflake'
            for col in all_columns:
                row_data['sql_values'][col] = None

        # Get Snowflake row if it exists
        if idx < len(snow_df):
            snow_row = snow_df.iloc[idx]
            for col in all_columns:
                if col in snow_df.columns:
                    snow_val = snow_row[col]
                    row_data['snowflake_values'][col] = str(snow_val) if snow_val is not None else None
                else:
                    row_data['snowflake_values'][col] = None
        else:
            # This row only exists in SQL Server
            row_data['only_in'] = 'sql'
            for col in all_columns:
                row_data['snowflake_values'][col] = None

        # Mark which columns differ (if row exists in both)
        if row_data['only_in'] is None:
            for col in all_columns:
                if row_data['sql_values'].get(col) != row_data['snowflake_values'].get(col):
                    row_data['differing_columns'].append(col)
        else:
            # All columns differ if row only exists in one system
            row_data['differing_columns'] = all_columns

        comparison_rows.append(row_data)

    return {
        'columns': all_columns,
        'rows': comparison_rows,
        'shape_mismatch': True,
        'sql_row_count': len(sql_df),
        'snowflake_row_count': len(snow_df),
        'rows_only_in_sql': max(0, len(sql_df) - len(snow_df)),
        'rows_only_in_snowflake': max(0, len(snow_df) - len(sql_df))
    }


def _analyze_differences(sql_df: pd.DataFrame, snow_df: pd.DataFrame, ignore_row_order: bool) -> Dict[str, Any]:
    """
    Analyze differences between two DataFrames and provide detailed explanation.

    Returns a dict with:
    - 'message': Summary message for display
    - 'comparison_details': Structured data for UI rendering (optional)
    - 'difference_type': 'row_order' | 'data_mismatch' | 'unknown'
    """
    # Check if the data is the same when sorted (row order issue)
    is_row_order_only = False
    if not ignore_row_order:
        try:
            sql_sorted = sql_df.sort_values(by=list(sql_df.columns)).reset_index(drop=True)
            snow_sorted = snow_df.sort_values(by=list(snow_df.columns)).reset_index(drop=True)
            if sql_sorted.equals(snow_sorted):
                is_row_order_only = True
        except:
            pass

    if is_row_order_only:
        # Same data, different order
        return {
            'message': (
                f"⚠️  Row order mismatch detected ({len(sql_df)} rows)\n"
                f"The result sets contain identical data but in different order.\n"
                f"💡 Suggestion: Add ORDER BY clause to the query or set ignore_row_order=true in config"
            ),
            'difference_type': 'row_order',
            'total_rows': len(sql_df)
        }

    # Find actual data differences
    try:
        # Try to find which rows/columns differ
        comparison = sql_df.compare(snow_df)

        if not comparison.empty:
            # Use the helper function to generate full comparison details
            comparison_details = _generate_comparison_details(sql_df, snow_df)
            comparison_rows = comparison_details['rows']

            # Determine affected columns
            affected_columns = set()
            for row in comparison_rows:
                affected_columns.update(row['differing_columns'])

            # Build summary message (show first 3 rows only in message)
            sample_size = min(3, len(comparison_rows))
            diff_examples = []

            for row in comparison_rows[:sample_size]:
                example = f"Row {row['row_index']}: "
                col_diffs = []
                for col in row['differing_columns'][:2]:  # Limit to 2 columns in summary
                    sql_val = row['sql_values'][col]
                    snow_val = row['snowflake_values'][col]
                    col_diffs.append(f"{col} (SQL: {sql_val} vs Snowflake: {snow_val})")
                example += ", ".join(col_diffs)
                if len(row['differing_columns']) > 2:
                    example += f" ... +{len(row['differing_columns'])-2} more"
                diff_examples.append(example)

            message = (
                f"❌ Data mismatch found ({len(comparison_rows)} of {len(sql_df)} rows differ)\n"
                f"Affected columns: {', '.join(sorted(affected_columns)) if affected_columns else 'multiple'}\n"
                f"Sample differences:\n  " + "\n  ".join(diff_examples)
            )

            if len(comparison_rows) > sample_size:
                message += f"\n  ... and {len(comparison_rows) - sample_size} more differing rows"

            message += f"\n💡 Click 'View Comparison' to see full side-by-side comparison"

            return {
                'message': message,
                'difference_type': 'data_mismatch',
                'total_rows': len(sql_df),
                'differing_rows_count': len(comparison_rows),
                'affected_columns': sorted(list(affected_columns)),
                'comparison_details': comparison_details  # Full data for UI rendering
            }

    except Exception as e:
        # If detailed analysis fails, provide basic info
        pass

    # Fallback message
    return {
        'message': f"❌ Result sets differ ({len(sql_df)} rows, {len(sql_df.columns)} columns) - unable to determine specific differences",
        'difference_type': 'unknown',
        'total_rows': len(sql_df)
    }


def validate_custom_sql(
    sql_conn,
    snow_conn,
    sql_server_query: str = None,
    snowflake_query: str = None,
    compare_mode: str = 'result_set',
    tolerance: float = 0.0,
    ignore_column_order: bool = True,
    ignore_row_order: bool = False,
    **kwargs
) -> Dict[str, Any]:
    """
    Execute custom SQL on both systems and compare results.

    Parameters:
        sql_conn: SQL Server connection
        snow_conn: Snowflake connection
        sql_server_query (str): Query to execute on SQL Server
        snowflake_query (str): Query to execute on Snowflake
        compare_mode (str): 'result_set', 'count', or 'value'
        tolerance (float): Acceptable difference threshold (default: 0.0)
        ignore_column_order (bool): Whether to ignore column order
        ignore_row_order (bool): Whether to ignore row order

    Returns:
        Dict with keys: status, severity, message, and comparison details
    """
    sql_query = sql_server_query
    snow_query = snowflake_query
    ignore_col_order = ignore_column_order
    ignore_row_order = ignore_row_order

    # Initialize diff_details for use in return statement
    diff_details = {}

    try:
        # Execute SQL Server query
        with sql_conn.cursor() as cursor:
            cursor.execute(sql_query)
            sql_results = cursor.fetchall()
            sql_columns = [desc[0] for desc in cursor.description] if cursor.description else []

        # Convert pyodbc Row objects - extract values explicitly
        if sql_results:
            # Convert each row to a list of raw values (not tuples)
            sql_data = [[val for val in row] for row in sql_results]
            sql_df = pd.DataFrame(sql_data, columns=sql_columns)
        else:
            sql_df = pd.DataFrame(columns=sql_columns)

        # Execute Snowflake query
        snow_cursor = snow_conn.cursor()
        snow_cursor.execute(snow_query)
        snow_results = snow_cursor.fetchall()
        snow_columns = [desc[0] for desc in snow_cursor.description] if snow_cursor.description else []
        snow_cursor.close()

        # Convert Snowflake tuples - extract values explicitly
        if snow_results:
            # Convert each row to a list of raw values (not tuples)
            snow_data = [[val for val in row] for row in snow_results]
            snow_df = pd.DataFrame(snow_data, columns=snow_columns)
        else:
            snow_df = pd.DataFrame(columns=snow_columns)

        # Debug: Check what's actually in the DataFrames
        print(f"[DEBUG] SQL DataFrame shape: {sql_df.shape}, dtypes: {sql_df.dtypes.to_dict() if not sql_df.empty else 'empty'}")
        if not sql_df.empty:
            print(f"[DEBUG] SQL first cell type: {type(sql_df.iloc[0, 0])}, value: {sql_df.iloc[0, 0]}")
        print(f"[DEBUG] Snow DataFrame shape: {snow_df.shape}, dtypes: {snow_df.dtypes.to_dict() if not snow_df.empty else 'empty'}")
        if not snow_df.empty:
            print(f"[DEBUG] Snow first cell type: {type(snow_df.iloc[0, 0])}, value: {snow_df.iloc[0, 0]}")

        # Normalize column names - replace empty strings with generic names
        sql_df.columns = [f'col_{i}' if c == '' else c for i, c in enumerate(sql_df.columns)]
        snow_df.columns = [f'col_{i}' if c == '' else c for i, c in enumerate(snow_df.columns)]

        # Normalize column names if ignoring order
        if ignore_col_order:
            sql_df.columns = [c.upper() for c in sql_df.columns]
            snow_df.columns = [c.upper() for c in snow_df.columns]
            sql_df = sql_df.reindex(sorted(sql_df.columns), axis=1)
            snow_df = snow_df.reindex(sorted(snow_df.columns), axis=1)

        # Sort rows if ignoring order
        if ignore_row_order:
            if not sql_df.empty and len(sql_df.columns) > 0:
                sql_df = sql_df.sort_values(by=list(sql_df.columns)).reset_index(drop=True)
            if not snow_df.empty and len(snow_df.columns) > 0:
                snow_df = snow_df.sort_values(by=list(snow_df.columns)).reset_index(drop=True)

        # Compare based on mode
        if compare_mode == 'count':
            sql_count = len(sql_df)
            snow_count = len(snow_df)
            passed = abs(sql_count - snow_count) <= tolerance
            message = f"SQL Server: {sql_count} rows, Snowflake: {snow_count} rows"
            if passed:
                message += " ✓ MATCH"
            else:
                message += f" ✗ MISMATCH (diff: {abs(sql_count - snow_count)})"

        elif compare_mode == 'result_set':
            # Compare entire DataFrames
            if sql_df.shape != snow_df.shape:
                passed = False
                message = f"Shape mismatch: SQL Server {sql_df.shape}, Snowflake {snow_df.shape}"

                # Generate comparison details for shape mismatch to help identify differences
                if len(sql_df) > 0 or len(snow_df) > 0:
                    comparison_details = _generate_shape_mismatch_comparison(sql_df, snow_df)
                    sql_only = max(0, len(sql_df) - len(snow_df))
                    snow_only = max(0, len(snow_df) - len(sql_df))

                    diff_details = {
                        'message': message,
                        'difference_type': 'shape_mismatch',
                        'total_rows': max(len(sql_df), len(snow_df)),
                        'differing_rows_count': max(len(sql_df), len(snow_df)),
                        'affected_columns': list(set(list(sql_df.columns) + list(snow_df.columns))),
                        'comparison_details': comparison_details,
                        'sql_row_count': len(sql_df),
                        'snowflake_row_count': len(snow_df),
                        'rows_only_in_sql': sql_only,
                        'rows_only_in_snowflake': snow_only
                    }
            else:
                # For single value comparisons (like COUNT), compare values directly
                # Do NOT generate comparison_details for single value comparisons
                if sql_df.shape == (1, 1):
                    sql_val = sql_df.iloc[0, 0]
                    snow_val = snow_df.iloc[0, 0]

                    # Extract from tuple if needed
                    if isinstance(sql_val, tuple) and len(sql_val) == 1:
                        sql_val = sql_val[0]
                    if isinstance(snow_val, tuple) and len(snow_val) == 1:
                        snow_val = snow_val[0]

                    # Convert to same type for comparison
                    try:
                        sql_numeric = float(sql_val)
                        snow_numeric = float(snow_val)
                        passed = abs(sql_numeric - snow_numeric) <= tolerance
                        if passed:
                            message = f"Result sets match ✓ (SQL: {sql_val}, Snowflake: {snow_val})"
                        else:
                            message = f"Values differ ✗ (SQL Server: {sql_val}, Snowflake: {snow_val})"
                    except (ValueError, TypeError):
                        # Non-numeric comparison
                        passed = str(sql_val) == str(snow_val)
                        if passed:
                            message = f"Result sets match ✓ ({sql_val})"
                        else:
                            message = f"Values differ ✗ (SQL Server: {sql_val}, Snowflake: {snow_val})"

                    # Note: We intentionally do NOT set diff_details here for single values
                    # This prevents the "View Comparison" button from appearing

                    # However, for COUNT queries, add the actual count values to the result
                    # Store them separately so they appear in the details section
                    if passed:
                        diff_details = {
                            'sql_value': sql_val,
                            'snowflake_value': snow_val,
                            'match': True
                        }
                    else:
                        diff_details = {
                            'sql_value': sql_val,
                            'snowflake_value': snow_val,
                            'match': False,
                            'difference': abs(float(sql_val) - float(snow_val)) if isinstance(sql_val, (int, float)) and isinstance(snow_val, (int, float)) else None
                        }
                else:
                    # Compare values for multi-row results
                    # Always generate comparison details for multi-row results
                    try:
                        comparison = sql_df.compare(snow_df)
                        if comparison.empty:
                            passed = True
                            message = f"Result sets match ✓ ({len(sql_df)} rows, {len(sql_df.columns)} columns)"

                            # Generate comparison details even for matching results
                            diff_details = {
                                'message': message,
                                'difference_type': 'match',
                                'total_rows': len(sql_df),
                                'differing_rows_count': 0,
                                'affected_columns': [],
                                'comparison_details': _generate_comparison_details(sql_df, snow_df)
                            }
                        else:
                            passed = False
                            diff_count = len(comparison)

                            # Analyze the type of difference
                            diff_details = _analyze_differences(sql_df, snow_df, ignore_row_order)
                            message = diff_details['message']

                    except Exception as e:
                        # Fallback to simple equality check
                        passed = sql_df.equals(snow_df)
                        if passed:
                            message = f"Result sets match ✓ ({len(sql_df)} rows, {len(sql_df.columns)} columns)"

                            # Generate comparison details even for matching results
                            diff_details = {
                                'message': message,
                                'difference_type': 'match',
                                'total_rows': len(sql_df),
                                'differing_rows_count': 0,
                                'affected_columns': [],
                                'comparison_details': _generate_comparison_details(sql_df, snow_df)
                            }
                        else:
                            # Try to analyze differences even on exception
                            try:
                                diff_details = _analyze_differences(sql_df, snow_df, ignore_row_order)
                                message = diff_details['message']
                            except:
                                message = f"Result sets differ ✗ ({len(sql_df)} rows, {len(sql_df.columns)} columns)"

        else:  # compare_mode == 'value'
            # For single value comparison
            sql_val = sql_df.iloc[0, 0] if not sql_df.empty else None
            snow_val = snow_df.iloc[0, 0] if not snow_df.empty else None

            if sql_val is None or snow_val is None:
                passed = sql_val == snow_val
                message = f"SQL Server: {sql_val}, Snowflake: {snow_val}"
            else:
                try:
                    diff = abs(float(sql_val) - float(snow_val))
                    passed = diff <= tolerance
                    if passed:
                        message = f"Values match ✓ (SQL: {sql_val}, Snowflake: {snow_val})"
                    else:
                        message = f"Values differ ✗ (SQL: {sql_val}, Snowflake: {snow_val}, diff: {diff})"
                except (ValueError, TypeError):
                    # Non-numeric comparison
                    passed = str(sql_val) == str(snow_val)
                    if passed:
                        message = f"Values match ✓ ({sql_val})"
                    else:
                        message = f"Values differ ✗ (SQL: {sql_val}, Snowflake: {snow_val})"

        # Build result with optional comparison details
        result = {
            "status": "PASS" if passed else "FAIL",
            "severity": "ERROR" if not passed else "INFO",
            "message": message,
            "sql_query": sql_query[:200] + '...' if len(sql_query) > 200 else sql_query,
            "snow_query": snow_query[:200] + '...' if len(snow_query) > 200 else snow_query,
            "sql_row_count": len(sql_df),
            "snow_row_count": len(snow_df),
            "compare_mode": compare_mode
        }

        # Add comparison details if available (from _analyze_differences)
        if diff_details:
            if 'difference_type' in diff_details:
                result['difference_type'] = diff_details['difference_type']
            if 'comparison_details' in diff_details:
                result['comparison_details'] = diff_details['comparison_details']
            if 'affected_columns' in diff_details:
                result['affected_columns'] = diff_details['affected_columns']
            if 'differing_rows_count' in diff_details:
                result['differing_rows_count'] = diff_details['differing_rows_count']

        return result

    except Exception as e:
        import traceback
        error_str = str(e)
        print(f"[ERROR] Exception in validate_custom_sql: {error_str}")
        print(f"[ERROR] Traceback:\n{traceback.format_exc()}")

        # Check if it's an "Invalid column name" error
        if "Invalid column name" in error_str or "42S22" in error_str:
            # Extract column name from error if possible
            import re
            col_match = re.search(r"Invalid column name '([^']+)'", error_str)
            col_name = col_match.group(1) if col_match else "unknown"

            return {
                "status": "SKIPPED",
                "severity": "WARNING",
                "message": f"Column '{col_name}' not found in database schema - query skipped",
                "sql_query": sql_query[:200] + '...' if len(sql_query) > 200 else sql_query if sql_query else "N/A",
                "snow_query": snow_query[:200] + '...' if len(snow_query) > 200 else snow_query if snow_query else "N/A",
                "error": str(e),
                "error_type": "ColumnNotFoundError"
            }

        return {
            "status": "FAIL",
            "severity": "ERROR",
            "message": f"Validation failed: {str(e)}",
            "sql_query": sql_query[:200] + '...' if len(sql_query) > 200 else sql_query if sql_query else "N/A",
            "snow_query": snow_query[:200] + '...' if len(snow_query) > 200 else snow_query if snow_query else "N/A",
            "error": str(e),
            "error_type": type(e).__name__
        }
