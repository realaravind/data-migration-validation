# src/ombudsman/pipeline/step_executor.py
'''
Runs a single validator with injected dependencies.

'''

from ..core.result import ValidationResult

class StepExecutor:
    def __init__(self, registry, sql_conn, snow_conn, mapping, metadata):
        self.registry = registry
        self.sql_conn = sql_conn
        self.snow_conn = snow_conn
        self.mapping = mapping
        self.metadata = metadata

    def run_step(self, step):
        name = step["name"]
        cfg = step.get("config", {})

        entry = self.registry.get(name)
        if not entry:
            return ValidationResult(
                name, 
                status="SKIPPED", 
                details={"reason": "not in registry"}
            )

        func = entry["func"]

        try:
            result = func(
                sql_conn=self.sql_conn,
                snow_conn=self.snow_conn,
                mapping=self.mapping,
                metadata=self.metadata,
                **cfg
            )

            return ValidationResult(
                name=name,
                status=result.get("status"),
                severity=result.get("severity"),
                details={k: v for k, v in result.items() if k not in ("status", "severity")}
            )
        except Exception as e:
            return ValidationResult(
                name,
                status="ERROR",
                severity="HIGH",
                details={"exception": str(e)}
            )