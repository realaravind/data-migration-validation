from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
import yaml
from io import StringIO
import os

# Import domain-specific patterns
try:
    from .domain_patterns import match_domain_pattern, enhance_nl_with_domain_patterns
    DOMAIN_PATTERNS_AVAILABLE = True
except ImportError:
    DOMAIN_PATTERNS_AVAILABLE = False

router = APIRouter()


# Custom YAML Dumper for better formatting
class CustomYAMLDumper(yaml.SafeDumper):
    """Custom YAML dumper with better formatting"""
    pass


def str_representer(dumper, data):
    """Represent strings with literal style for multi-line strings, quoted if they contain special chars"""
    if '\n' in data:
        return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
    # Quote strings that contain YAML-special characters
    if any(ch in data for ch in (':', '#', '{', '}', '[', ']', '&', '*', '?', '|', '>', '!')):
        return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='"')
    return dumper.represent_scalar('tag:yaml.org,2002:str', data)


CustomYAMLDumper.add_representer(str, str_representer)


def _extract_metadata_structure(columns: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Extract proper metadata structure from columns list.

    The frontend sends columns as:
    [
        {'name': 'columns', 'type': {<dict of actual columns>}},
        {'name': 'object_type', 'type': 'TABLE'}
    ]

    We need to extract the actual columns dict and structure it properly.
    """
    result = {}

    for col in columns:
        col_name = col.get('name')
        col_type = col.get('type') or col.get('data_type', 'VARCHAR')

        if col_name == 'columns' and isinstance(col_type, dict):
            # This is the actual columns dict
            result['columns'] = col_type
        elif col_name == 'object_type':
            # This is the object type
            result['object_type'] = col_type
        else:
            # Regular column - shouldn't happen with the new structure, but handle it
            if 'columns' not in result:
                result['columns'] = {}
            result['columns'][col_name] = col_type

    # Ensure columns and object_type exist
    if 'columns' not in result:
        result['columns'] = {}
    if 'object_type' not in result:
        result['object_type'] = 'TABLE'

    return result


def format_yaml(data: dict) -> str:
    """Format YAML with consistent indentation and style"""
    return yaml.dump(
        data,
        Dumper=CustomYAMLDumper,
        default_flow_style=False,
        sort_keys=False,
        indent=2,
        width=100,
        allow_unicode=True
    )


class FactAnalysisRequest(BaseModel):
    """Request to analyze a fact table and suggest validations"""
    fact_table: str
    fact_schema: str
    database_type: str  # 'sql' or 'snow'
    columns: List[Dict[str, Any]]  # Column metadata
    relationships: List[Dict[str, Any]]  # FK relationships
    schema_mappings: Optional[Dict[str, str]] = None  # SQL schema -> Snowflake schema


class NaturalLanguagePipelineRequest(BaseModel):
    """Request to create pipeline from natural language"""
    description: str
    context: Optional[Dict[str, Any]] = None  # Table names, columns, etc.


@router.post("/suggest-for-fact")
async def suggest_fact_validations(request: FactAnalysisRequest):
    """
    Analyze a fact table and intelligently suggest business metric validations

    Example for SalesFact:
    - Sum validations: TotalAmount, Quantity, Tax
    - Average validations: UnitPrice, DiscountPct
    - Ratio validations: Discount/Sales, Tax/Sales
    - Time-series: Sales continuity by OrderDate
    - Fact-dim conformance: ProductID → DimProduct, CustomerID → DimCustomer
    """
    try:
        print(f"\n=== Analyzing {request.fact_table} ===")
        print(f"Total columns received: {len(request.columns)}")
        print(f"Sample columns: {request.columns[:3]}")

        # Analyze columns
        numeric_columns = []
        date_columns = []
        fk_columns = []

        for col in request.columns:
            col_name = col.get('name', '')
            col_type = col.get('data_type') or col.get('type') or ''

            # SPECIAL CASE: Frontend sends metadata as [{'name': 'columns', 'type': {COL1: TYPE1, ...}}, {'name': 'object_type', 'type': 'TABLE'}]
            # If col_name is 'columns' and col_type is a dict, expand it into actual columns
            if col_name == 'columns' and isinstance(col_type, dict):
                print(f"[DEBUG] Detected wrapped columns structure, expanding {len(col_type)} columns")
                for actual_col_name, actual_col_type in col_type.items():
                    if not isinstance(actual_col_type, str):
                        continue
                    actual_col_type_lower = actual_col_type.lower()

                    # Identify numeric columns
                    if any(t in actual_col_type_lower for t in ['int', 'decimal', 'numeric', 'number', 'float', 'money']):
                        numeric_columns.append(actual_col_name)

                    # Identify date columns
                    if any(t in actual_col_type_lower for t in ['date', 'datetime', 'timestamp']):
                        date_columns.append(actual_col_name)

                    # Identify FK columns
                    if any(suffix in actual_col_name.lower() for suffix in ['id', 'key', '_fk']):
                        if actual_col_name.lower() not in ['id', 'factid', 'rowid']:
                            fk_columns.append(actual_col_name)
                continue  # Skip to next col, don't process 'columns' as a column name

            # Skip object_type metadata
            if col_name == 'object_type':
                continue

            # Normal case: col_type is a string
            if not isinstance(col_type, str):
                col_type = str(col_type) if col_type else ''
            col_type = col_type.lower()

            # Identify numeric columns (metrics)
            if any(t in col_type for t in ['int', 'decimal', 'numeric', 'number', 'float', 'money']):
                numeric_columns.append(col_name)

            # Identify date columns
            if any(t in col_type for t in ['date', 'datetime', 'timestamp']):
                date_columns.append(col_name)

            # Identify FK columns
            if any(suffix in col_name.lower() for suffix in ['id', 'key', '_fk']):
                if col_name.lower() not in ['id', 'factid', 'rowid']:  # Exclude primary keys
                    fk_columns.append(col_name)

        print(f"Detected: {len(numeric_columns)} numeric, {len(date_columns)} date, {len(fk_columns)} FK columns")
        print(f"Numeric columns: {numeric_columns}")
        print(f"Date columns: {date_columns}")

        # SMART Column Categorization (do this BEFORE building suggestions)
        # Initialize empty lists
        amount_cols = []
        quantity_cols = []
        price_cols = []
        percentage_cols = []
        weight_cols = []
        additive_cols = []
        non_additive_cols = []
        calculated_cols = []

        if numeric_columns:
            # Enhanced column categorization with business context
            amount_cols = [c for c in numeric_columns if any(k in c.lower() for k in
                ['amount', 'total', 'sales', 'revenue', 'income', 'cost', 'expense', 'payment', 'charge', 'fee'])]
            quantity_cols = [c for c in numeric_columns if any(k in c.lower() for k in
                ['quantity', 'qty', 'count', 'units', 'volume', 'pieces'])]
            price_cols = [c for c in numeric_columns if any(k in c.lower() for k in
                ['price', 'unitprice', 'unit_price', 'rate'])]
            percentage_cols = [c for c in numeric_columns if any(k in c.lower() for k in
                ['percent', 'pct', 'rate', 'ratio', 'margin', 'discount'])]
            weight_cols = [c for c in numeric_columns if any(k in c.lower() for k in
                ['weight', 'wt', 'mass'])]

            # Identify additive vs non-additive metrics
            additive_cols = amount_cols + quantity_cols + weight_cols
            non_additive_cols = price_cols + percentage_cols

            # Detect calculated columns that might need ratio validation
            for col in numeric_columns:
                col_lower = col.lower()
                # Detect columns that are likely calculated (Net = Gross - Discount, etc.)
                if any(k in col_lower for k in ['net', 'gross', 'subtotal', 'tax']):
                    calculated_cols.append(col)

        # Build suggested pipeline
        suggested_checks = []

        # 1. ALWAYS include schema validation
        suggested_checks.append({
            "category": "Schema Validation",
            "pipeline_type": "schema",
            "checks": [
                "validate_schema_columns",
                "validate_schema_datatypes",
                "validate_schema_nullability"
            ],
            "reason": "Ensures table structure matches between SQL Server and Snowflake",
            "priority": "CRITICAL"
        })

        # 2. ALWAYS include basic DQ
        suggested_checks.append({
            "category": "Data Quality",
            "pipeline_type": "dq",
            "checks": [
                "validate_record_counts",
                "validate_nulls"
            ],
            "reason": "Validates row counts match and NULL patterns are consistent",
            "priority": "CRITICAL"
        })

        # 3. SMART Business Metrics (Deep Column Analysis)
        if numeric_columns:
            metric_examples = []
            business_rules = []

            # For additive metrics - SUM must match EXACTLY
            if additive_cols:
                metric_examples.extend([
                    f"SUM({col}) must match exactly (critical for financial accuracy)"
                    for col in additive_cols[:3]
                ])
                business_rules.append("Additive metrics (amounts, quantities) require exact sum matching")

            # For non-additive metrics - AVG should match
            if non_additive_cols:
                metric_examples.extend([
                    f"AVG({col}) should be consistent"
                    for col in non_additive_cols[:2]
                ])
                business_rules.append("Non-additive metrics (prices, percentages) use average validation")

            if calculated_cols:
                business_rules.append(f"Calculated columns detected: {', '.join(calculated_cols[:3])} - ratio validation recommended")

            suggested_checks.append({
                "category": "Business Metrics (Smart Analysis)",
                "pipeline_type": "business",
                "checks": [
                    "validate_metric_sums",  # CRITICAL for additive metrics
                    "validate_metric_averages",  # For non-additive metrics
                    "validate_ratios"  # For calculated/derived columns
                ],
                "applicable_columns": {
                    "additive_sum_columns": additive_cols,
                    "non_additive_avg_columns": non_additive_cols,
                    "calculated_ratio_columns": calculated_cols,
                    "all_numeric": numeric_columns
                },
                "reason": f"Smart analysis identified {len(additive_cols)} additive, {len(non_additive_cols)} non-additive metrics",
                "priority": "CRITICAL" if additive_cols else "HIGH",
                "examples": metric_examples,
                "business_rules": business_rules
            })

            # Statistical analysis (only if enough numeric columns)
            if len(numeric_columns) >= 3:
                suggested_checks.append({
                    "category": "Statistical Analysis",
                    "pipeline_type": "dq",
                    "checks": [
                        "validate_statistics",
                        "validate_distribution",
                        "validate_outliers"
                    ],
                    "applicable_columns": numeric_columns,
                    "reason": "Ensures statistical properties match (mean, stddev, distribution)",
                    "priority": "MEDIUM",
                    "examples": [
                        "Detect anomalies in value distributions",
                        "Identify outliers that may indicate data quality issues"
                    ]
                })

        # 4. Referential Integrity (if FK columns exist)
        if fk_columns or request.relationships:
            dimension_tables = [rel.get('dim_table') for rel in request.relationships if rel.get('dim_table')]
            print(f"[DEBUG] Found {len(request.relationships)} relationships")
            print(f"[DEBUG] Dimension tables: {dimension_tables}")

            suggested_checks.append({
                "category": "Referential Integrity",
                "pipeline_type": "ri",
                "checks": [
                    "validate_foreign_keys",
                    "validate_cross_system_fk_alignment"
                ],
                "applicable_columns": fk_columns,
                "related_dimensions": dimension_tables,
                "reason": f"Validates FK integrity to {len(dimension_tables)} dimension tables",
                "priority": "HIGH"
            })

            suggested_checks.append({
                "category": "Fact-Dimension Conformance",
                "pipeline_type": "business",
                "checks": [
                    "validate_fact_dim_conformance",
                    "validate_late_arriving_facts"
                ],
                "related_dimensions": dimension_tables,
                "reason": "Ensures all fact records have valid dimension references",
                "priority": "HIGH"
            })

        # 5. ENHANCED Time-Series & Temporal Aggregations (if date columns exist)
        if date_columns:
            primary_date = date_columns[0]  # Assume first date column is primary

            # Basic time-series validation
            suggested_checks.append({
                "category": "Time-Series Analysis",
                "pipeline_type": "timeseries",
                "checks": [
                    "validate_ts_continuity",
                    "validate_ts_duplicates",
                ],
                "applicable_columns": date_columns,
                "primary_date_column": primary_date,
                "reason": f"Validates temporal continuity and detects duplicates using {primary_date}",
                "priority": "MEDIUM"
            })

            # Period-over-Period comparisons (if numeric columns exist)
            if numeric_columns:
                suggested_checks.append({
                    "category": "Period-over-Period Analysis",
                    "pipeline_type": "timeseries",
                    "checks": [
                        "validate_period_over_period"
                    ],
                    "applicable_columns": date_columns,
                    "metric_columns": numeric_columns[:5],  # Top 5 numeric columns
                    "primary_date_column": primary_date,
                    "time_grains": ["WoW", "MoM", "YoY"],
                    "reason": "Compares Week-over-Week, Month-over-Month, Year-over-Year trends",
                    "priority": "MEDIUM",
                    "examples": [
                        f"Compare {metric} growth WoW/MoM/YoY" for metric in numeric_columns[:2]
                    ]
                })

                # Rolling Window Analysis
                suggested_checks.append({
                    "category": "Rolling Window Analysis",
                    "pipeline_type": "timeseries",
                    "checks": [
                        "validate_ts_rolling_drift"
                    ],
                    "applicable_columns": date_columns,
                    "metric_columns": numeric_columns[:5],
                    "primary_date_column": primary_date,
                    "rolling_windows": ["7-day", "30-day", "365-day (Rolling 12-month)"],
                    "reason": "Validates rolling averages to detect drift in metrics over time",
                    "priority": "LOW",
                    "examples": [
                        "7-day rolling average for daily metrics",
                        "30-day rolling average for monthly trends",
                        "365-day rolling average for year-over-year patterns"
                    ]
                })

                # Temporal Aggregations by Time Grain
                temporal_metric_cols = additive_cols if additive_cols else numeric_columns
                suggested_checks.append({
                    "category": "Temporal Aggregations",
                    "pipeline_type": "timeseries",
                    "checks": [
                        "validate_metric_sums",  # Aggregated to time grain
                        "validate_record_counts"  # Count by time grain
                    ],
                    "applicable_columns": date_columns,
                    "metric_columns": temporal_metric_cols,
                    "primary_date_column": primary_date,
                    "aggregation_grains": [
                        "Monthly (GROUP BY YEAR, MONTH)",
                        "Quarterly (GROUP BY YEAR, QUARTER)",
                        "Yearly (GROUP BY YEAR)",
                        "Rolling 12-Month"
                    ],
                    "reason": "Validates aggregated metrics at different time grains (monthly, quarterly, yearly, rolling 12-month)",
                    "priority": "HIGH",
                    "examples": [
                        f"Monthly SUM({col}) matches between systems" for col in temporal_metric_cols[:2]
                    ] + [
                        "Quarterly revenue totals reconcile",
                        "Yearly aggregations are consistent",
                        "Rolling 12-month metrics align"
                    ],
                    "business_rules": [
                        "Monthly: GROUP BY DATEPART(YEAR, date), DATEPART(MONTH, date)",
                        "Quarterly: GROUP BY DATEPART(YEAR, date), DATEPART(QUARTER, date)",
                        "Yearly: GROUP BY DATEPART(YEAR, date)",
                        "Rolling 12: SUM OVER (ORDER BY date ROWS BETWEEN 364 PRECEDING AND CURRENT ROW)"
                    ]
                })

        # Generate complete pipeline YAML
        pipeline_yaml = generate_fact_pipeline_yaml(
            request.fact_table,
            request.fact_schema,
            suggested_checks,
            numeric_columns,
            date_columns,
            request.relationships,
            request.columns,
            schema_mappings=request.schema_mappings
        )

        return {
            "status": "success",
            "fact_table": request.fact_table,
            "analysis": {
                "total_columns": len(request.columns),
                "numeric_columns": len(numeric_columns),
                "date_columns": len(date_columns),
                "fk_columns": len(fk_columns),
                "relationships": len(request.relationships)
            },
            "suggested_checks": suggested_checks,
            "pipeline_yaml": pipeline_yaml,
            "total_validations": sum(len(check.get("checks", [])) for check in suggested_checks)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to suggest validations: {str(e)}")


@router.post("/create-from-nl")
async def create_pipeline_from_natural_language(request: NaturalLanguagePipelineRequest):
    """
    Create a validation pipeline from natural language description

    Example inputs:
    - "Validate that total sales amount matches between SQL and Snowflake"
    - "Check for orphaned product IDs in the sales fact table"
    - "Ensure no gaps in daily sales data for 2024"
    - "Compare revenue, quantity, and tax totals"
    - "Verify all dimension references are valid"
    """
    try:
        # Parse natural language to extract intent
        description = request.description.lower()
        context = request.context or {}

        # Intent detection with enhanced patterns
        checks = []
        pipeline_type = "custom"
        matched_intents = []

        # === BUSINESS METRICS ===

        # Sum/Total/Revenue validation
        if any(word in description for word in [
            'sum', 'total', 'aggregate', 'revenue', 'sales amount',
            'grand total', 'cumulative', 'add up'
        ]):
            checks.append({
                "type": "business",
                "check": "validate_metric_sums",
                "reason": "Detected request for sum/total/revenue validation"
            })
            matched_intents.append("metric_sums")

        # Average/Mean validation
        if any(word in description for word in [
            'average', 'avg', 'mean', 'typical', 'median',
            'average price', 'average sales', 'mean value'
        ]):
            checks.append({
                "type": "business",
                "check": "validate_metric_averages",
                "reason": "Detected request for average/mean validation"
            })
            matched_intents.append("metric_averages")

        # Ratio/Percentage validation
        if any(word in description for word in [
            'ratio', 'percentage', 'pct', 'rate', 'proportion',
            'discount rate', 'margin', 'percentage of'
        ]):
            checks.append({
                "type": "business",
                "check": "validate_ratios",
                "reason": "Detected request for ratio/percentage validation"
            })
            matched_intents.append("ratios")

        # === REFERENTIAL INTEGRITY ===

        # Foreign key / orphaned records
        if any(word in description for word in [
            'orphan', 'foreign key', 'fk', 'reference', 'relationship',
            'orphaned records', 'missing references', 'invalid ids',
            'broken links', 'dangling references'
        ]):
            checks.extend([
                {
                    "type": "ri",
                    "check": "validate_foreign_keys",
                    "reason": "Detected request for foreign key validation"
                },
                {
                    "type": "business",
                    "check": "validate_fact_dim_conformance",
                    "reason": "Detected request for fact-dimension conformance"
                }
            ])
            matched_intents.append("foreign_keys")

        # Cross-system FK alignment
        if any(word in description for word in [
            'cross-system', 'alignment', 'fk match', 'reference consistency',
            'same violations', 'consistent references'
        ]):
            checks.append({
                "type": "ri",
                "check": "validate_cross_system_fk_alignment",
                "reason": "Detected request for cross-system FK alignment"
            })
            matched_intents.append("fk_alignment")

        # === DATA QUALITY ===

        # Record count
        if any(word in description for word in [
            'count', 'row count', 'records', 'number of rows',
            'total records', 'record match', 'same number'
        ]):
            checks.append({
                "type": "dq",
                "check": "validate_record_counts",
                "reason": "Detected request for row count validation"
            })
            matched_intents.append("record_counts")

        # Null/Missing values
        if any(word in description for word in [
            'null', 'empty', 'missing values', 'blank', 'not null',
            'null count', 'missing data', 'incomplete records'
        ]):
            checks.append({
                "type": "dq",
                "check": "validate_nulls",
                "reason": "Detected request for NULL validation"
            })
            matched_intents.append("nulls")

        # Uniqueness/Duplicates
        if any(word in description for word in [
            'unique', 'duplicate', 'distinct', 'uniqueness',
            'no duplicates', 'primary key', 'unique values'
        ]):
            checks.append({
                "type": "dq",
                "check": "validate_uniqueness",
                "reason": "Detected request for uniqueness validation"
            })
            matched_intents.append("uniqueness")

        # Domain values
        if any(word in description for word in [
            'domain', 'valid values', 'allowed values', 'range',
            'in range', 'value set', 'acceptable values'
        ]):
            checks.append({
                "type": "dq",
                "check": "validate_domain_values",
                "reason": "Detected request for domain value validation"
            })
            matched_intents.append("domain_values")

        # === STATISTICAL ANALYSIS ===

        # Distribution analysis
        if any(word in description for word in [
            'distribution', 'pattern', 'spread', 'histogram',
            'distribution match', 'same pattern', 'similar distribution'
        ]):
            checks.append({
                "type": "dq",
                "check": "validate_distribution",
                "reason": "Detected request for distribution analysis"
            })
            matched_intents.append("distribution")

        # Statistics (mean, stddev, etc.)
        if any(word in description for word in [
            'statistics', 'statistical', 'stddev', 'variance',
            'min', 'max', 'standard deviation', 'statistical properties'
        ]):
            checks.append({
                "type": "dq",
                "check": "validate_statistics",
                "reason": "Detected request for statistical validation"
            })
            matched_intents.append("statistics")

        # Outliers
        if any(word in description for word in [
            'outlier', 'anomaly', 'unusual', 'extreme values',
            'outlier detection', 'anomalous', 'suspicious values'
        ]):
            checks.append({
                "type": "dq",
                "check": "validate_outliers",
                "reason": "Detected request for outlier detection"
            })
            matched_intents.append("outliers")

        # === SCHEMA VALIDATION ===

        # Schema/Structure
        if any(word in description for word in [
            'schema', 'structure', 'table structure', 'column structure',
            'schema match', 'same structure'
        ]):
            checks.append({
                "type": "schema",
                "check": "validate_schema_columns",
                "reason": "Detected request for schema validation"
            })
            matched_intents.append("schema_columns")

        # Data types
        if any(word in description for word in [
            'data type', 'column type', 'type match', 'datatypes',
            'type compatibility', 'type conversion'
        ]):
            checks.append({
                "type": "schema",
                "check": "validate_schema_datatypes",
                "reason": "Detected request for data type validation"
            })
            matched_intents.append("schema_datatypes")

        # Nullability/Constraints
        if any(word in description for word in [
            'constraint', 'nullability', 'not null constraint',
            'primary key constraint', 'check constraint'
        ]):
            checks.append({
                "type": "schema",
                "check": "validate_schema_constraints",
                "reason": "Detected request for constraint validation"
            })
            matched_intents.append("schema_constraints")

        # === TIME-SERIES ===

        # Date gaps / continuity
        if any(word in description for word in [
            'gap', 'continuity', 'missing dates', 'daily', 'continuous',
            'date gap', 'missing days', 'complete date range',
            'no missing dates', 'all dates present'
        ]):
            checks.append({
                "type": "timeseries",
                "check": "validate_ts_continuity",
                "reason": "Detected request for date continuity validation"
            })
            matched_intents.append("ts_continuity")

        # Duplicate timestamps
        if any(word in description for word in [
            'duplicate date', 'duplicate timestamp', 'same date',
            'time duplicate', 'repeated dates'
        ]):
            checks.append({
                "type": "timeseries",
                "check": "validate_ts_duplicates",
                "reason": "Detected request for time-series duplicate detection"
            })
            matched_intents.append("ts_duplicates")

        # Period-over-period
        if any(word in description for word in [
            'period over period', 'month over month', 'year over year',
            'trend', 'compare periods', 'period comparison'
        ]):
            checks.append({
                "type": "timeseries",
                "check": "validate_period_over_period",
                "reason": "Detected request for period-over-period comparison"
            })
            matched_intents.append("period_over_period")

        # === DIMENSION SPECIFIC ===

        # SCD (Slowly Changing Dimensions)
        if any(word in description for word in [
            'scd', 'slowly changing', 'scd1', 'scd2',
            'dimension history', 'historical dimension'
        ]):
            if 'scd2' in description or 'type 2' in description:
                checks.append({
                    "type": "dimensions",
                    "check": "validate_scd2",
                    "reason": "Detected request for SCD Type 2 validation"
                })
                matched_intents.append("scd2")
            else:
                checks.append({
                    "type": "dimensions",
                    "check": "validate_scd1",
                    "reason": "Detected request for SCD Type 1 validation"
                })
                matched_intents.append("scd1")

        # Business keys
        if any(word in description for word in [
            'business key', 'natural key', 'bk', 'business identifier'
        ]):
            checks.append({
                "type": "dimensions",
                "check": "validate_dim_business_keys",
                "reason": "Detected request for business key validation"
            })
            matched_intents.append("business_keys")

        # === COMPREHENSIVE VALIDATIONS ===

        # "Complete" or "Full" validation
        if any(word in description for word in [
            'complete', 'full', 'comprehensive', 'all', 'everything',
            'thorough', 'end to end'
        ]):
            # Add core validations if not already present
            core_checks = [
                {"type": "schema", "check": "validate_schema_columns", "reason": "Complete validation: schema"},
                {"type": "dq", "check": "validate_record_counts", "reason": "Complete validation: row counts"},
                {"type": "business", "check": "validate_metric_sums", "reason": "Complete validation: metric sums"}
            ]
            for core_check in core_checks:
                if core_check["check"] not in [c["check"] for c in checks]:
                    checks.append(core_check)
            matched_intents.append("comprehensive")

        # Remove duplicates while preserving order
        seen = set()
        unique_checks = []
        for check in checks:
            check_id = (check["type"], check["check"])
            if check_id not in seen:
                seen.add(check_id)
                unique_checks.append(check)
        checks = unique_checks

        # Enhance with domain-specific patterns
        domain_match = None
        if DOMAIN_PATTERNS_AVAILABLE:
            domain_matches = match_domain_pattern(description)
            if domain_matches:
                domain_match = domain_matches[0]
                checks = enhance_nl_with_domain_patterns(description, checks)

        if not checks:
            # Provide intelligent suggestions based on partial matches
            suggestions = []
            if 'sales' in description or 'revenue' in description:
                suggestions.append("Validate total sales amount matches (try: 'validate total sales')")
            if 'product' in description or 'customer' in description:
                suggestions.append("Check for orphaned foreign keys (try: 'check for orphaned products')")
            if 'date' in description or 'time' in description:
                suggestions.append("Ensure no gaps in date series (try: 'no gaps in daily data')")
            if not suggestions:
                suggestions = [
                    "Validate total sales amount matches",
                    "Check for orphaned foreign keys",
                    "Ensure no gaps in date series",
                    "Validate row counts match",
                    "Compare statistics between systems"
                ]

            return {
                "status": "unclear",
                "message": "Could not understand the validation request. Please be more specific.",
                "suggestions": suggestions,
                "partial_match": len(matched_intents) > 0,
                "detected_keywords": matched_intents
            }

        # Generate pipeline YAML
        pipeline_yaml = generate_nl_pipeline_yaml(request.description, checks, context)

        response_data = {
            "status": "success",
            "description": request.description,
            "detected_intent": {
                "checks": checks,
                "count": len(checks),
                "matched_patterns": matched_intents
            },
            "pipeline_yaml": pipeline_yaml,
            "confidence": calculate_confidence(matched_intents),
            "next_steps": "Review and execute this pipeline"
        }

        # Add domain match information if available
        if domain_match:
            response_data["domain_match"] = {
                "domain": domain_match["domain"],
                "pattern": domain_match["pattern"],
                "reason": domain_match["reason"]
            }

        return response_data

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create pipeline from NL: {str(e)}")


def calculate_confidence(matched_intents: list) -> str:
    """Calculate confidence level based on number of matched intents"""
    if len(matched_intents) == 0:
        return "none"
    elif len(matched_intents) == 1:
        return "low"
    elif len(matched_intents) <= 3:
        return "medium"
    else:
        return "high"


def _build_table_mapping(fact_table: str, sql_schema: str, snow_schema: str,
                         relationships: List[Dict], reverse_mappings: Dict[str, str]) -> Dict:
    """Build the mapping section with correct SQL and Snowflake schema references.

    Relationships may contain dim_table names from either SQL or Snowflake side.
    We normalize: snow side uses Snowflake schema, sql side uses SQL schema.
    """
    mapping = {
        fact_table: {
            "sql": f"{sql_schema}.{fact_table}",
            "snow": f"{snow_schema}.{fact_table}"
        }
    }
    if not relationships:
        return mapping

    for rel in relationships:
        dim_table_ref = rel.get("dim_table", "")
        if not dim_table_ref or '.' not in dim_table_ref:
            continue
        dim_schema, dim_name = dim_table_ref.split('.', 1)

        # Determine SQL and Snowflake schema for this dim table
        if dim_schema in reverse_mappings:
            # dim_schema is a Snowflake schema (e.g., DIM) -> look up SQL schema
            snow_dim_schema = dim_schema
            sql_dim_schema = reverse_mappings[dim_schema]
        elif dim_schema in {v: k for k, v in reverse_mappings.items()}:
            # dim_schema is a SQL schema (e.g., SAMPLE_DIM) -> look up Snowflake schema
            sql_dim_schema = dim_schema
            snow_dim_schema = {v: k for k, v in reverse_mappings.items()}.get(dim_schema, dim_schema)
        else:
            # No mapping found, use same for both
            sql_dim_schema = dim_schema
            snow_dim_schema = dim_schema

        # Use dim_name (just the table) as the key, with proper schema for each side
        if dim_name not in mapping:
            mapping[dim_name] = {
                "sql": f"{sql_dim_schema}.{dim_name}",
                "snow": f"{snow_dim_schema}.{dim_name}"
            }
    return mapping


def generate_fact_pipeline_yaml(fact_table: str, schema: str, suggested_checks: List[Dict],
                                  numeric_cols: List[str], date_cols: List[str],
                                  relationships: List[Dict], columns: List[Dict],
                                  schema_mappings: Dict[str, str] = None) -> str:
    """Generate complete pipeline YAML for fact table.

    schema_mappings: SQL schema -> Snowflake schema (e.g., {"SAMPLE_DIM": "DIM", "SAMPLE_FACT": "FACT"})
    """

    # Build reverse mapping: Snowflake schema -> SQL schema
    reverse_mappings = {v: k for k, v in (schema_mappings or {}).items()}

    # Get default alert email from environment
    default_email = os.getenv("ALERT_EMAIL", "")
    email_list = [default_email] if default_email else []

    # Parse the fact_table parameter - it may contain schema.table format
    # e.g., "FACT.FACT_SALES" should be split into schema="FACT", table="FACT_SALES"
    if '.' in fact_table:
        parts = fact_table.split('.', 1)  # Split only on first dot
        parsed_schema = parts[0]
        parsed_table = parts[1]
        print(f"[PIPELINE_GEN] Parsed table name '{fact_table}' -> schema='{parsed_schema}', table='{parsed_table}'")

        # parsed_schema is the Snowflake schema (since we iterate over snow tables)
        snow_schema = parsed_schema
        # Look up SQL schema from reverse mapping, fallback to same
        sql_schema = reverse_mappings.get(parsed_schema, parsed_schema)
        fact_table = parsed_table  # Update fact_table to just the table name
        print(f"[PIPELINE_GEN] SQL schema='{sql_schema}', Snowflake schema='{snow_schema}'")
    else:
        # No dot in table name - use provided schema as-is
        snow_schema = schema
        sql_schema = reverse_mappings.get(schema, schema)

    pipeline = {
        "pipeline": {
            "name": f"{fact_table} Complete Validation Pipeline",
            "description": f"Auto-generated comprehensive validation for {fact_table}",
            "type": "fact_validation",
            "category": "auto_generated",
            "source": {
                "connection": "${SQLSERVER_CONNECTION}",
                "database": "${SQL_DATABASE}",
                "schema": sql_schema,
                "table": fact_table
            },
            "target": {
                "connection": "${SNOWFLAKE_CONNECTION}",
                "database": "${SNOWFLAKE_DATABASE}",
                "schema": snow_schema,
                "table": fact_table
            },
            "mapping": _build_table_mapping(
                fact_table, sql_schema, snow_schema,
                relationships, reverse_mappings
            ),
            "metadata": {
                fact_table: {
                    **_extract_metadata_structure(columns),
                    "foreign_keys": {
                        rel["dim_table"]: {
                            "column": rel["fk_column"],
                            "references": f"{rel['dim_table']}.{rel['dim_column']}"
                        }
                        for rel in relationships
                    } if relationships else {}
                },
                # Add dimension table metadata with business keys
                **({
                    rel["dim_table"]: {
                        "business_key": rel["dim_column"]
                    }
                    for rel in relationships
                } if relationships else {})
            },
            "steps": []
        },
        "execution": {
            "write_results_to": f"results/{fact_table.lower()}/",
            "fail_on_error": False,
            "notify": {
                "email": email_list,
                "slack": []
            }
        }
    }

    # Add steps from suggested checks - FLATTEN checks into individual steps
    for suggestion in suggested_checks:
        # Each check in the array becomes a separate step
        for check_name in suggestion["checks"]:
            # Build config based on validator requirements
            config = {
                "table": fact_table  # All validators need the table name
            }

            # Add validator-specific config
            if check_name in ["validate_metric_sums", "validate_metric_averages"]:
                config["metric_cols"] = numeric_cols
            elif check_name == "validate_ratios":
                # Generate ratio definitions from calculated columns
                config["ratio_defs"] = [
                    {"numerator": col, "denominator": numeric_cols[0]}
                    for col in numeric_cols[1:3] if len(numeric_cols) > 1
                ]
            elif check_name == "validate_ts_continuity":
                if date_cols:
                    config["date_col"] = date_cols[0]
            elif check_name == "validate_ts_duplicates":
                if date_cols:
                    config["keys"] = [date_cols[0]]  # Use date column as key
            elif check_name in ["validate_ts_rolling_drift", "validate_period_over_period"]:
                if date_cols and numeric_cols:
                    config["date_col"] = date_cols[0]
                    config["metric_col"] = numeric_cols[0]  # Add required metric_col
            elif check_name == "validate_foreign_keys":
                # Skip - requires specific FK relationships, not enough info
                continue
            elif check_name == "validate_cross_system_fk_alignment":
                # Skip - requires SQL and Snowflake result sets
                continue
            elif check_name in ["validate_fact_dim_conformance", "validate_late_arriving_facts"]:
                # These require fact and dim parameters - add all relationships
                print(f"[PIPELINE_GEN] Processing {check_name}, relationships count: {len(relationships)}")
                if relationships:
                    # Add one step per relationship
                    for rel in relationships:
                        dim_table = rel.get("dim_table") or rel.get("target_table", "unknown_dim")
                        print(f"[PIPELINE_GEN] Adding {check_name} step for {fact_table} -> {dim_table}")
                        rel_config = {
                            "table": fact_table,
                            "fact": fact_table,
                            "dim": dim_table
                        }
                        pipeline["pipeline"]["steps"].append({
                            "name": check_name,
                            "config": rel_config
                        })
                    # Continue to skip the default step addition below
                    continue
                else:
                    print(f"[PIPELINE_GEN] Skipping {check_name} - no relationships provided")
                    continue  # Skip if no relationships

            pipeline["pipeline"]["steps"].append({
                "name": check_name,
                "config": config
            })

    return format_yaml(pipeline)


def generate_nl_pipeline_yaml(description: str, checks: List[Dict], context: Dict) -> str:
    """Generate pipeline YAML from natural language intent"""

    # Get default alert email from environment
    default_email = os.getenv("ALERT_EMAIL", "")
    email_list = [default_email] if default_email else []

    # Group checks by type
    steps_by_type = {}
    for check in checks:
        check_type = check["type"]
        if check_type not in steps_by_type:
            steps_by_type[check_type] = []
        steps_by_type[check_type].append(check["check"])

    table_name = context.get("table", "unknown_table")
    sql_schema = context.get("sql_schema", "FACT")
    snow_schema = context.get("snow_schema", "FACT")

    pipeline = {
        "pipeline": {
            "name": "Natural Language Pipeline",
            "description": description,
            "type": "custom",
            "category": "user_defined",
            "source": {
                "connection": "${SQLSERVER_CONNECTION}",
                "database": context.get("sql_database", "${SQL_DATABASE}"),
                "schema": sql_schema,
                "table": table_name
            },
            "target": {
                "connection": "${SNOWFLAKE_CONNECTION}",
                "database": context.get("snow_database", "${SNOWFLAKE_DATABASE}"),
                "schema": snow_schema,
                "table": table_name
            },
            "mapping": {
                table_name: {
                    "sql": f"{sql_schema}.{table_name}",
                    "snow": f"{snow_schema}.{table_name}"
                }
            },
            "metadata": {
                table_name: {
                    "columns": context.get("columns", [])
                }
            },
            "steps": []
        },
        "execution": {
            "write_results_to": "results/nl_pipeline/",
            "fail_on_error": False,
            "notify": {
                "email": email_list,
                "slack": []
            }
        }
    }

    # Add steps - FLATTEN checks into individual steps
    for step_type, step_checks in steps_by_type.items():
        # Each check becomes a separate step
        for check_name in step_checks:
            # Build config with table name from context
            config = {
                "table": context.get("table", "unknown_table")
            }

            # Add validator-specific config if available in context
            if check_name in ["validate_metric_sums", "validate_metric_averages"] and "metric_cols" in context:
                config["metric_cols"] = context["metric_cols"]
            elif check_name == "validate_ratios" and "ratio_defs" in context:
                config["ratio_defs"] = context["ratio_defs"]
            elif check_name in ["validate_ts_continuity", "validate_ts_duplicates"] and "date_col" in context:
                config["date_col"] = context["date_col"]

            pipeline["pipeline"]["steps"].append({
                "name": check_name,
                "config": config
            })

    return format_yaml(pipeline)
