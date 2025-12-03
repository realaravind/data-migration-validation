#!/usr/bin/env python3
"""
Example usage of the custom business query validator.
This demonstrates how to use the validator with your own queries.
"""

from ombudsman.validation.business import (
    validate_custom_queries,
    load_user_queries,
    load_example_queries,
    get_query_suggestions
)

def example_basic_usage(sql_conn, snow_conn):
    """
    Example 1: Basic usage with manually defined queries
    """
    print("=" * 60)
    print("Example 1: Basic Usage - Manually Defined Query")
    print("=" * 60)

    # Define a simple query
    queries = [{
        "name": "Total Sales Count",
        "comparison_type": "count",
        "sql_query": "SELECT COUNT(*) as count FROM fact.Sales",
        "snow_query": "SELECT COUNT(*) as count FROM FACT.SALES"
    }]

    # Run validation
    result = validate_custom_queries(sql_conn, snow_conn, queries, mapping={})

    # Display results
    print(f"Status: {result['status']}")
    print(f"Severity: {result['severity']}")

    if result['status'] == 'PASS':
        print("✓ Query validation passed!")
    else:
        print(f"✗ Found {len(result['issues'])} issues")
        for issue in result['issues']:
            print(f"  - {issue}")

    # Always show explain data
    for query_name, explain in result['explain'].items():
        print(f"\nQuery: {query_name}")
        print(f"Interpretation: {explain['interpretation']}")
        print(f"Execution times: SQL={explain['sql_execution_time']}s, Snow={explain['snow_execution_time']}s")


def example_load_from_yaml(sql_conn, snow_conn):
    """
    Example 2: Load queries from YAML configuration
    """
    print("\n" + "=" * 60)
    print("Example 2: Load from YAML Config")
    print("=" * 60)

    # Load user-defined queries
    queries = load_user_queries()

    if not queries:
        print("No custom queries found in config/custom_queries.yaml")
        return

    print(f"Loaded {len(queries)} queries from config")

    # Run validation
    result = validate_custom_queries(sql_conn, snow_conn, queries, mapping={})

    # Display summary
    print(f"\nResults: {result['status']}")
    print(f"Total queries: {len(result['details'])}")
    print(f"Passed: {sum(1 for d in result['details'] if d['match'])}")
    print(f"Failed: {len(result['issues'])}")


def example_complex_query(sql_conn, snow_conn):
    """
    Example 3: Complex multi-table join query
    """
    print("\n" + "=" * 60)
    print("Example 3: Complex Multi-Table Join")
    print("=" * 60)

    queries = [{
        "name": "Monthly Revenue by Product Category",
        "comparison_type": "rowset",
        "tolerance": 0.01,
        "limit": 12,
        "sql_query": """
            SELECT
                d.Month,
                d.MonthName,
                p.Category,
                SUM(s.Amount) as TotalRevenue,
                COUNT(*) as OrderCount
            FROM fact.Sales s
            INNER JOIN dim.Product p ON s.ProductID = p.ProductID
            INNER JOIN dim.Date d ON s.OrderDate = d.Date
            WHERE d.Year = 2024
            GROUP BY d.Month, d.MonthName, p.Category
            ORDER BY d.Month, TotalRevenue DESC
        """,
        "snow_query": """
            SELECT
                d.Month,
                d.MonthName,
                p.Category,
                SUM(s.Amount) as TotalRevenue,
                COUNT(*) as OrderCount
            FROM FACT.SALES s
            INNER JOIN DIM.PRODUCT p ON s.ProductID = p.ProductID
            INNER JOIN DIM.DATE d ON s.OrderDate = d.Date
            WHERE d.Year = 2024
            GROUP BY d.Month, d.MonthName, p.Category
            ORDER BY d.Month, TotalRevenue DESC
        """
    }]

    result = validate_custom_queries(sql_conn, snow_conn, queries, mapping={})

    print(f"Status: {result['status']}")

    # Show explain data
    for query_name, explain in result['explain'].items():
        print(f"\nQuery: {query_name}")
        print(f"Interpretation: {explain['interpretation']}")
        print(f"SQL rows: {explain['sql_row_count']}")
        print(f"Snowflake rows: {explain['snow_row_count']}")

        if explain.get('sql_sample_results'):
            print("\nSample results (first 3):")
            for i, row in enumerate(explain['sql_sample_results'][:3]):
                print(f"  Row {i+1}: {row}")


def example_suggestions():
    """
    Example 4: Get query pattern suggestions
    """
    print("\n" + "=" * 60)
    print("Example 4: Query Pattern Suggestions")
    print("=" * 60)

    suggestions = get_query_suggestions()

    for category, patterns in suggestions.items():
        print(f"\n{category.replace('_', ' ').title()}:")
        for pattern in patterns:
            print(f"  • {pattern}")


def example_load_examples():
    """
    Example 5: Load and browse example queries
    """
    print("\n" + "=" * 60)
    print("Example 5: Browse Example Query Templates")
    print("=" * 60)

    examples = load_example_queries()

    if not examples:
        print("No examples found")
        return

    print(f"Found {len(examples)} example queries:\n")

    for i, query in enumerate(examples[:5], 1):  # Show first 5
        print(f"{i}. {query['name']}")
        print(f"   Type: {query['comparison_type']}")
        print(f"   SQL Preview: {query['sql_query'][:100]}...")
        print()


if __name__ == "__main__":
    print("Custom Business Query Validator - Usage Examples")
    print("=" * 60)
    print()
    print("This script demonstrates how to use the custom query validator.")
    print("You'll need to provide actual database connections to run validations.")
    print()

    # Show suggestions (doesn't need DB connection)
    example_suggestions()

    # Show examples (doesn't need DB connection)
    example_load_examples()

    print("\n" + "=" * 60)
    print("To run actual validations:")
    print("=" * 60)
    print("""
    from ombudsman.core.connections import SQLServerConnection, SnowflakeConnection

    # Set up connections
    sql_conn = SQLServerConnection(...)
    snow_conn = SnowflakeConnection(...)

    # Run examples
    example_basic_usage(sql_conn, snow_conn)
    example_load_from_yaml(sql_conn, snow_conn)
    example_complex_query(sql_conn, snow_conn)
    """)
