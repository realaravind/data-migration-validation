# Validation module for custom validators
# Uses lazy imports to avoid startup failures if dependencies are missing

__all__ = [
    # AI Type Checker
    "get_ai_type_checker",
    "batch_check_types",
    "clear_type_cache",
    # AI Table Classifier
    "classify_table_sync",
    "classify_table_by_rules",
    "TableType",
    "TableClassification",
    "filter_validations_for_table",
    "get_validations_for_table_type",
    "FACT_VALIDATIONS",
    "DIMENSION_VALIDATIONS",
    "clear_classification_cache",
]


def __getattr__(name):
    """Lazy import to avoid startup failures."""
    if name in ("get_ai_type_checker", "batch_check_types", "clear_type_cache"):
        from .ai_type_checker import get_ai_type_checker, batch_check_types, clear_type_cache
        return locals()[name]
    elif name in ("classify_table_sync", "classify_table_by_rules", "TableType",
                  "TableClassification", "filter_validations_for_table",
                  "get_validations_for_table_type", "FACT_VALIDATIONS",
                  "DIMENSION_VALIDATIONS", "clear_classification_cache"):
        from .ai_table_classifier import (
            classify_table_sync, classify_table_by_rules, TableType,
            TableClassification, filter_validations_for_table,
            get_validations_for_table_type, FACT_VALIDATIONS,
            DIMENSION_VALIDATIONS, clear_classification_cache,
        )
        return locals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
