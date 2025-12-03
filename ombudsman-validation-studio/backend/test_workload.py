"""
Test script for Workload API endpoints
"""

import requests
import json
from pathlib import Path

# Configuration
API_BASE = "http://localhost:8000"
PROJECT_ID = "test_project"
SAMPLE_FILE = "data/sample_query_store_workload.json"

def test_upload_workload():
    """Test workload upload endpoint"""
    print("\n" + "="*60)
    print("TEST 1: Upload Workload")
    print("="*60)

    url = f"{API_BASE}/workload/upload"

    # Read sample file
    with open(SAMPLE_FILE, 'r') as f:
        sample_data = f.read()

    # Prepare multipart form data
    files = {
        'file': ('sample_query_store.json', sample_data, 'application/json')
    }
    data = {
        'project_id': PROJECT_ID
    }

    response = requests.post(url, files=files, data=data)

    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

    if response.status_code == 200:
        workload_id = response.json()['workload_id']
        print(f"\n✅ Upload successful! Workload ID: {workload_id}")
        return workload_id
    else:
        print(f"\n❌ Upload failed!")
        return None


def test_list_workloads():
    """Test list workloads endpoint"""
    print("\n" + "="*60)
    print("TEST 2: List Workloads")
    print("="*60)

    url = f"{API_BASE}/workload/list/{PROJECT_ID}"
    response = requests.get(url)

    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

    if response.status_code == 200:
        workloads = response.json()['workloads']
        print(f"\n✅ Found {len(workloads)} workload(s)")
        return workloads
    else:
        print(f"\n❌ List failed!")
        return []


def test_get_workload(workload_id):
    """Test get workload endpoint"""
    print("\n" + "="*60)
    print("TEST 3: Get Workload Details")
    print("="*60)

    url = f"{API_BASE}/workload/{PROJECT_ID}/{workload_id}"
    response = requests.get(url)

    print(f"Status Code: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"Workload ID: {data.get('workload_id')}")
        print(f"Query Count: {data.get('query_count')}")
        print(f"Total Executions: {data.get('total_executions')}")
        print(f"Tables Found: {len(data.get('table_usage', {}))}")
        print(f"Date Range: {data.get('date_range')}")
        print(f"\n✅ Get workload successful!")
        return data
    else:
        print(f"Response: {response.text}")
        print(f"\n❌ Get workload failed!")
        return None


def test_analyze_workload(workload_id):
    """Test analyze workload endpoint"""
    print("\n" + "="*60)
    print("TEST 4: Analyze Workload")
    print("="*60)

    url = f"{API_BASE}/workload/analyze"

    # Sample metadata
    metadata = {
        "fact.FACT_SALES": {
            "SALE_ID": "INT",
            "AMOUNT": "DECIMAL(12,2)",
            "QUANTITY": "INT",
            "CUSTOMER_KEY": "INT",
            "PRODUCT_KEY": "INT",
            "DATE_KEY": "INT",
            "STORE_KEY": "INT",
            "SALE_DATE": "DATE"
        },
        "dim.DIM_CUSTOMER": {
            "CUSTOMER_KEY": "INT",
            "CUSTOMER_NAME": "VARCHAR(100)",
            "EMAIL": "VARCHAR(100)",
            "CITY": "VARCHAR(50)",
            "STATE": "VARCHAR(2)",
            "ACTIVE_FLAG": "BIT"
        },
        "dim.DIM_DATE": {
            "DATE_KEY": "INT",
            "DATE_FULL": "DATE",
            "YEAR": "INT",
            "MONTH": "INT",
            "DAY": "INT",
            "QUARTER": "INT"
        },
        "dim.DIM_PRODUCT": {
            "PRODUCT_KEY": "INT",
            "PRODUCT_NAME": "VARCHAR(100)",
            "CATEGORY": "VARCHAR(50)",
            "SUBCATEGORY": "VARCHAR(50)",
            "UNIT_PRICE": "DECIMAL(10,2)",
            "ACTIVE_FLAG": "BIT"
        },
        "dim.DIM_STORE": {
            "STORE_KEY": "INT",
            "STORE_NAME": "VARCHAR(100)",
            "REGION": "VARCHAR(50)",
            "ACTIVE_FLAG": "BIT"
        }
    }

    payload = {
        "workload_id": workload_id,
        "project_id": PROJECT_ID,
        "metadata": metadata
    }

    response = requests.post(url, json=payload)

    print(f"Status Code: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"\nAnalysis Results:")
        print(f"  Tables Analyzed: {len(data.get('tables', {}))}")
        print(f"  Total Suggestions: {data.get('total_suggestions', 0)}")

        # Coverage metrics
        coverage = data.get('coverage', {})
        print(f"\nCoverage Metrics:")
        print(f"  Total Queries: {coverage.get('total_queries', 0)}")
        print(f"  Queries Covered: {coverage.get('queries_covered', 0)}")
        print(f"  Coverage %: {coverage.get('coverage_percentage', 0):.1f}%")
        print(f"  High Confidence: {coverage.get('high_confidence_count', 0)}")
        print(f"  Medium Confidence: {coverage.get('medium_confidence_count', 0)}")
        print(f"  Low Confidence: {coverage.get('low_confidence_count', 0)}")

        # Category breakdown
        categories = data.get('categories', {})
        print(f"\nValidation Categories:")
        for category, count in categories.items():
            print(f"  {category}: {count}")

        # Table details (first 2 tables)
        print(f"\nTable Analysis (sample):")
        for i, (table_name, table_data) in enumerate(list(data.get('tables', {}).items())[:2]):
            print(f"\n  Table: {table_name}")
            print(f"    Suggestions: {len(table_data.get('suggestions', []))}")
            print(f"    Access Count: {table_data.get('access_count', 0)}")

            # Show first 3 suggestions
            for j, suggestion in enumerate(table_data.get('suggestions', [])[:3]):
                print(f"\n    Suggestion {j+1}:")
                print(f"      Validator: {suggestion.get('validator_name')}")
                print(f"      Confidence: {suggestion.get('confidence', 0):.2f}")
                print(f"      Reason: {suggestion.get('reason', '')[:80]}...")

        print(f"\n✅ Analysis successful!")
        return data
    else:
        print(f"Response: {response.text}")
        print(f"\n❌ Analysis failed!")
        return None


def test_get_coverage(workload_id):
    """Test get coverage endpoint"""
    print("\n" + "="*60)
    print("TEST 5: Get Coverage Metrics")
    print("="*60)

    url = f"{API_BASE}/workload/coverage/{PROJECT_ID}/{workload_id}"
    response = requests.get(url)

    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

    if response.status_code == 200:
        print(f"\n✅ Get coverage successful!")
        return response.json()
    else:
        print(f"\n❌ Get coverage failed!")
        return None


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("WORKLOAD API ENDPOINT TESTS")
    print("="*60)

    # Test 1: Upload
    workload_id = test_upload_workload()
    if not workload_id:
        print("\n❌ Cannot proceed without successful upload!")
        return

    # Test 2: List
    workloads = test_list_workloads()

    # Test 3: Get
    workload_data = test_get_workload(workload_id)

    # Test 4: Analyze
    analysis = test_analyze_workload(workload_id)

    # Test 5: Coverage
    coverage = test_get_coverage(workload_id)

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"✅ Upload: {'PASS' if workload_id else 'FAIL'}")
    print(f"✅ List: {'PASS' if workloads else 'FAIL'}")
    print(f"✅ Get: {'PASS' if workload_data else 'FAIL'}")
    print(f"✅ Analyze: {'PASS' if analysis else 'FAIL'}")
    print(f"✅ Coverage: {'PASS' if coverage else 'FAIL'}")
    print("="*60)


if __name__ == "__main__":
    main()
