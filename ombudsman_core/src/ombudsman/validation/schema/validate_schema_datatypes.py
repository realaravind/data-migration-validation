# src/ombudsman/validation/schema/validate_schema_datatypes.py
import logging
from ombudsman.validation.sql_utils import escape_sql_server_identifier, escape_snowflake_identifier

logger = logging.getLogger(__name__)

# SQL Server to Snowflake type compatibility mapping
TYPE_COMPATIBILITY = {
    "varchar": ["varchar", "string", "text"],
    "nvarchar": ["varchar", "string", "text"],
    "char": ["char", "varchar", "string", "text"],
    "nchar": ["char", "varchar", "string", "text"],
    "text": ["text", "string", "varchar"],
    "ntext": ["text", "string", "varchar"],
    "int": ["int", "integer", "number"],
    "bigint": ["bigint", "number", "integer"],
    "smallint": ["smallint", "int", "number", "integer"],
    "tinyint": ["tinyint", "int", "number", "integer"],
    "decimal": ["decimal", "number", "numeric"],
    "numeric": ["numeric", "number", "decimal"],
    "float": ["float", "double", "number"],
    "real": ["real", "float", "number"],
    "money": ["number", "decimal"],
    "smallmoney": ["number", "decimal"],
    "datetime": ["datetime", "timestamp", "timestamp_ntz", "timestamp_ltz"],
    "datetime2": ["datetime", "timestamp", "timestamp_ntz", "timestamp_ltz"],
    "smalldatetime": ["datetime", "timestamp", "timestamp_ntz"],
    "date": ["date"],
    "time": ["time"],
    "bit": ["boolean", "bit", "number"],
    "uniqueidentifier": ["varchar", "string", "text"],
    "varbinary": ["binary", "varbinary"],
    "binary": ["binary", "varbinary"],
    "image": ["binary", "varbinary"],
}

def normalize_type(t):
    """Normalize type name for comparison."""
    if not t:
        return ""
    # Lowercase, remove spaces, remove size specs like (255)
    t = t.lower().replace(" ", "")
    # Remove size/precision specs: varchar(255) -> varchar
    if "(" in t:
        t = t.split("(")[0]
    return t

def types_compatible(sql_type, snow_type):
    """Check if SQL Server type is compatible with Snowflake type."""
    sql_normalized = normalize_type(sql_type)
    snow_normalized = normalize_type(snow_type)

    # Exact match
    if sql_normalized == snow_normalized:
        return True

    # Check compatibility mapping
    compatible_types = TYPE_COMPATIBILITY.get(sql_normalized, [])
    if snow_normalized in compatible_types:
        return True

    # Check if both are numeric
    numeric_types = {"int", "integer", "bigint", "smallint", "tinyint", "decimal", "numeric", "float", "real", "double", "number", "money", "smallmoney"}
    if sql_normalized in numeric_types and snow_normalized in numeric_types:
        return True

    # Check if both are string
    string_types = {"varchar", "nvarchar", "char", "nchar", "text", "ntext", "string"}
    if sql_normalized in string_types and snow_normalized in string_types:
        return True

    # Check if both are datetime
    datetime_types = {"datetime", "datetime2", "smalldatetime", "date", "time", "timestamp", "timestamp_ntz", "timestamp_ltz", "timestamp_tz"}
    if sql_normalized in datetime_types and snow_normalized in datetime_types:
        return True

    return False

def validate_schema_datatypes(sql_conn=None, snow_conn=None, mapping=None, metadata=None, table=None, **kwargs):
    """
    Validate that data types match between SQL Server and Snowflake tables.
    Queries both databases and compares column data types.
    """
    # Need connections, mapping, and table
    if not sql_conn or not snow_conn or not mapping or not table:
        return {
            "status": "SKIPPED",
            "severity": "NONE",
            "message": "Missing required parameters: sql_conn, snow_conn, mapping, or table"
        }

    try:
        # Get table names from mapping
        sql_table = escape_sql_server_identifier(mapping[table]["sql"])
        snow_table = escape_snowflake_identifier(mapping[table]["snow"])

        # Query SQL Server column types
        sql_query = f"""
            SELECT COLUMN_NAME, DATA_TYPE
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = PARSENAME('{sql_table}', 2)
            AND TABLE_NAME = PARSENAME('{sql_table}', 1)
            ORDER BY ORDINAL_POSITION
        """
        sql_results = sql_conn.fetch_many(sql_query)
        # Uppercase column names for case-insensitive comparison
        sql_types = {row[0].upper(): normalize_type(row[1]) for row in sql_results}

        # Query Snowflake column types
        # Get database name from connection
        snow_db = snow_conn.database

        # Parse snow_table - handle "DATABASE.SCHEMA.TABLE", "SCHEMA.TABLE", and "TABLE" formats
        parts = snow_table.split('.')
        if len(parts) == 3:
            # DATABASE.SCHEMA.TABLE - use the database from the identifier
            snow_db = parts[0]
            snow_schema = parts[1]
            snow_table_name = parts[2]
        elif len(parts) == 2:
            # SCHEMA.TABLE
            snow_schema = parts[0]
            snow_table_name = parts[1]
        else:
            # Just TABLE - default to PUBLIC schema
            snow_schema = 'PUBLIC'
            snow_table_name = snow_table

        # Snowflake stores unquoted identifiers as uppercase in INFORMATION_SCHEMA
        # Uppercase the values for the WHERE clause to match
        snow_schema_upper = snow_schema.upper()
        snow_table_name_upper = snow_table_name.upper()

        snow_query = f"""
            SELECT COLUMN_NAME, DATA_TYPE
            FROM {snow_db}.INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = '{snow_schema_upper}'
            AND TABLE_NAME = '{snow_table_name_upper}'
            ORDER BY ORDINAL_POSITION
        """
        logger.info(f"[SNOW_TYPE] Table: {snow_table} -> db={snow_db}, schema={snow_schema_upper}, table={snow_table_name_upper}")
        snow_results = snow_conn.fetch_many(snow_query)
        # Uppercase column names for case-insensitive comparison
        snow_types = {row[0].upper(): normalize_type(row[1]) for row in snow_results}
        logger.info(f"[SNOW_TYPE] Returned {len(snow_results)} columns: {dict(list(snow_types.items())[:5])}{'...' if len(snow_types) > 5 else ''}")

        # Compare types for each column using type compatibility
        mismatches = []
        matched = []
        for col_name in sql_types.keys():
            sql_type = sql_types[col_name]
            if col_name not in snow_types:
                mismatches.append({
                    "column": col_name,
                    "sql_type": sql_type,
                    "snow_type": None,
                    "match": False,
                    "compatible": False,
                    "severity": "HIGH"
                })
            else:
                snow_type = snow_types[col_name]
                is_compatible = types_compatible(sql_type, snow_type)
                if is_compatible:
                    matched.append({
                        "column": col_name,
                        "sql_type": sql_type,
                        "snow_type": snow_type,
                        "match": sql_type == snow_type,
                        "compatible": True,
                        "severity": "NONE"
                    })
                else:
                    mismatches.append({
                        "column": col_name,
                        "sql_type": sql_type,
                        "snow_type": snow_type,
                        "match": False,
                        "compatible": False,
                        "severity": "MEDIUM"
                    })

        return {
            "status": "FAIL" if mismatches else "PASS",
            "severity": "HIGH" if any(m["severity"] == "HIGH" for m in mismatches) else ("MEDIUM" if mismatches else "NONE"),
            "sql_types": sql_types,
            "snow_types": snow_types,
            "matched": matched,
            "mismatches": mismatches,
            "matched_count": len(matched),
            "mismatch_count": len(mismatches)
        }
    except Exception as e:
        return {
            "status": "ERROR",
            "severity": "HIGH",
            "message": f"Failed to validate schema datatypes: {str(e)}"
        }

    # Fallback for legacy signature
    sql_columns = kwargs.get('sql_columns', {})
    snow_columns = kwargs.get('snow_columns', {})

    if not sql_columns and not snow_columns:
        return {
            "status": "SKIPPED",
            "severity": "NONE",
            "message": "No column metadata provided"
        }

    results = {}

    for table in sql_columns.keys():
        table_res = []
        for col in sql_columns[table]:
            col_name = col["name"]
            sql_type = normalize_type(col["type"])
            snow_col = next((c for c in snow_columns.get(table, []) if c["name"].upper() == col_name.upper()), None)

            if not snow_col:
                table_res.append({
                    "column": col_name,
                    "sql_type": sql_type,
                    "snow_type": None,
                    "match": False,
                    "compatible": False,
                    "severity": "HIGH"
                })
                continue

            snow_type = normalize_type(snow_col["type"])
            is_compatible = types_compatible(sql_type, snow_type)

            table_res.append({
                "column": col_name,
                "sql_type": sql_type,
                "snow_type": snow_type,
                "match": sql_type == snow_type,
                "compatible": is_compatible,
                "severity": "NONE" if is_compatible else "MEDIUM"
            })

        results[table] = table_res

    return {
        "status": "PASS" if all(all(r["compatible"] for r in res) for res in results.values()) else "FAIL",
        "severity": "HIGH" if any(any(r["severity"] == "HIGH" for r in res) for res in results.values()) else "NONE",
        "results": results
    }