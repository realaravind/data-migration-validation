/*
==============================================================================
SQL Server Workload JSON Generator
==============================================================================

This script extracts query performance data from SQL Server Query Store
and generates a JSON file for Ombudsman Validation Studio Workload Analysis.

INSTRUCTIONS:
1. Run this script in your SQL Server database (SQL Server 2016+ with Query Store enabled)
2. Copy the entire JSON output
3. Save it as a .json file (e.g., workload_analysis.json)
4. Upload the file to the Workload Analysis page in Ombudsman Validation Studio

REQUIREMENTS:
- SQL Server 2016 or later
- Query Store must be enabled (ALTER DATABASE [YourDB] SET QUERY_STORE = ON)
- Sufficient permissions to query system views

NOTE: This generates workload data from the last 7 days. Adjust the date filter as needed.

==============================================================================
*/

SET NOCOUNT ON;

-- Configuration
DECLARE @DaysBack INT = 7;  -- Number of days to look back
DECLARE @MinExecutions INT = 10;  -- Minimum executions to include a query
DECLARE @TopQueries INT = 100;  -- Maximum number of queries to export

-- Generate JSON output
SELECT
    '[' + STRING_AGG(
        CAST((
            SELECT
                CAST(q.query_id AS VARCHAR(20)) AS query_id,
                qt.query_sql_text,
                DB_NAME() AS database_name,
                CAST(p.plan_id AS VARCHAR(20)) AS plan_id,
                CAST(p.query_plan AS NVARCHAR(MAX)) AS query_plan,
                rs.count_executions AS total_executions,
                CONVERT(VARCHAR(23), rs.last_execution_time, 126) AS last_execution_time,
                CAST(rs.avg_duration / 1000.0 AS DECIMAL(10,2)) AS avg_duration_ms,
                CAST(rs.avg_cpu_time / 1000.0 AS DECIMAL(10,2)) AS avg_cpu_time_ms,
                rs.avg_logical_io_reads AS avg_logical_io_reads,
                NULL AS parameters
            FOR JSON PATH, WITHOUT_ARRAY_WRAPPER
        ) AS NVARCHAR(MAX)),
        ',' + CHAR(13) + CHAR(10)
    ) WITHIN GROUP (ORDER BY rs.count_executions DESC) + ']' AS workload_json
FROM sys.query_store_query AS q
INNER JOIN sys.query_store_query_text AS qt
    ON q.query_text_id = qt.query_text_id
INNER JOIN sys.query_store_plan AS p
    ON q.query_id = p.query_id
INNER JOIN sys.query_store_runtime_stats AS rs
    ON p.plan_id = rs.plan_id
INNER JOIN sys.query_store_runtime_stats_interval AS rsi
    ON rs.runtime_stats_interval_id = rsi.runtime_stats_interval_id
WHERE
    -- Filter by time range
    rsi.start_time >= DATEADD(DAY, -@DaysBack, GETUTCDATE())
    -- Exclude system queries
    AND qt.query_sql_text NOT LIKE '%sys.%'
    AND qt.query_sql_text NOT LIKE '%INFORMATION_SCHEMA%'
    -- Minimum execution threshold
    AND rs.count_executions >= @MinExecutions
    -- Only SELECT statements (adjust as needed)
    AND qt.query_sql_text LIKE 'SELECT%'
GROUP BY
    q.query_id,
    qt.query_sql_text,
    p.plan_id,
    p.query_plan,
    rs.count_executions,
    rs.last_execution_time,
    rs.avg_duration,
    rs.avg_cpu_time,
    rs.avg_logical_io_reads
ORDER BY
    rs.count_executions DESC
OFFSET 0 ROWS
FETCH NEXT @TopQueries ROWS ONLY
OPTION (MAXRECURSION 0);

/*
==============================================================================
SAMPLE OUTPUT FORMAT:
==============================================================================

[
  {
    "query_id": "42",
    "query_sql_text": "SELECT CustomerID, OrderDate FROM Sales.Orders WHERE OrderDate > @date",
    "database_name": "AdventureWorks",
    "plan_id": "123",
    "query_plan": "<ShowPlanXML>...</ShowPlanXML>",
    "total_executions": 15000,
    "last_execution_time": "2024-12-01T10:30:00",
    "avg_duration_ms": 45.20,
    "avg_cpu_time_ms": 22.10,
    "avg_logical_io_reads": 320,
    "parameters": null
  },
  ...
]

==============================================================================
TROUBLESHOOTING:
==============================================================================

1. "Query Store is not enabled"
   Solution: Run this command:
   ALTER DATABASE [YourDatabaseName] SET QUERY_STORE = ON;

2. "No data returned"
   Solutions:
   - Increase @DaysBack value
   - Decrease @MinExecutions threshold
   - Check if Query Store has collected data: SELECT * FROM sys.query_store_query

3. "Insufficient permissions"
   Solution: User needs db_datareader permission or higher

4. "String or binary data would be truncated"
   Solution: Some query plans are very large. Reduce @TopQueries or add WHERE clause
   to filter specific databases/schemas

==============================================================================
ADDITIONAL QUERY STORE CONFIGURATION (if needed):
==============================================================================

-- Check Query Store status
SELECT
    actual_state_desc,
    readonly_reason,
    desired_state_desc,
    current_storage_size_mb,
    max_storage_size_mb
FROM sys.database_query_store_options;

-- Enable Query Store with recommended settings
ALTER DATABASE [YourDatabaseName] SET QUERY_STORE = ON (
    OPERATION_MODE = READ_WRITE,
    CLEANUP_POLICY = (STALE_QUERY_THRESHOLD_DAYS = 30),
    DATA_FLUSH_INTERVAL_SECONDS = 900,
    INTERVAL_LENGTH_MINUTES = 60,
    MAX_STORAGE_SIZE_MB = 1000,
    QUERY_CAPTURE_MODE = AUTO,
    SIZE_BASED_CLEANUP_MODE = AUTO
);

==============================================================================
*/
