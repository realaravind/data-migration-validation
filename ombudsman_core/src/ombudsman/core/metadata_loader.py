import yaml
import os
import re


def load_metadata():
    """Legacy function for loading metadata from YAML files."""
    tables = yaml.safe_load(open("ombudsman/config/tables.yaml"))
    columns = yaml.safe_load(open("ombudsman/config/columns.yaml"))
    relationships = yaml.safe_load(open("ombudsman/config/relationships.yaml"))
    return tables, columns, relationships


class MetadataLoader:
    """
    Extract metadata from databases (SQL Server, Snowflake, etc.)
    """

    def __init__(self, connection_string: str):
        """
        Initialize MetadataLoader with a connection string.

        Args:
            connection_string: Database connection string or connection type
                              Examples:
                              - "sqlserver" (uses env vars)
                              - "DRIVER={...};SERVER=..." (SQL Server ODBC)
                              - "snowflake" (uses env vars)
        """
        self.connection_string = connection_string
        self.conn = None
        self._connect()

    def _connect(self):
        """Establish database connection based on connection string."""
        conn_str_lower = self.connection_string.lower()

        # SQL Server connection
        if "sqlserver" in conn_str_lower or "driver=" in conn_str_lower:
            from ombudsman.core.sqlserver_conn import SQLServerConn

            if conn_str_lower == "sqlserver":
                # Use environment variables
                conn_str = os.getenv("SQLSERVER_CONN_STR")
                if not conn_str:
                    # Build from individual env vars
                    conn_str = (
                        f"DRIVER={{ODBC Driver 18 for SQL Server}};"
                        f"SERVER={os.getenv('MSSQL_HOST', 'localhost')},{os.getenv('MSSQL_PORT', '1433')};"
                        f"DATABASE={os.getenv('MSSQL_DATABASE', 'master')};"
                        f"UID={os.getenv('MSSQL_USER', 'sa')};"
                        f"PWD={os.getenv('MSSQL_PASSWORD', '')};"
                        f"TrustServerCertificate=yes;"
                    )
            else:
                conn_str = self.connection_string

            self.conn = SQLServerConn(conn_str)
            self.db_type = "sqlserver"

        # Snowflake connection
        elif "snowflake" in conn_str_lower:
            from ombudsman.core.snowflake_conn import SnowflakeConn
            self.conn = SnowflakeConn()
            self.db_type = "snowflake"

        else:
            raise ValueError(f"Unsupported connection type: {self.connection_string}")

    def get_columns(self, table_name: str) -> list:
        """
        Get column metadata for a specific table.

        Args:
            table_name: Name of the table (can be schema.table format)

        Returns:
            List of column metadata dictionaries
        """
        if self.db_type == "sqlserver":
            return self._get_sqlserver_columns(table_name)
        elif self.db_type == "snowflake":
            return self._get_snowflake_columns(table_name)
        else:
            return []

    def _get_sqlserver_columns(self, table_name: str) -> list:
        """Extract column metadata from SQL Server."""
        # Parse schema and table name
        parts = table_name.split('.')
        if len(parts) == 2:
            schema, table = parts
        else:
            schema = 'dbo'
            table = table_name

        query = f"""
        SELECT
            c.COLUMN_NAME as name,
            c.DATA_TYPE as data_type,
            c.CHARACTER_MAXIMUM_LENGTH as max_length,
            c.NUMERIC_PRECISION as precision,
            c.NUMERIC_SCALE as scale,
            c.IS_NULLABLE as is_nullable,
            c.COLUMN_DEFAULT as default_value,
            CASE
                WHEN pk.COLUMN_NAME IS NOT NULL THEN 1
                ELSE 0
            END as is_primary_key
        FROM INFORMATION_SCHEMA.COLUMNS c
        LEFT JOIN (
            SELECT ku.TABLE_CATALOG, ku.TABLE_SCHEMA, ku.TABLE_NAME, ku.COLUMN_NAME
            FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS AS tc
            JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE AS ku
                ON tc.CONSTRAINT_TYPE = 'PRIMARY KEY'
                AND tc.CONSTRAINT_NAME = ku.CONSTRAINT_NAME
        ) pk
            ON c.TABLE_CATALOG = pk.TABLE_CATALOG
            AND c.TABLE_SCHEMA = pk.TABLE_SCHEMA
            AND c.TABLE_NAME = pk.TABLE_NAME
            AND c.COLUMN_NAME = pk.COLUMN_NAME
        WHERE c.TABLE_SCHEMA = '{schema}'
        AND c.TABLE_NAME = '{table}'
        ORDER BY c.ORDINAL_POSITION
        """

        try:
            results = self.conn.fetch_dicts(query)
            return [
                {
                    "name": row["name"],
                    "data_type": row["data_type"],
                    "max_length": row["max_length"],
                    "precision": row["precision"],
                    "scale": row["scale"],
                    "nullable": row["is_nullable"] == "YES",
                    "default": row["default_value"],
                    "primary_key": bool(row["is_primary_key"])
                }
                for row in results
            ]
        except Exception as e:
            raise Exception(f"Failed to get columns for {table_name}: {str(e)}")

    def _get_snowflake_columns(self, table_name: str) -> list:
        """Extract column metadata from Snowflake."""
        # Parse database.schema.table format
        parts = table_name.split('.')
        if len(parts) == 3:
            database, schema, table = parts
        elif len(parts) == 2:
            database = os.getenv("SNOW_DATABASE", "DEMO_DB")
            schema, table = parts
        else:
            database = os.getenv("SNOW_DATABASE", "DEMO_DB")
            schema = os.getenv("SNOW_SCHEMA", "PUBLIC")
            table = table_name

        query = f"""
        SELECT
            COLUMN_NAME as name,
            DATA_TYPE as data_type,
            CHARACTER_MAXIMUM_LENGTH as max_length,
            NUMERIC_PRECISION as precision,
            NUMERIC_SCALE as scale,
            IS_NULLABLE as is_nullable,
            COLUMN_DEFAULT as default_value
        FROM {database}.INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = '{schema}'
        AND TABLE_NAME = '{table}'
        ORDER BY ORDINAL_POSITION
        """

        try:
            results = self.conn.fetch_dicts(query)
            return [
                {
                    "name": row["NAME"],
                    "data_type": row["DATA_TYPE"],
                    "max_length": row["MAX_LENGTH"],
                    "precision": row["PRECISION"],
                    "scale": row["SCALE"],
                    "nullable": row["IS_NULLABLE"] == "YES",
                    "default": row["DEFAULT_VALUE"]
                }
                for row in results
            ]
        except Exception as e:
            raise Exception(f"Failed to get columns for {table_name}: {str(e)}")

    def get_tables(self, schema: str = None) -> list:
        """
        Get list of tables in the database.

        Args:
            schema: Schema name (optional)

        Returns:
            List of table names
        """
        if self.db_type == "sqlserver":
            schema = schema or "dbo"
            query = f"""
            SELECT TABLE_NAME
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = '{schema}'
            AND TABLE_TYPE = 'BASE TABLE'
            ORDER BY TABLE_NAME
            """
        elif self.db_type == "snowflake":
            schema = schema or os.getenv("SNOW_SCHEMA", "PUBLIC")
            database = os.getenv("SNOW_DATABASE", "DEMO_DB")
            query = f"""
            SELECT TABLE_NAME
            FROM {database}.INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = '{schema}'
            AND TABLE_TYPE = 'BASE TABLE'
            ORDER BY TABLE_NAME
            """

        try:
            results = self.conn.fetch_many(query)
            return [row[0] for row in results]
        except Exception as e:
            raise Exception(f"Failed to get tables: {str(e)}")