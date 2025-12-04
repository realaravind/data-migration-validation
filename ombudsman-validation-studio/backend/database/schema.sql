-- Ombudsman Validation Studio - Results Database Schema
-- Database: OmbudsmanResults
-- Purpose: Store pipeline execution results for historical tracking and analysis

-- Create database if it doesn't exist
IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = 'OmbudsmanResults')
BEGIN
    CREATE DATABASE OmbudsmanResults;
END
GO

USE OmbudsmanResults;
GO

-- ============================================================================
-- Projects Table
-- Stores validation projects/workspaces
-- ============================================================================
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'Projects')
BEGIN
    CREATE TABLE Projects (
        project_id VARCHAR(100) PRIMARY KEY,
        project_name NVARCHAR(255) NOT NULL,
        description NVARCHAR(MAX),
        created_at DATETIME2 DEFAULT GETDATE(),
        updated_at DATETIME2 DEFAULT GETDATE(),
        created_by NVARCHAR(100),
        tags NVARCHAR(MAX),  -- JSON array of tags
        is_active BIT DEFAULT 1
    );

    CREATE INDEX IX_Projects_CreatedAt ON Projects(created_at DESC);
    CREATE INDEX IX_Projects_IsActive ON Projects(is_active);
END
GO

-- ============================================================================
-- Pipeline Runs Table
-- Stores each pipeline execution
-- ============================================================================
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'PipelineRuns')
BEGIN
    CREATE TABLE PipelineRuns (
        run_id VARCHAR(100) PRIMARY KEY,
        project_id VARCHAR(100),
        pipeline_name NVARCHAR(255) NOT NULL,
        status VARCHAR(20) NOT NULL,  -- pending, running, completed, failed
        started_at DATETIME2 NOT NULL DEFAULT GETDATE(),
        completed_at DATETIME2,
        duration_seconds INT,
        pipeline_config NVARCHAR(MAX),  -- JSON of pipeline configuration
        error_message NVARCHAR(MAX),
        total_steps INT DEFAULT 0,
        successful_steps INT DEFAULT 0,
        failed_steps INT DEFAULT 0,
        warnings_count INT DEFAULT 0,
        errors_count INT DEFAULT 0,
        executed_by NVARCHAR(100),

        FOREIGN KEY (project_id) REFERENCES Projects(project_id) ON DELETE SET NULL
    );

    CREATE INDEX IX_PipelineRuns_ProjectId ON PipelineRuns(project_id);
    CREATE INDEX IX_PipelineRuns_StartedAt ON PipelineRuns(started_at DESC);
    CREATE INDEX IX_PipelineRuns_Status ON PipelineRuns(status);
    CREATE INDEX IX_PipelineRuns_PipelineName ON PipelineRuns(pipeline_name);
END
GO

-- ============================================================================
-- Validation Steps Table
-- Stores individual validation step results within a pipeline run
-- ============================================================================
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'ValidationSteps')
BEGIN
    CREATE TABLE ValidationSteps (
        step_id BIGINT IDENTITY(1,1) PRIMARY KEY,
        run_id VARCHAR(100) NOT NULL,
        step_name NVARCHAR(255) NOT NULL,
        step_order INT,
        validator_type VARCHAR(100),  -- validate_record_counts, validate_schema, custom_sql, etc.
        status VARCHAR(20) NOT NULL,  -- passed, failed, warning, skipped
        started_at DATETIME2 NOT NULL DEFAULT GETDATE(),
        completed_at DATETIME2,
        duration_milliseconds INT,

        -- Results
        result_message NVARCHAR(MAX),
        difference_type VARCHAR(50),  -- row_order, data_mismatch, shape_mismatch, etc.
        total_rows INT,
        differing_rows_count INT,
        affected_columns NVARCHAR(MAX),  -- JSON array

        -- Detailed comparison data (for UI rendering)
        comparison_details NVARCHAR(MAX),  -- JSON with full comparison data

        -- Metrics
        sql_row_count BIGINT,
        snowflake_row_count BIGINT,
        match_percentage DECIMAL(5,2),

        -- Configuration
        step_config NVARCHAR(MAX),  -- JSON of step-specific configuration

        -- Error details
        error_message NVARCHAR(MAX),
        error_stack_trace NVARCHAR(MAX),

        FOREIGN KEY (run_id) REFERENCES PipelineRuns(run_id) ON DELETE CASCADE
    );

    CREATE INDEX IX_ValidationSteps_RunId ON ValidationSteps(run_id);
    CREATE INDEX IX_ValidationSteps_StepName ON ValidationSteps(step_name);
    CREATE INDEX IX_ValidationSteps_Status ON ValidationSteps(status);
    CREATE INDEX IX_ValidationSteps_ValidatorType ON ValidationSteps(validator_type);
    CREATE INDEX IX_ValidationSteps_StartedAt ON ValidationSteps(started_at DESC);
END
GO

-- ============================================================================
-- Execution Logs Table
-- Stores detailed execution logs for debugging
-- ============================================================================
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'ExecutionLogs')
BEGIN
    CREATE TABLE ExecutionLogs (
        log_id BIGINT IDENTITY(1,1) PRIMARY KEY,
        run_id VARCHAR(100) NOT NULL,
        step_id BIGINT,
        log_level VARCHAR(20) NOT NULL,  -- DEBUG, INFO, WARNING, ERROR
        message NVARCHAR(MAX) NOT NULL,
        timestamp DATETIME2 NOT NULL DEFAULT GETDATE(),
        context NVARCHAR(MAX),  -- JSON with additional context

        FOREIGN KEY (run_id) REFERENCES PipelineRuns(run_id) ON DELETE CASCADE,
        FOREIGN KEY (step_id) REFERENCES ValidationSteps(step_id) ON DELETE CASCADE
    );

    CREATE INDEX IX_ExecutionLogs_RunId ON ExecutionLogs(run_id);
    CREATE INDEX IX_ExecutionLogs_StepId ON ExecutionLogs(step_id);
    CREATE INDEX IX_ExecutionLogs_Timestamp ON ExecutionLogs(timestamp DESC);
    CREATE INDEX IX_ExecutionLogs_LogLevel ON ExecutionLogs(log_level);
END
GO

-- ============================================================================
-- Data Quality Metrics Table
-- Stores aggregate metrics for reporting and trending
-- ============================================================================
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'DataQualityMetrics')
BEGIN
    CREATE TABLE DataQualityMetrics (
        metric_id BIGINT IDENTITY(1,1) PRIMARY KEY,
        run_id VARCHAR(100) NOT NULL,
        metric_date DATE NOT NULL DEFAULT CAST(GETDATE() AS DATE),

        -- Overall metrics
        total_tables_validated INT,
        total_rows_compared BIGINT,
        total_mismatches BIGINT,
        overall_match_percentage DECIMAL(5,2),

        -- Category breakdowns
        schema_validations INT,
        data_validations INT,
        business_rule_validations INT,

        -- Error categories
        critical_errors INT,
        warnings INT,
        info_messages INT,

        -- Performance metrics
        total_execution_time_seconds INT,
        avg_step_execution_time_ms INT,

        -- Computed scores
        data_quality_score DECIMAL(5,2),  -- 0-100 score
        completeness_score DECIMAL(5,2),
        consistency_score DECIMAL(5,2),

        created_at DATETIME2 NOT NULL DEFAULT GETDATE(),

        FOREIGN KEY (run_id) REFERENCES PipelineRuns(run_id) ON DELETE CASCADE
    );

    CREATE INDEX IX_DataQualityMetrics_RunId ON DataQualityMetrics(run_id);
    CREATE INDEX IX_DataQualityMetrics_MetricDate ON DataQualityMetrics(metric_date DESC);
END
GO

-- ============================================================================
-- Views for Easy Querying
-- ============================================================================

-- Latest Pipeline Runs with Summary
IF EXISTS (SELECT * FROM sys.views WHERE name = 'vw_LatestPipelineRuns')
    DROP VIEW vw_LatestPipelineRuns;
GO

CREATE VIEW vw_LatestPipelineRuns AS
SELECT
    pr.run_id,
    pr.project_id,
    p.project_name,
    pr.pipeline_name,
    pr.status,
    pr.started_at,
    pr.completed_at,
    pr.duration_seconds,
    pr.total_steps,
    pr.successful_steps,
    pr.failed_steps,
    pr.errors_count,
    pr.warnings_count,
    CASE
        WHEN pr.status = 'completed' AND pr.failed_steps = 0 THEN 'success'
        WHEN pr.status = 'completed' AND pr.failed_steps > 0 THEN 'completed_with_errors'
        WHEN pr.status = 'failed' THEN 'failed'
        ELSE pr.status
    END as result_status
FROM PipelineRuns pr
LEFT JOIN Projects p ON pr.project_id = p.project_id;
GO

-- Step-Level Details with Parent Run Info
IF EXISTS (SELECT * FROM sys.views WHERE name = 'vw_ValidationStepDetails')
    DROP VIEW vw_ValidationStepDetails;
GO

CREATE VIEW vw_ValidationStepDetails AS
SELECT
    vs.step_id,
    vs.run_id,
    pr.pipeline_name,
    pr.project_id,
    vs.step_name,
    vs.step_order,
    vs.validator_type,
    vs.status,
    vs.started_at,
    vs.completed_at,
    vs.duration_milliseconds,
    vs.difference_type,
    vs.total_rows,
    vs.differing_rows_count,
    vs.match_percentage,
    vs.result_message,
    pr.started_at as run_started_at
FROM ValidationSteps vs
INNER JOIN PipelineRuns pr ON vs.run_id = pr.run_id;
GO

-- Daily Quality Metrics Trend
IF EXISTS (SELECT * FROM sys.views WHERE name = 'vw_DailyQualityTrend')
    DROP VIEW vw_DailyQualityTrend;
GO

CREATE VIEW vw_DailyQualityTrend AS
SELECT
    metric_date,
    COUNT(DISTINCT run_id) as total_runs,
    AVG(data_quality_score) as avg_quality_score,
    SUM(total_mismatches) as total_mismatches,
    AVG(overall_match_percentage) as avg_match_percentage,
    SUM(critical_errors) as total_critical_errors,
    SUM(warnings) as total_warnings
FROM DataQualityMetrics
GROUP BY metric_date;
GO

-- ============================================================================
-- Stored Procedures
-- ============================================================================

-- Get Pipeline Run History
IF EXISTS (SELECT * FROM sys.procedures WHERE name = 'sp_GetPipelineRunHistory')
    DROP PROCEDURE sp_GetPipelineRunHistory;
GO

CREATE PROCEDURE sp_GetPipelineRunHistory
    @ProjectId VARCHAR(100) = NULL,
    @PipelineName NVARCHAR(255) = NULL,
    @Status VARCHAR(20) = NULL,
    @StartDate DATETIME2 = NULL,
    @EndDate DATETIME2 = NULL,
    @Limit INT = 100,
    @Offset INT = 0
AS
BEGIN
    SET NOCOUNT ON;

    SELECT
        run_id,
        project_id,
        pipeline_name,
        status,
        started_at,
        completed_at,
        duration_seconds,
        total_steps,
        successful_steps,
        failed_steps,
        errors_count,
        warnings_count
    FROM PipelineRuns
    WHERE (@ProjectId IS NULL OR project_id = @ProjectId)
        AND (@PipelineName IS NULL OR pipeline_name = @PipelineName)
        AND (@Status IS NULL OR status = @Status)
        AND (@StartDate IS NULL OR started_at >= @StartDate)
        AND (@EndDate IS NULL OR started_at <= @EndDate)
    ORDER BY started_at DESC
    OFFSET @Offset ROWS
    FETCH NEXT @Limit ROWS ONLY;
END
GO

-- Get Step Details for Run
IF EXISTS (SELECT * FROM sys.procedures WHERE name = 'sp_GetStepDetails')
    DROP PROCEDURE sp_GetStepDetails;
GO

CREATE PROCEDURE sp_GetStepDetails
    @RunId VARCHAR(100)
AS
BEGIN
    SET NOCOUNT ON;

    SELECT
        step_id,
        run_id,
        step_name,
        step_order,
        validator_type,
        status,
        started_at,
        completed_at,
        duration_milliseconds,
        result_message,
        difference_type,
        total_rows,
        differing_rows_count,
        affected_columns,
        match_percentage,
        sql_row_count,
        snowflake_row_count,
        error_message
    FROM ValidationSteps
    WHERE run_id = @RunId
    ORDER BY step_order;
END
GO

-- Get Comparison Details for Step
IF EXISTS (SELECT * FROM sys.procedures WHERE name = 'sp_GetComparisonDetails')
    DROP PROCEDURE sp_GetComparisonDetails;
GO

CREATE PROCEDURE sp_GetComparisonDetails
    @RunId VARCHAR(100),
    @StepName NVARCHAR(255)
AS
BEGIN
    SET NOCOUNT ON;

    SELECT
        step_id,
        run_id,
        step_name,
        status,
        difference_type,
        total_rows,
        differing_rows_count,
        affected_columns,
        comparison_details,
        result_message
    FROM ValidationSteps
    WHERE run_id = @RunId
        AND step_name = @StepName;
END
GO

-- ============================================================================
-- Sample Data for Testing (Optional - comment out for production)
-- ============================================================================

/*
-- Insert sample project
IF NOT EXISTS (SELECT * FROM Projects WHERE project_id = 'sample_project')
BEGIN
    INSERT INTO Projects (project_id, project_name, description, created_by, tags)
    VALUES ('sample_project', 'Sample Data Migration', 'Test project for data validation', 'admin', '["test", "sample"]');
END

-- Insert sample pipeline run
IF NOT EXISTS (SELECT * FROM PipelineRuns WHERE run_id = 'run_sample_001')
BEGIN
    INSERT INTO PipelineRuns (
        run_id, project_id, pipeline_name, status, started_at, completed_at,
        duration_seconds, total_steps, successful_steps, failed_steps,
        errors_count, warnings_count, executed_by
    )
    VALUES (
        'run_sample_001', 'sample_project', 'Daily Validation', 'completed',
        DATEADD(hour, -2, GETDATE()), DATEADD(hour, -1, GETDATE()),
        3600, 5, 4, 1, 10, 2, 'admin'
    );
END
*/

PRINT 'Database schema created successfully!';
PRINT 'Tables: Projects, PipelineRuns, ValidationSteps, ExecutionLogs, DataQualityMetrics';
PRINT 'Views: vw_LatestPipelineRuns, vw_ValidationStepDetails, vw_DailyQualityTrend';
PRINT 'Stored Procedures: sp_GetPipelineRunHistory, sp_GetStepDetails, sp_GetComparisonDetails';
GO
