# src/ombudsman/validation/business/query_loader.py
'''
Helper module to load custom query definitions from YAML files.
'''

import yaml
import os
from pathlib import Path

def load_queries_from_yaml(yaml_path):
    """
    Load custom query definitions from a YAML file.

    Args:
        yaml_path: Path to YAML file containing query definitions

    Returns:
        List of query definition dictionaries
    """
    if not os.path.exists(yaml_path):
        raise FileNotFoundError(f"Query definition file not found: {yaml_path}")

    with open(yaml_path, 'r') as f:
        queries = yaml.safe_load(f)

    if not queries:
        return []

    # Validate query format
    validated_queries = []
    for i, query in enumerate(queries):
        if not isinstance(query, dict):
            print(f"Warning: Skipping invalid query at index {i} - not a dictionary")
            continue

        if 'name' not in query:
            print(f"Warning: Skipping query at index {i} - missing 'name' field")
            continue

        if 'sql_query' not in query or 'snow_query' not in query:
            print(f"Warning: Skipping query '{query.get('name')}' - missing sql_query or snow_query")
            continue

        # Set defaults
        query.setdefault('comparison_type', 'aggregation')
        query.setdefault('tolerance', 0.01)
        query.setdefault('limit', 100)

        validated_queries.append(query)

    return validated_queries


def load_user_queries(config_dir=None):
    """
    Load user-defined queries from the default config directory.

    Args:
        config_dir: Optional custom config directory path

    Returns:
        List of query definition dictionaries
    """
    if config_dir is None:
        # Default to ombudsman/config directory
        current_dir = Path(__file__).parent.parent.parent
        config_dir = current_dir / 'config'

    yaml_path = Path(config_dir) / 'custom_queries.yaml'

    if not yaml_path.exists():
        print(f"No custom queries file found at {yaml_path}")
        return []

    return load_queries_from_yaml(str(yaml_path))


def load_example_queries(config_dir=None):
    """
    Load example query templates.

    Args:
        config_dir: Optional custom config directory path

    Returns:
        List of query definition dictionaries
    """
    if config_dir is None:
        # Default to ombudsman/config directory
        current_dir = Path(__file__).parent.parent.parent
        config_dir = current_dir / 'config'

    yaml_path = Path(config_dir) / 'custom_query_examples.yaml'

    if not yaml_path.exists():
        print(f"No example queries file found at {yaml_path}")
        return []

    return load_queries_from_yaml(str(yaml_path))


def get_query_suggestions():
    """
    Returns a list of query pattern suggestions for users.
    """
    return {
        "aggregation_patterns": [
            "Total revenue by product category",
            "Customer count by region",
            "Average order value by month",
            "Sum of quantities by product",
        ],
        "date_patterns": [
            "Monthly sales summary for a year",
            "Quarterly performance comparison",
            "Weekly trends with moving averages",
            "Year-over-year growth analysis",
        ],
        "top_n_patterns": [
            "Top 5 customers by revenue",
            "Top 10 products by quantity sold",
            "Top 20 performers with rankings",
        ],
        "join_patterns": [
            "Sales with customer and product dimensions",
            "Orders with date dimension filtering",
            "Multi-table joins with region and category",
        ],
        "filter_patterns": [
            "Specific customer transaction history",
            "Regional sales for specific quarters",
            "Active customers in last N days",
        ],
        "advanced_patterns": [
            "Random sample validation",
            "Customer cohort segmentation",
            "Window functions with rankings",
        ]
    }
