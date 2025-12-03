#!/usr/bin/env python3
"""Test the workload generator and show full JOIN queries"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(__file__))

from workload_generator import WorkloadGenerator

def main():
    print("Testing relationship-based workload generator - FULL OUTPUT\n")

    # Create generator instance
    generator = WorkloadGenerator()

    # Generate workload
    queries = generator.generate_workload("Retail")

    print(f"\nGenerated {len(queries)} queries total\n")
    print("=" * 80)

    # Show all JOIN queries with full SQL
    join_queries = [q for q in queries if 'JOIN' in q['raw_text']]
    print(f"\nJOIN Queries ({len(join_queries)} found):")
    print("=" * 80)

    for i, q in enumerate(join_queries, 1):
        print(f"\n{i}. Query ID {q['query_id']}:")
        print(f"   SQL: {q['raw_text']}")
        print()

if __name__ == "__main__":
    main()
