"""
Domain-Specific Natural Language Patterns
Extends intelligent_suggest.py with industry-specific validation patterns
"""

from typing import List, Dict

# ========================================
# FINANCE & BANKING DOMAIN
# ========================================

FINANCE_PATTERNS = {
    "revenue_reconciliation": {
        "keywords": [
            "revenue reconciliation", "revenue rec", "rec revenue",
            "sales reconciliation", "ar reconciliation"
        ],
        "checks": [
            {"type": "business", "check": "validate_metric_sums", "columns": ["revenue", "sales", "amount"]},
            {"type": "dq", "check": "validate_record_counts"},
            {"type": "business", "check": "validate_metric_averages"},
            {"type": "dq", "check": "validate_nulls"}
        ],
        "reason": "Financial revenue reconciliation requires exact sum matches and row counts"
    },

    "gl_posting": {
        "keywords": [
            "general ledger", "gl posting", "journal entry",
            "accounting entry", "ledger reconciliation"
        ],
        "checks": [
            {"type": "business", "check": "validate_metric_sums", "columns": ["debit", "credit", "amount"]},
            {"type": "dq", "check": "validate_record_counts"},
            {"type": "business", "check": "validate_ratios"},  # Debit=Credit balance
            {"type": "timeseries", "check": "validate_ts_continuity"}  # Posting dates
        ],
        "reason": "GL postings must have balanced debits/credits and continuous posting dates"
    },

    "payment_validation": {
        "keywords": [
            "payment validation", "payment reconciliation",
            "transaction validation", "payment processing"
        ],
        "checks": [
            {"type": "business", "check": "validate_metric_sums", "columns": ["payment_amount", "transaction_amount"]},
            {"type": "dq", "check": "validate_record_counts"},
            {"type": "ri", "check": "validate_foreign_keys"},  # Customer/Account FKs
            {"type": "dq", "check": "validate_domain_values"}  # Payment status values
        ],
        "reason": "Payment processing requires exact amounts and valid references"
    },

    "balance_sheet": {
        "keywords": [
            "balance sheet", "assets liabilities", "financial position",
            "balance reconciliation"
        ],
        "checks": [
            {"type": "business", "check": "validate_metric_sums", "columns": ["assets", "liabilities", "equity"]},
            {"type": "business", "check": "validate_ratios"},  # Assets = Liabilities + Equity
            {"type": "dq", "check": "validate_statistics"}
        ],
        "reason": "Balance sheet must balance: Assets = Liabilities + Equity"
    }
}


# ========================================
# RETAIL & E-COMMERCE DOMAIN
# ========================================

RETAIL_PATTERNS = {
    "sales_reconciliation": {
        "keywords": [
            "sales reconciliation", "pos reconciliation",
            "retail sales", "transaction reconciliation"
        ],
        "checks": [
            {"type": "business", "check": "validate_metric_sums", "columns": ["sales_amount", "quantity", "tax"]},
            {"type": "dq", "check": "validate_record_counts"},
            {"type": "timeseries", "check": "validate_ts_continuity"},  # Daily sales
            {"type": "ri", "check": "validate_foreign_keys"}  # Product/Store FKs
        ],
        "reason": "Retail sales require daily continuity and product/store references"
    },

    "inventory_validation": {
        "keywords": [
            "inventory validation", "stock reconciliation",
            "inventory count", "warehouse validation"
        ],
        "checks": [
            {"type": "business", "check": "validate_metric_sums", "columns": ["quantity", "on_hand", "available"]},
            {"type": "dq", "check": "validate_record_counts"},
            {"type": "ri", "check": "validate_foreign_keys"},  # Product/Location FKs
            {"type": "dq", "check": "validate_domain_values"}  # Status values
        ],
        "reason": "Inventory requires exact quantity matches and valid product references"
    },

    "order_fulfillment": {
        "keywords": [
            "order fulfillment", "order validation",
            "fulfillment reconciliation", "order processing"
        ],
        "checks": [
            {"type": "dq", "check": "validate_record_counts"},
            {"type": "business", "check": "validate_fact_dim_conformance"},  # Order→Customer
            {"type": "ri", "check": "validate_foreign_keys"},
            {"type": "timeseries", "check": "validate_late_arriving_facts"}  # Late orders
        ],
        "reason": "Order fulfillment requires valid customer references and temporal checks"
    },

    "pricing_validation": {
        "keywords": [
            "pricing validation", "price check",
            "promotion validation", "discount validation"
        ],
        "checks": [
            {"type": "business", "check": "validate_metric_averages", "columns": ["price", "unit_price"]},
            {"type": "business", "check": "validate_ratios"},  # Discount/Price ratios
            {"type": "dq", "check": "validate_outliers"},  # Unusual prices
            {"type": "dq", "check": "validate_domain_values"}  # Price ranges
        ],
        "reason": "Pricing validation checks average prices, discount ratios, and outliers"
    }
}


# ========================================
# HEALTHCARE DOMAIN
# ========================================

HEALTHCARE_PATTERNS = {
    "patient_encounter": {
        "keywords": [
            "patient encounter", "visit validation",
            "encounter reconciliation", "patient visit"
        ],
        "checks": [
            {"type": "dq", "check": "validate_record_counts"},
            {"type": "ri", "check": "validate_foreign_keys"},  # Patient/Provider FKs
            {"type": "timeseries", "check": "validate_ts_continuity"},  # Encounter dates
            {"type": "business", "check": "validate_fact_dim_conformance"}
        ],
        "reason": "Patient encounters require valid patient/provider references and date continuity"
    },

    "claims_processing": {
        "keywords": [
            "claims processing", "insurance claims",
            "claims reconciliation", "medical claims"
        ],
        "checks": [
            {"type": "business", "check": "validate_metric_sums", "columns": ["claim_amount", "paid_amount"]},
            {"type": "dq", "check": "validate_record_counts"},
            {"type": "ri", "check": "validate_foreign_keys"},  # Patient/Provider/Payer FKs
            {"type": "dq", "check": "validate_domain_values"}  # Claim status
        ],
        "reason": "Claims require exact amount matches and valid references"
    },

    "lab_results": {
        "keywords": [
            "lab results", "laboratory validation",
            "test results", "lab reconciliation"
        ],
        "checks": [
            {"type": "dq", "check": "validate_record_counts"},
            {"type": "ri", "check": "validate_foreign_keys"},  # Patient/Order FKs
            {"type": "dq", "check": "validate_nulls"},  # Critical results
            {"type": "dq", "check": "validate_domain_values"}  # Result ranges
        ],
        "reason": "Lab results require complete data and valid patient references"
    }
}


# ========================================
# MANUFACTURING DOMAIN
# ========================================

MANUFACTURING_PATTERNS = {
    "production_validation": {
        "keywords": [
            "production validation", "manufacturing reconciliation",
            "production output", "work order validation"
        ],
        "checks": [
            {"type": "business", "check": "validate_metric_sums", "columns": ["quantity_produced", "output"]},
            {"type": "dq", "check": "validate_record_counts"},
            {"type": "ri", "check": "validate_foreign_keys"},  # Product/Line FKs
            {"type": "timeseries", "check": "validate_ts_continuity"}  # Production dates
        ],
        "reason": "Production requires exact output quantities and continuous date tracking"
    },

    "quality_control": {
        "keywords": [
            "quality control", "qc validation",
            "inspection validation", "defect tracking"
        ],
        "checks": [
            {"type": "business", "check": "validate_metric_sums", "columns": ["defects", "passed", "failed"]},
            {"type": "business", "check": "validate_ratios"},  # Defect rates
            {"type": "dq", "check": "validate_record_counts"},
            {"type": "dq", "check": "validate_outliers"}  # Unusual defect rates
        ],
        "reason": "QC validation checks defect counts, pass rates, and outliers"
    },

    "material_consumption": {
        "keywords": [
            "material consumption", "raw material",
            "bom validation", "material usage"
        ],
        "checks": [
            {"type": "business", "check": "validate_metric_sums", "columns": ["quantity_used", "consumed"]},
            {"type": "ri", "check": "validate_foreign_keys"},  # Material/Product FKs
            {"type": "business", "check": "validate_ratios"},  # Consumption ratios
            {"type": "dq", "check": "validate_statistics"}
        ],
        "reason": "Material consumption requires exact quantities and valid material references"
    }
}


# ========================================
# TELECOM DOMAIN
# ========================================

TELECOM_PATTERNS = {
    "call_detail_records": {
        "keywords": [
            "cdr validation", "call detail records",
            "call reconciliation", "usage validation"
        ],
        "checks": [
            {"type": "dq", "check": "validate_record_counts"},
            {"type": "business", "check": "validate_metric_sums", "columns": ["duration", "cost"]},
            {"type": "timeseries", "check": "validate_ts_continuity"},
            {"type": "ri", "check": "validate_foreign_keys"}  # Subscriber FKs
        ],
        "reason": "CDR validation requires exact record counts and duration totals"
    },

    "billing_validation": {
        "keywords": [
            "billing validation", "telecom billing",
            "subscriber billing", "invoice reconciliation"
        ],
        "checks": [
            {"type": "business", "check": "validate_metric_sums", "columns": ["charges", "amount"]},
            {"type": "dq", "check": "validate_record_counts"},
            {"type": "ri", "check": "validate_foreign_keys"},  # Account/Plan FKs
            {"type": "dq", "check": "validate_nulls"}
        ],
        "reason": "Billing requires exact charge totals and valid account references"
    },

    "network_performance": {
        "keywords": [
            "network performance", "kpi validation",
            "service quality", "network metrics"
        ],
        "checks": [
            {"type": "business", "check": "validate_metric_averages", "columns": ["latency", "throughput"]},
            {"type": "dq", "check": "validate_statistics"},
            {"type": "dq", "check": "validate_outliers"},
            {"type": "timeseries", "check": "validate_period_over_period"}
        ],
        "reason": "Network metrics require statistical analysis and trend tracking"
    }
}


# ========================================
# DOMAIN PATTERN MATCHER
# ========================================

def match_domain_pattern(description: str) -> List[Dict]:
    """
    Match natural language description against domain-specific patterns

    Args:
        description: User's natural language input

    Returns:
        List of matched domain patterns with suggested checks
    """
    description_lower = description.lower()
    matched_patterns = []

    all_domains = {
        "Finance & Banking": FINANCE_PATTERNS,
        "Retail & E-Commerce": RETAIL_PATTERNS,
        "Healthcare": HEALTHCARE_PATTERNS,
        "Manufacturing": MANUFACTURING_PATTERNS,
        "Telecom": TELECOM_PATTERNS
    }

    for domain_name, patterns in all_domains.items():
        for pattern_name, pattern_config in patterns.items():
            # Check if any keyword matches
            for keyword in pattern_config["keywords"]:
                if keyword in description_lower:
                    matched_patterns.append({
                        "domain": domain_name,
                        "pattern": pattern_name,
                        "checks": pattern_config["checks"],
                        "reason": pattern_config["reason"],
                        "confidence": "high"
                    })
                    break  # Only match once per pattern

    return matched_patterns


def enhance_nl_with_domain_patterns(description: str, base_checks: List[Dict]) -> List[Dict]:
    """
    Enhance base NL detection with domain-specific patterns

    Args:
        description: User's natural language input
        base_checks: Checks detected by base NL parser

    Returns:
        Enhanced list of checks combining base + domain-specific
    """
    domain_matches = match_domain_pattern(description)

    if not domain_matches:
        return base_checks

    # Get best domain match (first one found)
    best_match = domain_matches[0]
    domain_checks = best_match["checks"]

    # Merge with base checks, removing duplicates
    all_checks = base_checks.copy()

    for domain_check in domain_checks:
        check_id = (domain_check["type"], domain_check["check"])
        base_check_ids = [(c["type"], c["check"]) for c in all_checks]

        if check_id not in base_check_ids:
            all_checks.append({
                "type": domain_check["type"],
                "check": domain_check["check"],
                "reason": f"Domain pattern: {best_match['reason']}"
            })

    return all_checks


# ========================================
# EXAMPLE USAGE
# ========================================

if __name__ == "__main__":
    # Test domain pattern matching
    test_cases = [
        "Revenue reconciliation for Q4 2024",
        "Validate retail sales data",
        "Patient encounter validation",
        "Production output reconciliation",
        "CDR validation for telecom"
    ]

    for test in test_cases:
        matches = match_domain_pattern(test)
        print(f"\nInput: {test}")
        if matches:
            match = matches[0]
            print(f"  Domain: {match['domain']}")
            print(f"  Pattern: {match['pattern']}")
            print(f"  Checks: {len(match['checks'])}")
        else:
            print("  No domain pattern matched")
