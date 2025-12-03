import yaml
import os
from difflib import SequenceMatcher


def load_mapping(tables_metadata):
    """Legacy function for loading mapping from YAML files."""
    mapping_file = "ombudsman/config/mapping.yaml"
    override = {}

    if os.path.exists(mapping_file):
        override = yaml.safe_load(open(mapping_file))

    final = {}

    for logical_name, meta in tables_metadata.items():
        sql_name = meta.get("sql_name")
        snow_name = meta.get("snow_name")

        if logical_name in override:
            o = override[logical_name]
            sql_name = o.get("sql_name", sql_name)
            snow_name = o.get("snow_name", snow_name)

        final[logical_name] = {
            "sql": sql_name,
            "snow": snow_name
        }

    return final


class MappingLoader:
    """
    Generate column mappings between source and target tables.
    Uses fuzzy matching and data type compatibility.
    """

    def __init__(self):
        """Initialize MappingLoader."""
        self.type_compatibility = {
            # SQL Server to Snowflake type mappings
            "varchar": ["varchar", "string", "text"],
            "nvarchar": ["varchar", "string", "text"],
            "char": ["char", "varchar", "string"],
            "nchar": ["char", "varchar", "string"],
            "text": ["text", "string", "varchar"],
            "int": ["int", "integer", "number"],
            "bigint": ["bigint", "number", "integer"],
            "smallint": ["smallint", "int", "number"],
            "tinyint": ["tinyint", "int", "number"],
            "decimal": ["decimal", "number", "numeric"],
            "numeric": ["numeric", "number", "decimal"],
            "float": ["float", "double", "number"],
            "real": ["real", "float", "number"],
            "money": ["number", "decimal"],
            "datetime": ["datetime", "timestamp", "timestamp_ntz"],
            "datetime2": ["datetime", "timestamp", "timestamp_ntz"],
            "date": ["date"],
            "time": ["time"],
            "bit": ["boolean", "bit"],
            "uniqueidentifier": ["varchar", "string"],
        }

    def suggest_mapping(self, source_cols: list, target_cols: list) -> dict:
        """
        Suggest column mappings between source and target.

        Args:
            source_cols: List of source column dicts with 'name' and optionally 'data_type'
            target_cols: List of target column dicts with 'name' and optionally 'data_type'

        Returns:
            Dictionary with mapping suggestions
        """
        mappings = []
        unmatched_source = []
        unmatched_target = list(target_cols)

        for source_col in source_cols:
            source_name = source_col.get("name", source_col) if isinstance(source_col, dict) else source_col
            source_type = source_col.get("data_type", "").lower() if isinstance(source_col, dict) else ""

            # Find best match
            best_match = None
            best_score = 0.0

            for target_col in target_cols:
                target_name = target_col.get("name", target_col) if isinstance(target_col, dict) else target_col
                target_type = target_col.get("data_type", "").lower() if isinstance(target_col, dict) else ""

                # Calculate name similarity
                name_score = self._similarity(source_name, target_name)

                # Calculate type compatibility score
                type_score = self._type_compatibility_score(source_type, target_type)

                # Weighted total score (name is more important)
                total_score = (name_score * 0.7) + (type_score * 0.3)

                if total_score > best_score:
                    best_score = total_score
                    best_match = target_col

            # Accept match if score is above threshold
            if best_score > 0.5:  # 50% confidence threshold
                target_name = best_match.get("name", best_match) if isinstance(best_match, dict) else best_match
                mappings.append({
                    "source": source_name,
                    "target": target_name,
                    "confidence": round(best_score * 100, 2),
                    "auto_mapped": True,  # All mappings from this function are auto-generated
                    "is_exact_match": best_score >= 0.99  # Flag for perfect matches
                })

                # Remove from unmatched
                if best_match in unmatched_target:
                    unmatched_target.remove(best_match)
            else:
                unmatched_source.append(source_name)

        return {
            "mappings": mappings,
            "unmatched_source": unmatched_source,
            "unmatched_target": [
                col.get("name", col) if isinstance(col, dict) else col
                for col in unmatched_target
            ],
            "stats": {
                "total_source": len(source_cols),
                "total_target": len(target_cols),
                "mapped": len(mappings),
                "unmatched_source_count": len(unmatched_source),
                "unmatched_target_count": len(unmatched_target),
                "mapping_percentage": round((len(mappings) / len(source_cols)) * 100, 2) if source_cols else 0
            }
        }

    def _similarity(self, name1: str, name2: str) -> float:
        """Calculate similarity between two column names."""
        # Normalize names
        n1 = self._normalize_name(name1)
        n2 = self._normalize_name(name2)

        # Exact match
        if n1 == n2:
            return 1.0

        # Use sequence matcher for fuzzy matching
        return SequenceMatcher(None, n1, n2).ratio()

    def _normalize_name(self, name: str) -> str:
        """Normalize column name for comparison."""
        # Convert to lowercase
        name = name.lower()

        # Remove common prefixes/suffixes
        prefixes = ["src_", "tgt_", "old_", "new_", "dim_", "fact_"]
        for prefix in prefixes:
            if name.startswith(prefix):
                name = name[len(prefix):]
                break

        # Remove underscores and spaces
        name = name.replace("_", "").replace(" ", "")

        return name

    def _type_compatibility_score(self, source_type: str, target_type: str) -> float:
        """Calculate type compatibility score between source and target types."""
        if not source_type or not target_type:
            return 0.5  # Neutral score if types not provided

        # Normalize types
        source_type = source_type.lower().split('(')[0].strip()
        target_type = target_type.lower().split('(')[0].strip()

        # Exact type match
        if source_type == target_type:
            return 1.0

        # Check compatibility mapping
        compatible_types = self.type_compatibility.get(source_type, [])
        if target_type in compatible_types:
            return 0.8

        # Partial match (e.g., both numeric types)
        if self._is_numeric(source_type) and self._is_numeric(target_type):
            return 0.6

        if self._is_string(source_type) and self._is_string(target_type):
            return 0.6

        if self._is_datetime(source_type) and self._is_datetime(target_type):
            return 0.6

        # No compatibility
        return 0.2

    def _is_numeric(self, data_type: str) -> bool:
        """Check if data type is numeric."""
        numeric_types = ["int", "integer", "bigint", "smallint", "tinyint",
                        "decimal", "numeric", "float", "real", "double",
                        "money", "number"]
        return any(nt in data_type for nt in numeric_types)

    def _is_string(self, data_type: str) -> bool:
        """Check if data type is string."""
        string_types = ["char", "varchar", "nchar", "nvarchar", "text", "string"]
        return any(st in data_type for st in string_types)

    def _is_datetime(self, data_type: str) -> bool:
        """Check if data type is datetime."""
        datetime_types = ["date", "time", "datetime", "timestamp"]
        return any(dt in data_type for dt in datetime_types)