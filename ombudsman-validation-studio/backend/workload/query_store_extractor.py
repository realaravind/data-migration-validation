"""
SQL Server Query Store Extractor
Captures actual queries from SQL Server Query Store for validation
"""

import pyodbc
from typing import List, Dict, Optional
import os


class QueryStoreExtractor:
    """Extract queries from SQL Server Query Store"""

    def __init__(self):
        self.connection_string = None

    def connect(self, server: str = None, database: str = None, user: str = None, password: str = None):
        """Create connection string for SQL Server"""

        # Use environment variables if not provided
        server = server or os.getenv('MSSQL_HOST', 'localhost')
        port = os.getenv('MSSQL_PORT', '1433')
        database = database or os.getenv('MSSQL_DATABASE', 'master')
        user = user or os.getenv('MSSQL_USER', 'sa')
        password = password or os.getenv('MSSQL_PASSWORD', '')

        self.connection_string = (
            f"DRIVER={{ODBC Driver 18 for SQL Server}};"
            f"SERVER={server},{port};"
            f"DATABASE={database};"
            f"UID={user};"
            f"PWD={password};"
            f"TrustServerCertificate=yes;"
        )

    def extract_queries(
        self,
        top_n: int = 100,
        min_executions: int = 10,
        schemas: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Extract top queries from Query Store

        Args:
            top_n: Number of top queries to extract
            min_executions: Minimum execution count
            schemas: Filter by schemas (e.g., ['dim', 'fact'])

        Returns:
            List of query records
        """

        if not self.connection_string:
            raise ValueError("Not connected. Call connect() first.")

        conn = pyodbc.connect(self.connection_string)
        cursor = conn.cursor()

        # Build schema filter
        schema_filter = ""
        if schemas:
            schema_list = "', '".join(schemas)
            schema_filter = f"AND OBJECT_SCHEMA_NAME(q.object_id) IN ('{schema_list}')"

        # Query Store query to get top executed queries
        query = f"""
        SELECT TOP {top_n}
            q.query_id,
            qt.query_sql_text AS raw_text,
            rs.count_executions AS execution_count,
            rs.avg_duration / 1000.0 AS avg_duration_ms,
            rs.last_execution_time,
            ISNULL(OBJECT_SCHEMA_NAME(q.object_id), 'dbo') AS schema_name,
            ISNULL(OBJECT_NAME(q.object_id), 'ad_hoc') AS object_name
        FROM sys.query_store_query q
        INNER JOIN sys.query_store_query_text qt ON q.query_text_id = qt.query_text_id
        INNER JOIN sys.query_store_plan p ON q.query_id = p.query_id
        INNER JOIN sys.query_store_runtime_stats rs ON p.plan_id = rs.plan_id
        WHERE rs.count_executions >= {min_executions}
            {schema_filter}
        ORDER BY rs.count_executions DESC
        """

        cursor.execute(query)
        columns = [column[0] for column in cursor.description]

        results = []
        for row in cursor.fetchall():
            record = dict(zip(columns, row))

            # Format for workload engine
            formatted = {
                "query_id": record['query_id'],
                "raw_text": record['raw_text'].strip(),
                "stats": {
                    "total_executions": record['execution_count'],
                    "avg_duration": record['avg_duration_ms'],
                    "last_execution_time": record['last_execution_time'].isoformat() if record['last_execution_time'] else None
                },
                "metadata": {
                    "schema_name": record['schema_name'],
                    "object_name": record['object_name']
                }
            }
            results.append(formatted)

        cursor.close()
        conn.close()

        return results

    def test_connection(self) -> Dict:
        """Test the Query Store connection"""

        if not self.connection_string:
            raise ValueError("Not connected. Call connect() first.")

        try:
            conn = pyodbc.connect(self.connection_string)
            cursor = conn.cursor()

            # Check if Query Store is enabled
            cursor.execute("""
                SELECT
                    DB_NAME() as database_name,
                    actual_state_desc as query_store_status,
                    readonly_reason,
                    current_storage_size_mb,
                    max_storage_size_mb
                FROM sys.database_query_store_options
            """)

            row = cursor.fetchone()
            if row:
                result = {
                    "connected": True,
                    "database": row[0],
                    "query_store_enabled": row[1] == 'READ_WRITE',
                    "status": row[1],
                    "readonly_reason": row[2],
                    "storage_used_mb": row[3],
                    "storage_max_mb": row[4]
                }
            else:
                result = {
                    "connected": True,
                    "database": "Unknown",
                    "query_store_enabled": False,
                    "status": "Not configured"
                }

            cursor.close()
            conn.close()

            return result

        except Exception as e:
            return {
                "connected": False,
                "error": str(e)
            }
