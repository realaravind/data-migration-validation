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

        print(f"[DEBUG StepExecutor] Looking up validator: '{name}'")
        entry = self.registry.get(name)
        if not entry:
            print(f"[DEBUG StepExecutor] Validator '{name}' NOT FOUND in registry")
            print(f"[DEBUG StepExecutor] Available validators: {sorted(list(self.registry.registry.keys()))[:10]}...")
            return ValidationResult(
                name,
                status="SKIPPED",
                details={"reason": "not in registry"}
            )

        print(f"[DEBUG StepExecutor] Found validator '{name}' in registry")

        func = entry["func"]

        try:
            # Try calling with standard parameters
            try:
                result = func(
                    sql_conn=self.sql_conn,
                    snow_conn=self.snow_conn,
                    mapping=self.mapping,
                    metadata=self.metadata,
                    **cfg
                )
            except TypeError as e:
                # If function doesn't accept these parameters, try without them
                import inspect
                sig = inspect.signature(func)
                params = sig.parameters

                # Build kwargs based on what function actually accepts
                call_kwargs = {}

                if 'sql_conn' in params:
                    call_kwargs['sql_conn'] = self.sql_conn
                if 'snow_conn' in params:
                    call_kwargs['snow_conn'] = self.snow_conn
                if 'conn' in params:  # Some validators use 'conn' instead
                    call_kwargs['conn'] = self.sql_conn
                if 'mapping' in params:
                    call_kwargs['mapping'] = self.mapping
                if 'metadata' in params:
                    call_kwargs['metadata'] = self.metadata

                # Add config parameters
                for key, value in cfg.items():
                    if key in params:
                        call_kwargs[key] = value

                print(f"[DEBUG StepExecutor] Retrying with adapted parameters: {list(call_kwargs.keys())}")
                result = func(**call_kwargs)

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