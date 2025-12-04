"""
Results Repository

Handles all database operations for pipeline execution results.
Uses pyodbc for SQL Server connectivity.
"""

import os
import json
import pyodbc
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple

from .models import (
    Project, PipelineRun, ValidationStep, ExecutionLog, DataQualityMetrics,
    ProjectCreate, ProjectUpdate, PipelineRunCreate, PipelineRunUpdate,
    ValidationStepCreate, ValidationStepUpdate,
    PipelineRunHistory, ValidationStepDetail, DailyQualityTrend,
    PipelineStatus, StepStatus, LogLevel
)

logger = logging.getLogger(__name__)


class ResultsRepository:
    """Repository for storing and retrieving pipeline execution results"""

    def __init__(self, connection_string: Optional[str] = None):
        """
        Initialize repository with database connection.

        Args:
            connection_string: SQL Server connection string.
                             If None, builds from environment variables.
        """
        if connection_string is None:
            # Build from environment variables
            host = os.getenv('RESULTS_DB_HOST', os.getenv('MSSQL_HOST', 'localhost'))
            port = os.getenv('RESULTS_DB_PORT', '1433')
            database = os.getenv('RESULTS_DB_NAME', 'OmbudsmanResults')
            user = os.getenv('RESULTS_DB_USER', os.getenv('MSSQL_USER', 'sa'))
            password = os.getenv('RESULTS_DB_PASSWORD', os.getenv('MSSQL_PASSWORD', ''))

            connection_string = (
                f"DRIVER={{ODBC Driver 18 for SQL Server}};"
                f"SERVER={host},{port};"
                f"DATABASE={database};"
                f"UID={user};"
                f"PWD={password};"
                f"TrustServerCertificate=yes;"
            )

        self.connection_string = connection_string
        logger.info("ResultsRepository initialized")

    def _get_connection(self) -> pyodbc.Connection:
        """Get database connection"""
        return pyodbc.connect(self.connection_string, timeout=10)

    def _execute_query(self, query: str, params: Optional[Tuple] = None) -> List[Dict[str, Any]]:
        """
        Execute SELECT query and return results as list of dicts.

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            List of dictionaries with column names as keys
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)

            # Get column names
            columns = [column[0] for column in cursor.description] if cursor.description else []

            # Fetch all rows
            rows = cursor.fetchall()

            # Convert to list of dicts
            results = []
            for row in rows:
                row_dict = {}
                for i, col in enumerate(columns):
                    row_dict[col] = row[i]
                results.append(row_dict)

            cursor.close()
            return results
        finally:
            conn.close()

    def _execute_non_query(self, query: str, params: Optional[Tuple] = None) -> int:
        """
        Execute INSERT/UPDATE/DELETE query.

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            Number of affected rows
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            conn.commit()
            affected_rows = cursor.rowcount
            cursor.close()
            return affected_rows
        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()

    # ========================================================================
    # Projects
    # ========================================================================

    def create_project(self, project: ProjectCreate) -> Project:
        """Create a new project"""
        query = """
        INSERT INTO Projects (project_id, project_name, description, created_by, tags, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, GETDATE(), GETDATE())
        """
        tags_json = json.dumps(project.tags) if project.tags else None
        self._execute_non_query(query, (
            project.project_id,
            project.project_name,
            project.description,
            project.created_by,
            tags_json
        ))
        logger.info(f"Created project: {project.project_id}")
        return self.get_project(project.project_id)

    def get_project(self, project_id: str) -> Optional[Project]:
        """Get project by ID"""
        query = "SELECT * FROM Projects WHERE project_id = ?"
        results = self._execute_query(query, (project_id,))
        if results:
            row = results[0]
            return Project(
                project_id=row['project_id'],
                project_name=row['project_name'],
                description=row['description'],
                created_at=row['created_at'],
                updated_at=row['updated_at'],
                created_by=row['created_by'],
                tags=json.loads(row['tags']) if row.get('tags') else None,
                is_active=row['is_active']
            )
        return None

    def list_projects(self, active_only: bool = True) -> List[Project]:
        """List all projects"""
        query = "SELECT * FROM Projects"
        if active_only:
            query += " WHERE is_active = 1"
        query += " ORDER BY created_at DESC"

        results = self._execute_query(query)
        projects = []
        for row in results:
            projects.append(Project(
                project_id=row['project_id'],
                project_name=row['project_name'],
                description=row['description'],
                created_at=row['created_at'],
                updated_at=row['updated_at'],
                created_by=row['created_by'],
                tags=json.loads(row['tags']) if row.get('tags') else None,
                is_active=row['is_active']
            ))
        return projects

    def update_project(self, project_id: str, update: ProjectUpdate) -> Optional[Project]:
        """Update project"""
        updates = []
        params = []

        if update.project_name is not None:
            updates.append("project_name = ?")
            params.append(update.project_name)
        if update.description is not None:
            updates.append("description = ?")
            params.append(update.description)
        if update.tags is not None:
            updates.append("tags = ?")
            params.append(json.dumps(update.tags))
        if update.is_active is not None:
            updates.append("is_active = ?")
            params.append(update.is_active)

        if not updates:
            return self.get_project(project_id)

        updates.append("updated_at = GETDATE()")
        params.append(project_id)

        query = f"UPDATE Projects SET {', '.join(updates)} WHERE project_id = ?"
        self._execute_non_query(query, tuple(params))
        logger.info(f"Updated project: {project_id}")
        return self.get_project(project_id)

    # ========================================================================
    # Pipeline Runs
    # ========================================================================

    def create_pipeline_run(self, run: PipelineRunCreate) -> PipelineRun:
        """Create a new pipeline run"""
        query = """
        INSERT INTO PipelineRuns (
            run_id, project_id, pipeline_name, status, started_at,
            pipeline_config, executed_by
        )
        VALUES (?, ?, ?, ?, GETDATE(), ?, ?)
        """
        config_json = json.dumps(run.pipeline_config) if run.pipeline_config else None
        self._execute_non_query(query, (
            run.run_id,
            run.project_id,
            run.pipeline_name,
            PipelineStatus.PENDING.value,
            config_json,
            run.executed_by
        ))
        logger.info(f"Created pipeline run: {run.run_id}")
        return self.get_pipeline_run(run.run_id)

    def get_pipeline_run(self, run_id: str) -> Optional[PipelineRun]:
        """Get pipeline run by ID"""
        query = "SELECT * FROM PipelineRuns WHERE run_id = ?"
        results = self._execute_query(query, (run_id,))
        if results:
            row = results[0]
            return PipelineRun(
                run_id=row['run_id'],
                project_id=row['project_id'],
                pipeline_name=row['pipeline_name'],
                status=PipelineStatus(row['status']),
                started_at=row['started_at'],
                completed_at=row['completed_at'],
                duration_seconds=row['duration_seconds'],
                pipeline_config=json.loads(row['pipeline_config']) if row.get('pipeline_config') else None,
                error_message=row['error_message'],
                total_steps=row['total_steps'],
                successful_steps=row['successful_steps'],
                failed_steps=row['failed_steps'],
                warnings_count=row['warnings_count'],
                errors_count=row['errors_count'],
                executed_by=row['executed_by']
            )
        return None

    def update_pipeline_run(self, run_id: str, update: PipelineRunUpdate) -> Optional[PipelineRun]:
        """Update pipeline run"""
        updates = []
        params = []

        if update.status is not None:
            updates.append("status = ?")
            params.append(update.status.value)
        if update.completed_at is not None:
            updates.append("completed_at = ?")
            params.append(update.completed_at)
        if update.duration_seconds is not None:
            updates.append("duration_seconds = ?")
            params.append(update.duration_seconds)
        if update.error_message is not None:
            updates.append("error_message = ?")
            params.append(update.error_message)
        if update.total_steps is not None:
            updates.append("total_steps = ?")
            params.append(update.total_steps)
        if update.successful_steps is not None:
            updates.append("successful_steps = ?")
            params.append(update.successful_steps)
        if update.failed_steps is not None:
            updates.append("failed_steps = ?")
            params.append(update.failed_steps)
        if update.warnings_count is not None:
            updates.append("warnings_count = ?")
            params.append(update.warnings_count)
        if update.errors_count is not None:
            updates.append("errors_count = ?")
            params.append(update.errors_count)

        if not updates:
            return self.get_pipeline_run(run_id)

        params.append(run_id)
        query = f"UPDATE PipelineRuns SET {', '.join(updates)} WHERE run_id = ?"
        self._execute_non_query(query, tuple(params))
        logger.info(f"Updated pipeline run: {run_id}")
        return self.get_pipeline_run(run_id)

    def get_pipeline_run_history(
        self,
        project_id: Optional[str] = None,
        pipeline_name: Optional[str] = None,
        status: Optional[PipelineStatus] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[PipelineRunHistory]:
        """Get pipeline run history with filters"""
        query = """
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
        LEFT JOIN Projects p ON pr.project_id = p.project_id
        WHERE 1=1
        """
        params = []

        if project_id:
            query += " AND pr.project_id = ?"
            params.append(project_id)
        if pipeline_name:
            query += " AND pr.pipeline_name = ?"
            params.append(pipeline_name)
        if status:
            query += " AND pr.status = ?"
            params.append(status.value)
        if start_date:
            query += " AND pr.started_at >= ?"
            params.append(start_date)
        if end_date:
            query += " AND pr.started_at <= ?"
            params.append(end_date)

        query += f" ORDER BY pr.started_at DESC OFFSET {offset} ROWS FETCH NEXT {limit} ROWS ONLY"

        results = self._execute_query(query, tuple(params) if params else None)
        return [PipelineRunHistory(**row) for row in results]

    # ========================================================================
    # Validation Steps
    # ========================================================================

    def create_validation_step(self, step: ValidationStepCreate) -> ValidationStep:
        """Create a new validation step"""
        query = """
        INSERT INTO ValidationSteps (
            run_id, step_name, step_order, validator_type, status, started_at, step_config
        )
        OUTPUT INSERTED.step_id
        VALUES (?, ?, ?, ?, ?, GETDATE(), ?)
        """
        config_json = json.dumps(step.step_config) if step.step_config else None

        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, (
                step.run_id,
                step.step_name,
                step.step_order,
                step.validator_type,
                StepStatus.PASSED.value,
                config_json
            ))
            step_id = cursor.fetchone()[0]
            conn.commit()
            cursor.close()
            logger.info(f"Created validation step: {step_id} for run {step.run_id}")
            return self.get_validation_step(step_id)
        finally:
            conn.close()

    def get_validation_step(self, step_id: int) -> Optional[ValidationStep]:
        """Get validation step by ID"""
        query = "SELECT * FROM ValidationSteps WHERE step_id = ?"
        results = self._execute_query(query, (step_id,))
        if results:
            row = results[0]
            return self._row_to_validation_step(row)
        return None

    def update_validation_step(self, step_id: int, update: ValidationStepUpdate) -> Optional[ValidationStep]:
        """Update validation step"""
        updates = []
        params = []

        if update.status is not None:
            updates.append("status = ?")
            params.append(update.status.value)
        if update.completed_at is not None:
            updates.append("completed_at = ?")
            params.append(update.completed_at)
        if update.duration_milliseconds is not None:
            updates.append("duration_milliseconds = ?")
            params.append(update.duration_milliseconds)
        if update.result_message is not None:
            updates.append("result_message = ?")
            params.append(update.result_message)
        if update.difference_type is not None:
            updates.append("difference_type = ?")
            params.append(update.difference_type)
        if update.total_rows is not None:
            updates.append("total_rows = ?")
            params.append(update.total_rows)
        if update.differing_rows_count is not None:
            updates.append("differing_rows_count = ?")
            params.append(update.differing_rows_count)
        if update.affected_columns is not None:
            updates.append("affected_columns = ?")
            params.append(json.dumps(update.affected_columns))
        if update.comparison_details is not None:
            updates.append("comparison_details = ?")
            params.append(json.dumps(update.comparison_details))
        if update.sql_row_count is not None:
            updates.append("sql_row_count = ?")
            params.append(update.sql_row_count)
        if update.snowflake_row_count is not None:
            updates.append("snowflake_row_count = ?")
            params.append(update.snowflake_row_count)
        if update.match_percentage is not None:
            updates.append("match_percentage = ?")
            params.append(update.match_percentage)
        if update.error_message is not None:
            updates.append("error_message = ?")
            params.append(update.error_message)
        if update.error_stack_trace is not None:
            updates.append("error_stack_trace = ?")
            params.append(update.error_stack_trace)

        if not updates:
            return self.get_validation_step(step_id)

        params.append(step_id)
        query = f"UPDATE ValidationSteps SET {', '.join(updates)} WHERE step_id = ?"
        self._execute_non_query(query, tuple(params))
        logger.info(f"Updated validation step: {step_id}")
        return self.get_validation_step(step_id)

    def get_steps_for_run(self, run_id: str) -> List[ValidationStep]:
        """Get all validation steps for a pipeline run"""
        query = "SELECT * FROM ValidationSteps WHERE run_id = ? ORDER BY step_order"
        results = self._execute_query(query, (run_id,))
        return [self._row_to_validation_step(row) for row in results]

    def _row_to_validation_step(self, row: Dict[str, Any]) -> ValidationStep:
        """Convert database row to ValidationStep model"""
        return ValidationStep(
            step_id=row['step_id'],
            run_id=row['run_id'],
            step_name=row['step_name'],
            step_order=row['step_order'],
            validator_type=row['validator_type'],
            status=StepStatus(row['status']),
            started_at=row['started_at'],
            completed_at=row['completed_at'],
            duration_milliseconds=row['duration_milliseconds'],
            result_message=row['result_message'],
            difference_type=row['difference_type'],
            total_rows=row['total_rows'],
            differing_rows_count=row['differing_rows_count'],
            affected_columns=json.loads(row['affected_columns']) if row.get('affected_columns') else None,
            comparison_details=json.loads(row['comparison_details']) if row.get('comparison_details') else None,
            sql_row_count=row['sql_row_count'],
            snowflake_row_count=row['snowflake_row_count'],
            match_percentage=row['match_percentage'],
            step_config=json.loads(row['step_config']) if row.get('step_config') else None,
            error_message=row['error_message'],
            error_stack_trace=row['error_stack_trace']
        )

    # ========================================================================
    # Execution Logs
    # ========================================================================

    def add_execution_log(
        self,
        run_id: str,
        log_level: LogLevel,
        message: str,
        step_id: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Add execution log entry"""
        query = """
        INSERT INTO ExecutionLogs (run_id, step_id, log_level, message, timestamp, context)
        VALUES (?, ?, ?, ?, GETDATE(), ?)
        """
        context_json = json.dumps(context) if context else None
        self._execute_non_query(query, (run_id, step_id, log_level.value, message, context_json))

    def get_execution_logs(
        self,
        run_id: str,
        step_id: Optional[int] = None,
        log_level: Optional[LogLevel] = None,
        limit: int = 1000
    ) -> List[ExecutionLog]:
        """Get execution logs for a run"""
        query = "SELECT * FROM ExecutionLogs WHERE run_id = ?"
        params = [run_id]

        if step_id:
            query += " AND step_id = ?"
            params.append(step_id)
        if log_level:
            query += " AND log_level = ?"
            params.append(log_level.value)

        query += f" ORDER BY timestamp DESC OFFSET 0 ROWS FETCH NEXT {limit} ROWS ONLY"

        results = self._execute_query(query, tuple(params))
        logs = []
        for row in results:
            logs.append(ExecutionLog(
                log_id=row['log_id'],
                run_id=row['run_id'],
                step_id=row['step_id'],
                log_level=LogLevel(row['log_level']),
                message=row['message'],
                timestamp=row['timestamp'],
                context=json.loads(row['context']) if row.get('context') else None
            ))
        return logs

    # ========================================================================
    # Data Quality Metrics
    # ========================================================================

    def save_quality_metrics(self, metrics: DataQualityMetrics) -> DataQualityMetrics:
        """Save data quality metrics"""
        query = """
        INSERT INTO DataQualityMetrics (
            run_id, metric_date, total_tables_validated, total_rows_compared,
            total_mismatches, overall_match_percentage, schema_validations,
            data_validations, business_rule_validations, critical_errors,
            warnings, info_messages, total_execution_time_seconds,
            avg_step_execution_time_ms, data_quality_score, completeness_score,
            consistency_score, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, GETDATE())
        """
        self._execute_non_query(query, (
            metrics.run_id,
            metrics.metric_date,
            metrics.total_tables_validated,
            metrics.total_rows_compared,
            metrics.total_mismatches,
            metrics.overall_match_percentage,
            metrics.schema_validations,
            metrics.data_validations,
            metrics.business_rule_validations,
            metrics.critical_errors,
            metrics.warnings,
            metrics.info_messages,
            metrics.total_execution_time_seconds,
            metrics.avg_step_execution_time_ms,
            metrics.data_quality_score,
            metrics.completeness_score,
            metrics.consistency_score
        ))
        logger.info(f"Saved quality metrics for run: {metrics.run_id}")
        return metrics

    def get_daily_quality_trend(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[DailyQualityTrend]:
        """Get daily quality trend"""
        query = """
        SELECT
            metric_date,
            COUNT(DISTINCT run_id) as total_runs,
            AVG(data_quality_score) as avg_quality_score,
            SUM(total_mismatches) as total_mismatches,
            AVG(overall_match_percentage) as avg_match_percentage,
            SUM(critical_errors) as total_critical_errors,
            SUM(warnings) as total_warnings
        FROM DataQualityMetrics
        WHERE 1=1
        """
        params = []

        if start_date:
            query += " AND metric_date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND metric_date <= ?"
            params.append(end_date)

        query += " GROUP BY metric_date ORDER BY metric_date DESC"

        results = self._execute_query(query, tuple(params) if params else None)
        return [DailyQualityTrend(**row) for row in results]
