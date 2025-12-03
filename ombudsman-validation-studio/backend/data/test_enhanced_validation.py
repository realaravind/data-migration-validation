#!/usr/bin/env python3
"""Test enhanced error messages in validate_custom_sql"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from connections.database import get_sql_server_connection, get_snowflake_connection
from validation.validate_custom_sql import validate_custom_sql

def test_row_order_detection():
    """Test that row order mismatches are properly detected and explained"""
    print("=" * 80)
    print("TEST 1: Row Order Mismatch Detection")
    print("=" * 80)

    sql_conn = get_sql_server_connection()
    snow_conn = get_snowflake_connection()

    # Query without ORDER BY - should detect row order mismatch
    result = validate_custom_sql(
        sql_conn=sql_conn,
        snow_conn=snow_conn,
        sql_server_query="SELECT * FROM DIM.dim_product WHERE category = 'Electronics'",
        snowflake_query="SELECT * FROM DIM.DIM_PRODUCT WHERE category = 'Electronics'",
        compare_mode="result_set",
        tolerance=0.0,
        ignore_column_order=True,
        ignore_row_order=False  # Intentionally false
    )

    print(f"\nStatus: {result['status']}")
    print(f"Message:\n{result['message']}")
    print(f"\nSQL Row Count: {result.get('sql_row_count', 'N/A')}")
    print(f"Snowflake Row Count: {result.get('snow_row_count', 'N/A')}")

    sql_conn.close()
    snow_conn.close()

    return result

def test_actual_data_difference():
    """Test detection of actual data differences with detailed breakdown"""
    print("\n" + "=" * 80)
    print("TEST 2: Actual Data Difference Detection")
    print("=" * 80)

    sql_conn = get_sql_server_connection()
    snow_conn = get_snowflake_connection()

    # Query with ORDER BY to compare ordered results
    # If data matches, this should pass
    result = validate_custom_sql(
        sql_conn=sql_conn,
        snow_conn=snow_conn,
        sql_server_query="SELECT product_key, product_id, product_name, unit_price FROM DIM.dim_product ORDER BY product_key",
        snowflake_query="SELECT product_key, product_id, product_name, unit_price FROM DIM.DIM_PRODUCT ORDER BY product_key",
        compare_mode="result_set",
        tolerance=0.0,
        ignore_column_order=True,
        ignore_row_order=False
    )

    print(f"\nStatus: {result['status']}")
    print(f"Message:\n{result['message']}")
    print(f"\nSQL Row Count: {result.get('sql_row_count', 'N/A')}")
    print(f"Snowflake Row Count: {result.get('snow_row_count', 'N/A')}")

    sql_conn.close()
    snow_conn.close()

    return result

if __name__ == "__main__":
    try:
        # Test 1: Row order mismatch
        test1_result = test_row_order_detection()

        # Test 2: Actual data comparison
        test2_result = test_actual_data_difference()

        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"Test 1 (Row Order): {test1_result['status']}")
        print(f"Test 2 (Data Comparison): {test2_result['status']}")

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
