# src/ombudsman/pipeline/pipeline_runner.py
'''
Executes an entire ordered validation suite.

''' 


# src/ombudsman/pipeline/pipeline_runner.py
'''
Executes an entire ordered validation suite.
'''

from ombudsman.core.connections import get_snow_conn
from datetime import datetime
import json  


class PipelineRunner:
    def __init__(self, executor, logger, cfg=None):
        self.executor = executor
        self.logger = logger
        self.tables_initialized = False

        # create a single Snowflake connection for the run
        if cfg:
            self.snow_conn = get_snow_conn(cfg)
            self.cursor = self.snow_conn.cursor()
        else:
            self.snow_conn = None
            self.cursor = None

    def _ensure_tables_exist(self):
        """Create OMBUDSMAN_RESULTS table if it doesn't exist"""
        if self.tables_initialized or not self.cursor:
            return

        try:
            # Get database and schema from connection
            database = self.snow_conn.database
            schema = self.snow_conn.schema

            # Use fully qualified table name to avoid database context issues
            if database and schema:
                table_name = f"{database}.{schema}.OMBUDSMAN_RESULTS"
            else:
                table_name = "OMBUDSMAN_RESULTS"

            # Create table if it doesn't exist
            self.cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {table_name} (
                    ID INTEGER AUTOINCREMENT PRIMARY KEY,
                    PIPELINE_NAME STRING,
                    STEP_NAME STRING,
                    STATUS STRING,
                    MESSAGE STRING,
                    RUN_TIMESTAMP TIMESTAMP_LTZ DEFAULT CURRENT_TIMESTAMP
                )
            """)
            self.snow_conn.commit()
            self.tables_initialized = True
            print(f"✓ OMBUDSMAN_RESULTS table initialized at {table_name}")
        except Exception as e:
            print(f"Warning: Failed to create OMBUDSMAN_RESULTS table: {e}")
            # If table creation fails, it might already exist or we don't have permissions
            # Mark as initialized to avoid repeated attempts
            self.tables_initialized = True

    def _write_result_to_snowflake(self, pipeline_name, result):
        if not self.cursor or not self.tables_initialized:
            return  # Skip if no Snowflake connection configured or table creation failed

        try:
            # Get fully qualified table name
            database = self.snow_conn.database
            schema = self.snow_conn.schema
            if database and schema:
                table_name = f"{database}.{schema}.OMBUDSMAN_RESULTS"
            else:
                table_name = "OMBUDSMAN_RESULTS"

            # Convert details to JSON string for MESSAGE column
            message = json.dumps({
                "severity": result.severity,
                "details": result.details,
                "timestamp": result.timestamp
            })

            self.cursor.execute(f"""
                INSERT INTO {table_name} (PIPELINE_NAME, STEP_NAME, STATUS, MESSAGE)
                VALUES (%s, %s, %s, %s)
            """, (
                pipeline_name,
                result.name,  # Fixed: was result.step, now result.name
                result.status,
                message  # Fixed: was result.message, now JSON string with details
            ))
            self.snow_conn.commit()
        except Exception as e:
            # Silently skip Snowflake logging if it fails
            # Results are still returned to the API
            print(f"Note: Snowflake logging skipped: {e}")

    def run(self, pipeline_def, pipeline_name="UNKNOWN_PIPELINE"):
        results = []

        # Ensure Snowflake tables exist once at the start
        self._ensure_tables_exist()

        for step in pipeline_def:
            # run the validation step
            res = self.executor.run_step(step)
            results.append(res)

            # normal logging
            self.logger.log(res.to_dict())

            # write into Snowflake database
            self._write_result_to_snowflake(pipeline_name, res)

        return results