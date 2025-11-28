'''
Bootstrap: Validator Auto‑Registration

This file imports all validators and registers them automatically with the registry.
'''
# src/ombudsman/bootstrap.py

def register_validators(registry):

    # ---- Data Quality Validators (Batch 4) ----
    from .validation.dq.validate_nulls import validate_nulls
    from .validation.dq.validate_uniqueness import validate_uniqueness
    from .validation.dq.validate_domain_values import validate_domain_values
    from .validation.dq.validate_distribution import validate_distribution
    from .validation.dq.validate_statistics import validate_statistics
    from .validation.dq.validate_outliers import validate_outliers
    from .validation.dq.validate_record_counts import validate_record_counts
    from .validation.dq.validate_regex_patterns import validate_regex_patterns

    registry.register("validate_nulls", validate_nulls, "dq")
    registry.register("validate_uniqueness", validate_uniqueness, "dq")
    registry.register("validate_domain_values", validate_domain_values, "dq")
    registry.register("validate_distribution", validate_distribution, "dq")
    registry.register("validate_statistics", validate_statistics, "dq")
    registry.register("validate_outliers", validate_outliers, "dq")
    registry.register("validate_record_counts", validate_record_counts, "dq")
    registry.register("validate_regex_patterns", validate_regex_patterns, "dq")

    # ---- Referential Integrity (Batch 5) ----
    from .validation.ri.validate_foreign_keys import validate_foreign_keys
    from .validation.ri.validate_cross_system_fk_alignment import (
        validate_cross_system_fk_alignment
    )

    registry.register("validate_foreign_keys", validate_foreign_keys, "ri")
    registry.register("validate_cross_system_fk_alignment", validate_cross_system_fk_alignment, "ri")

    # ---- Metric Validators (Batch 5) ----
    from .validation.metrics.validate_metric_sums import validate_metric_sums
    from .validation.metrics.validate_metric_averages import validate_metric_averages
    from .validation.metrics.validate_ratios import validate_ratios

    registry.register("validate_metric_sums", validate_metric_sums, "metrics")
    registry.register("validate_metric_averages", validate_metric_averages, "metrics")
    registry.register("validate_ratios", validate_ratios, "metrics")

    # ---- Time Series Validators (Batch 5) ----
    from .validation.timeseries.validate_ts_continuity import validate_ts_continuity
    from .validation.timeseries.validate_ts_duplicates import validate_ts_duplicates
    from .validation.timeseries.validate_ts_rolling_drift import validate_ts_rolling_drift
    from .validation.timeseries.validate_period_over_period import validate_period_over_period

    registry.register("validate_ts_continuity", validate_ts_continuity, "timeseries")
    registry.register("validate_ts_duplicates", validate_ts_duplicates, "timeseries")
    registry.register("validate_ts_rolling_drift", validate_ts_rolling_drift, "timeseries")
    registry.register("validate_period_over_period", validate_period_over_period, "timeseries")

    return registry
