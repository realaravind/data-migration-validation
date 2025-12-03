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

        print(f"[DEBUG StepExecutor] Executing step: '{name}'")
        print(f"[DEBUG StepExecutor] Config keys: {list(cfg.keys())}")

        entry = self.registry.get(name)
        if not entry:
            print(f"[ERROR StepExecutor] Validator '{name}' NOT FOUND in registry")
            print(f"[INFO StepExecutor] Available validators: {sorted(list(self.registry.registry.keys()))}")
            return ValidationResult(
                name,
                status="SKIPPED",
                severity="HIGH",
                details={
                    "reason": "Validator not found in registry",
                    "validator_name": name,
                    "available_validators": sorted(list(self.registry.registry.keys()))[:20]
                }
            )

        print(f"[DEBUG StepExecutor] Found validator '{name}' in registry")

        func = entry["func"]

        try:
            import inspect
            sig = inspect.signature(func)
            params = sig.parameters

            print(f"[DEBUG StepExecutor] Validator '{name}' expects parameters: {list(params.keys())}")

            # Build complete kwargs with both injected dependencies and config
            call_kwargs = {}

            # Add injected dependencies if validator accepts them
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

            # Add config parameters (these override injected ones if same key)
            for key, value in cfg.items():
                if key in params:
                    call_kwargs[key] = value
                elif params.get(key, None) is not None or key not in call_kwargs:
                    # Validator might accept **kwargs, so include it
                    call_kwargs[key] = value

            print(f"[DEBUG StepExecutor] Calling validator with: {list(call_kwargs.keys())}")

            # Call the validator function
            result = func(**call_kwargs)

            # Validate result format
            if not isinstance(result, dict):
                print(f"[ERROR StepExecutor] Validator '{name}' returned non-dict result: {type(result)}")
                return ValidationResult(
                    name,
                    status="ERROR",
                    severity="HIGH",
                    details={"error": f"Validator returned invalid result type: {type(result)}"}
                )

            if "status" not in result:
                print(f"[ERROR StepExecutor] Validator '{name}' result missing 'status' field")
                return ValidationResult(
                    name,
                    status="ERROR",
                    severity="HIGH",
                    details={"error": "Validator result missing required 'status' field", "result": result}
                )

            # Return properly formatted ValidationResult
            return ValidationResult(
                name=name,
                status=result.get("status"),
                severity=result.get("severity", "NONE"),
                details={k: v for k, v in result.items() if k not in ("status", "severity")}
            )

        except TypeError as e:
            # Parameter mismatch - provide detailed error
            import inspect
            sig = inspect.signature(func)
            expected_params = list(sig.parameters.keys())
            provided_params = list(call_kwargs.keys()) if 'call_kwargs' in locals() else []

            error_msg = f"Parameter mismatch for validator '{name}': {str(e)}"
            print(f"[ERROR StepExecutor] {error_msg}")
            print(f"[ERROR StepExecutor] Expected parameters: {expected_params}")
            print(f"[ERROR StepExecutor] Provided parameters: {provided_params}")

            return ValidationResult(
                name,
                status="ERROR",
                severity="HIGH",
                details={
                    "error": error_msg,
                    "expected_parameters": expected_params,
                    "provided_parameters": provided_params,
                    "config": cfg
                }
            )
        except Exception as e:
            # General exception - capture full context
            import traceback
            error_trace = traceback.format_exc()

            print(f"[ERROR StepExecutor] Validator '{name}' raised exception: {str(e)}")
            print(f"[ERROR StepExecutor] Full traceback:\n{error_trace}")

            return ValidationResult(
                name,
                status="ERROR",
                severity="HIGH",
                details={
                    "exception": str(e),
                    "exception_type": type(e).__name__,
                    "traceback": error_trace,
                    "config": cfg
                }
            )