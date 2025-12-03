#!/usr/bin/env python3
"""Test the relationship-based workload generator"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(__file__))

from workload_generator import WorkloadGenerator

def main():
    print("Testing relationship-based workload generator...\n")

    # Create generator instance
    generator = WorkloadGenerator()

    # Test loading relationships
    print("=" * 60)
    print("Testing relationship loading:")
    print("=" * 60)
    relationships = generator._load_relationships()

    if relationships:
        print(f"\nFound {len(relationships)} fact table(s) with relationships:")
        for fact_table, rels in relationships.items():
            print(f"\n  {fact_table}:")
            for fk_col, rel_info in rels.items():
                print(f"    {fk_col} → {rel_info['dim_table']}.{rel_info['dim_column']} ({rel_info['confidence']})")
    else:
        print("\nNo relationships found!")

    # Generate workload
    print("\n" + "=" * 60)
    print("Testing workload generation:")
    print("=" * 60)

    queries = generator.generate_workload("Retail")

    print(f"\nGenerated {len(queries)} queries")

    # Show JOIN queries specifically
    join_queries = [q for q in queries if 'JOIN' in q['raw_text']]
    print(f"\nFound {len(join_queries)} JOIN queries:")
    for i, q in enumerate(join_queries, 1):
        print(f"\n{i}. Query ID {q['query_id']}:")
        print(f"   {q['raw_text'][:150]}{'...' if len(q['raw_text']) > 150 else ''}")

    print("\n" + "=" * 60)
    print("Test completed!")
    print("=" * 60)

if __name__ == "__main__":
    main()
