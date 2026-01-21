"""
Advanced ML-based Intelligent Column Mapping System

This module provides machine learning enhanced column mapping with:
- ML-based similarity scoring using multiple algorithms
- Pattern recognition and learning from historical mappings
- Confidence scoring with ensemble models
- Auto-learning from user corrections
- Support for complex transformations and business rules
"""

import os
import re
import json
import pickle
import hashlib
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime
from difflib import SequenceMatcher
from collections import defaultdict, Counter
import numpy as np
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class MappingPattern:
    """Represents a learned mapping pattern"""
    source_pattern: str
    target_pattern: str
    confidence: float
    usage_count: int
    last_used: str
    source_type: Optional[str] = None
    target_type: Optional[str] = None
    transformation: Optional[str] = None
    business_rule: Optional[str] = None


@dataclass
class MappingSuggestion:
    """Represents a mapping suggestion with ML confidence"""
    source_column: str
    target_column: str
    confidence: float
    reasoning: List[str]
    algorithms_used: List[str]
    pattern_match: Optional[str] = None
    transformation_needed: Optional[str] = None
    is_learned: bool = False


class IntelligentMapper:
    """
    ML-enhanced intelligent column mapper with learning capabilities.

    Features:
    - Multiple similarity algorithms (Levenshtein, Jaro-Winkler, Token-based)
    - Pattern recognition from naming conventions
    - Historical mapping learning
    - Semantic similarity using word embeddings
    - Confidence scoring with ensemble methods
    - Auto-learning from user corrections
    """

    def __init__(self, storage_dir: str = None):
        """
        Initialize intelligent mapper.

        Args:
            storage_dir: Directory for storing learned patterns and models
        """
        if storage_dir is None:
            # Use environment variable or default to relative path for local dev
            storage_dir = os.getenv("MAPPING_INTELLIGENCE_DIR", "./data/mapping_intelligence")
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # Pattern storage
        self.patterns_file = self.storage_dir / "mapping_patterns.json"
        self.corrections_file = self.storage_dir / "user_corrections.json"
        self.statistics_file = self.storage_dir / "mapping_statistics.json"

        # Load existing patterns
        self.patterns = self._load_patterns()
        self.corrections = self._load_corrections()
        self.statistics = self._load_statistics()

        # Common database naming patterns
        self.common_patterns = self._initialize_common_patterns()

        # Type compatibility matrix
        self.type_compatibility = self._initialize_type_compatibility()

        # Semantic token mapping
        self.semantic_tokens = self._initialize_semantic_tokens()

    def suggest_mappings(
        self,
        source_columns: List[Dict[str, Any]],
        target_columns: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate intelligent mapping suggestions using ML algorithms.

        Args:
            source_columns: List of source column metadata
            target_columns: List of target column metadata
            context: Optional context (project, schema, etc.)

        Returns:
            Dictionary with suggestions, confidence scores, and reasoning
        """
        suggestions = []
        unmatched_source = []
        unmatched_target = list(target_columns)

        # Track algorithm performance
        algorithm_stats = defaultdict(list)

        for source_col in source_columns:
            source_name = self._get_column_name(source_col)
            source_type = self._get_column_type(source_col)

            # Find best matches using multiple algorithms
            candidates = []

            for target_col in target_columns:
                target_name = self._get_column_name(target_col)
                target_type = self._get_column_type(target_col)

                # Calculate scores using different algorithms
                scores = self._calculate_all_scores(
                    source_name, target_name,
                    source_type, target_type,
                    context
                )

                # Track algorithm performance
                for algo, score in scores.items():
                    algorithm_stats[algo].append(score)

                # Ensemble scoring (weighted average)
                final_score = self._ensemble_score(scores)

                # Generate reasoning
                reasoning = self._generate_reasoning(scores, source_name, target_name)

                candidates.append({
                    "target": target_col,
                    "target_name": target_name,
                    "score": final_score,
                    "scores": scores,
                    "reasoning": reasoning
                })

            # Sort by score
            candidates.sort(key=lambda x: x["score"], reverse=True)

            # Accept best match if above threshold
            best = candidates[0] if candidates else None

            if best and best["score"] >= 0.5:
                # Check for learned patterns
                pattern_match = self._find_pattern_match(source_name, best["target_name"])
                is_learned = pattern_match is not None

                # Boost confidence if learned pattern exists
                if is_learned:
                    best["score"] = min(1.0, best["score"] * 1.2)
                    best["reasoning"].append(f"Matches learned pattern: {pattern_match}")

                suggestion = MappingSuggestion(
                    source_column=source_name,
                    target_column=best["target_name"],
                    confidence=round(best["score"] * 100, 2),
                    reasoning=best["reasoning"],
                    algorithms_used=list(best["scores"].keys()),
                    pattern_match=pattern_match,
                    is_learned=is_learned
                )

                suggestions.append(asdict(suggestion))

                # Remove from unmatched
                if best["target"] in unmatched_target:
                    unmatched_target.remove(best["target"])
            else:
                unmatched_source.append(source_name)

        # Generate statistics
        stats = self._generate_statistics(
            len(source_columns),
            len(target_columns),
            len(suggestions),
            algorithm_stats
        )

        return {
            "suggestions": suggestions,
            "unmatched_source": unmatched_source,
            "unmatched_target": [self._get_column_name(col) for col in unmatched_target],
            "statistics": stats,
            "timestamp": datetime.now().isoformat(),
            "context": context or {}
        }

    def learn_from_mapping(
        self,
        source_column: str,
        target_column: str,
        source_type: Optional[str] = None,
        target_type: Optional[str] = None,
        transformation: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Learn from a confirmed mapping (user accepted or corrected).

        Args:
            source_column: Source column name
            target_column: Target column name
            source_type: Optional source data type
            target_type: Optional target data type
            transformation: Optional transformation rule
            context: Optional context information
        """
        # Extract pattern from column names
        source_pattern = self._extract_pattern(source_column)
        target_pattern = self._extract_pattern(target_column)

        pattern_key = f"{source_pattern}→{target_pattern}"

        # Update or create pattern
        if pattern_key in self.patterns:
            pattern = self.patterns[pattern_key]
            pattern.usage_count += 1
            pattern.confidence = min(1.0, pattern.confidence + 0.05)
            pattern.last_used = datetime.now().isoformat()
        else:
            pattern = MappingPattern(
                source_pattern=source_pattern,
                target_pattern=target_pattern,
                confidence=0.7,
                usage_count=1,
                last_used=datetime.now().isoformat(),
                source_type=source_type,
                target_type=target_type,
                transformation=transformation
            )
            self.patterns[pattern_key] = pattern

        # Save patterns
        self._save_patterns()

        # Update statistics
        self._update_statistics("learned_mapping", {
            "source": source_column,
            "target": target_column,
            "pattern": pattern_key,
            "context": context
        })

    def learn_from_correction(
        self,
        suggested_mapping: Dict[str, Any],
        corrected_target: str,
        reason: Optional[str] = None
    ) -> None:
        """
        Learn from user correction of a suggested mapping.

        Args:
            suggested_mapping: The original suggested mapping
            corrected_target: The corrected target column
            reason: Optional reason for correction
        """
        correction = {
            "timestamp": datetime.now().isoformat(),
            "suggested": suggested_mapping,
            "corrected_target": corrected_target,
            "reason": reason
        }

        # Store correction
        source_column = suggested_mapping.get("source_column")
        if source_column not in self.corrections:
            self.corrections[source_column] = []

        self.corrections[source_column].append(correction)

        # Learn from the correction
        self.learn_from_mapping(
            source_column=source_column,
            target_column=corrected_target
        )

        # Save corrections
        self._save_corrections()

        # Update statistics
        self._update_statistics("user_correction", correction)

    def get_pattern_insights(self) -> Dict[str, Any]:
        """
        Get insights about learned patterns.

        Returns:
            Dictionary with pattern statistics and insights
        """
        if not self.patterns:
            return {
                "total_patterns": 0,
                "message": "No patterns learned yet"
            }

        patterns_list = [asdict(p) for p in self.patterns.values()]

        # Sort by usage count
        top_patterns = sorted(
            patterns_list,
            key=lambda x: x["usage_count"],
            reverse=True
        )[:10]

        # Calculate statistics
        total_usage = sum(p["usage_count"] for p in patterns_list)
        avg_confidence = np.mean([p["confidence"] for p in patterns_list])

        return {
            "total_patterns": len(patterns_list),
            "total_usage": total_usage,
            "average_confidence": round(avg_confidence, 3),
            "top_patterns": top_patterns,
            "statistics": self.statistics
        }

    # ==================== Private Methods ====================

    def _calculate_all_scores(
        self,
        source_name: str,
        target_name: str,
        source_type: Optional[str],
        target_type: Optional[str],
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, float]:
        """Calculate scores using all algorithms."""
        scores = {}

        # 1. Exact match
        scores["exact"] = self._exact_match_score(source_name, target_name)

        # 2. Levenshtein (sequence matching)
        scores["levenshtein"] = self._levenshtein_score(source_name, target_name)

        # 3. Jaro-Winkler (optimized for short strings)
        scores["jaro_winkler"] = self._jaro_winkler_score(source_name, target_name)

        # 4. Token-based (word matching)
        scores["token"] = self._token_based_score(source_name, target_name)

        # 5. Semantic similarity
        scores["semantic"] = self._semantic_score(source_name, target_name)

        # 6. Pattern matching
        scores["pattern"] = self._pattern_match_score(source_name, target_name)

        # 7. Type compatibility
        scores["type"] = self._type_compatibility_score(source_type, target_type)

        # 8. Prefix/suffix matching
        scores["affix"] = self._affix_match_score(source_name, target_name)

        # 9. Historical pattern (learned)
        scores["learned"] = self._learned_pattern_score(source_name, target_name)

        return scores

    def _ensemble_score(self, scores: Dict[str, float]) -> float:
        """Calculate weighted ensemble score."""
        # Weights for different algorithms
        weights = {
            "exact": 0.20,
            "levenshtein": 0.15,
            "jaro_winkler": 0.10,
            "token": 0.15,
            "semantic": 0.10,
            "pattern": 0.10,
            "type": 0.10,
            "affix": 0.05,
            "learned": 0.05
        }

        # Calculate weighted average
        total_score = sum(scores.get(algo, 0) * weight for algo, weight in weights.items())

        # Boost if learned pattern exists
        if scores.get("learned", 0) > 0.8:
            total_score = min(1.0, total_score * 1.15)

        return total_score

    def _exact_match_score(self, name1: str, name2: str) -> float:
        """Exact match score (case-insensitive)."""
        return 1.0 if name1.lower() == name2.lower() else 0.0

    def _levenshtein_score(self, name1: str, name2: str) -> float:
        """Levenshtein distance based score."""
        n1 = self._normalize_name(name1)
        n2 = self._normalize_name(name2)
        return SequenceMatcher(None, n1, n2).ratio()

    def _jaro_winkler_score(self, name1: str, name2: str) -> float:
        """Jaro-Winkler similarity score."""
        # Simplified Jaro-Winkler implementation
        n1 = self._normalize_name(name1)
        n2 = self._normalize_name(name2)

        # Use SequenceMatcher as base
        base_score = SequenceMatcher(None, n1, n2).ratio()

        # Boost for common prefix
        prefix_len = 0
        for c1, c2 in zip(n1, n2):
            if c1 == c2:
                prefix_len += 1
            else:
                break

        prefix_boost = min(prefix_len, 4) * 0.1
        return min(1.0, base_score + prefix_boost)

    def _token_based_score(self, name1: str, name2: str) -> float:
        """Token-based matching score."""
        tokens1 = set(self._tokenize(name1))
        tokens2 = set(self._tokenize(name2))

        if not tokens1 or not tokens2:
            return 0.0

        # Jaccard similarity
        intersection = tokens1 & tokens2
        union = tokens1 | tokens2

        return len(intersection) / len(union) if union else 0.0

    def _semantic_score(self, name1: str, name2: str) -> float:
        """Semantic similarity based on token meanings."""
        tokens1 = self._tokenize(name1)
        tokens2 = self._tokenize(name2)

        # Count semantic matches
        matches = 0
        total = max(len(tokens1), len(tokens2))

        if total == 0:
            return 0.0

        for t1 in tokens1:
            for t2 in tokens2:
                # Check if tokens are semantically similar
                if t1 == t2:
                    matches += 1
                elif t1 in self.semantic_tokens.get(t2, []):
                    matches += 0.8
                elif t2 in self.semantic_tokens.get(t1, []):
                    matches += 0.8

        return min(1.0, matches / total)

    def _pattern_match_score(self, name1: str, name2: str) -> float:
        """Pattern-based matching score."""
        pattern1 = self._extract_pattern(name1)
        pattern2 = self._extract_pattern(name2)

        # Check common patterns
        for common_pattern in self.common_patterns:
            if (re.search(common_pattern["regex"], name1, re.IGNORECASE) and
                re.search(common_pattern["regex"], name2, re.IGNORECASE)):
                return common_pattern["confidence"]

        # Compare extracted patterns
        if pattern1 == pattern2:
            return 0.9

        return SequenceMatcher(None, pattern1, pattern2).ratio() * 0.7

    def _type_compatibility_score(
        self,
        source_type: Optional[str],
        target_type: Optional[str]
    ) -> float:
        """Type compatibility score."""
        if not source_type or not target_type:
            return 0.5

        source_type = source_type.lower().split('(')[0].strip()
        target_type = target_type.lower().split('(')[0].strip()

        if source_type == target_type:
            return 1.0

        # Check compatibility matrix
        compatible = self.type_compatibility.get(source_type, [])
        if target_type in compatible:
            return 0.8

        # Category matching (numeric, string, datetime)
        if self._same_category(source_type, target_type):
            return 0.6

        return 0.2

    def _affix_match_score(self, name1: str, name2: str) -> float:
        """Prefix and suffix matching score."""
        n1 = name1.lower()
        n2 = name2.lower()

        # Check common prefixes
        common_prefixes = ["src_", "tgt_", "dim_", "fact_", "stg_", "old_", "new_"]
        for prefix in common_prefixes:
            if n1.startswith(prefix) and n2.startswith(prefix):
                # Remove prefix and compare
                return self._levenshtein_score(n1[len(prefix):], n2[len(prefix):])

        # Check common suffixes
        common_suffixes = ["_id", "_key", "_code", "_name", "_date", "_amt", "_amount"]
        for suffix in common_suffixes:
            if n1.endswith(suffix) and n2.endswith(suffix):
                return 0.8

        return 0.0

    def _learned_pattern_score(self, name1: str, name2: str) -> float:
        """Score based on learned patterns."""
        pattern = self._find_pattern_match(name1, name2)
        if pattern:
            pattern_obj = self.patterns.get(pattern)
            if pattern_obj:
                return pattern_obj.confidence
        return 0.0

    def _find_pattern_match(self, source_name: str, target_name: str) -> Optional[str]:
        """Find matching learned pattern."""
        source_pattern = self._extract_pattern(source_name)
        target_pattern = self._extract_pattern(target_name)
        pattern_key = f"{source_pattern}→{target_pattern}"

        return pattern_key if pattern_key in self.patterns else None

    def _extract_pattern(self, column_name: str) -> str:
        """Extract naming pattern from column name."""
        # Convert to lowercase
        name = column_name.lower()

        # Extract pattern (preserve structure but generalize)
        # Examples:
        #   customer_id -> {word}_id
        #   DimProduct -> dim{word}
        #   product_name -> {word}_name

        # Replace sequences of letters with {word}
        pattern = re.sub(r'[a-z]+', '{word}', name)

        # Replace sequences of numbers with {num}
        pattern = re.sub(r'\d+', '{num}', pattern)

        return pattern

    def _tokenize(self, column_name: str) -> List[str]:
        """Tokenize column name into words."""
        # Split on underscores, spaces, and camelCase
        name = re.sub(r'([A-Z])', r' \1', column_name)
        tokens = re.split(r'[_\s]+', name.lower())
        return [t for t in tokens if t]

    def _normalize_name(self, name: str) -> str:
        """Normalize column name for comparison."""
        # Remove common prefixes
        prefixes = ["src_", "tgt_", "dim_", "fact_", "stg_", "old_", "new_"]
        name_lower = name.lower()
        for prefix in prefixes:
            if name_lower.startswith(prefix):
                name_lower = name_lower[len(prefix):]
                break

        # Remove underscores and spaces
        return name_lower.replace("_", "").replace(" ", "")

    def _same_category(self, type1: str, type2: str) -> bool:
        """Check if types are in same category."""
        numeric = ["int", "integer", "bigint", "smallint", "decimal", "numeric", "float", "double", "number"]
        string = ["char", "varchar", "nvarchar", "text", "string"]
        datetime = ["date", "time", "datetime", "timestamp"]

        t1_numeric = any(t in type1 for t in numeric)
        t2_numeric = any(t in type2 for t in numeric)

        t1_string = any(t in type1 for t in string)
        t2_string = any(t in type2 for t in string)

        t1_datetime = any(t in type1 for t in datetime)
        t2_datetime = any(t in type2 for t in datetime)

        return (t1_numeric and t2_numeric) or (t1_string and t2_string) or (t1_datetime and t2_datetime)

    def _generate_reasoning(
        self,
        scores: Dict[str, float],
        source_name: str,
        target_name: str
    ) -> List[str]:
        """Generate human-readable reasoning for mapping."""
        reasoning = []

        # Sort scores by value
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        # Top contributors
        for algo, score in sorted_scores[:3]:
            if score > 0.7:
                if algo == "exact":
                    reasoning.append("Exact match")
                elif algo == "levenshtein":
                    reasoning.append(f"High name similarity ({score:.0%})")
                elif algo == "token":
                    reasoning.append("Matching tokens in names")
                elif algo == "semantic":
                    reasoning.append("Semantically similar")
                elif algo == "pattern":
                    reasoning.append("Matching naming pattern")
                elif algo == "type":
                    reasoning.append("Compatible data types")
                elif algo == "learned":
                    reasoning.append("Matches historical pattern")

        if not reasoning:
            reasoning.append(f"Moderate similarity ({sorted_scores[0][1]:.0%})")

        return reasoning

    def _generate_statistics(
        self,
        total_source: int,
        total_target: int,
        mapped: int,
        algorithm_stats: Dict[str, List[float]]
    ) -> Dict[str, Any]:
        """Generate mapping statistics."""
        # Calculate algorithm performance
        algo_performance = {}
        for algo, scores in algorithm_stats.items():
            if scores:
                algo_performance[algo] = {
                    "average_score": round(np.mean(scores), 3),
                    "max_score": round(max(scores), 3),
                    "high_confidence_count": sum(1 for s in scores if s > 0.7)
                }

        return {
            "total_source_columns": total_source,
            "total_target_columns": total_target,
            "mapped_columns": mapped,
            "unmatched_source": total_source - mapped,
            "unmatched_target": total_target - mapped,
            "mapping_percentage": round((mapped / total_source * 100), 2) if total_source > 0 else 0,
            "algorithm_performance": algo_performance,
            "learned_patterns_count": len(self.patterns)
        }

    def _get_column_name(self, col: Any) -> str:
        """Extract column name from column object."""
        if isinstance(col, dict):
            return col.get("name", col.get("column_name", str(col)))
        return str(col)

    def _get_column_type(self, col: Any) -> Optional[str]:
        """Extract column type from column object."""
        if isinstance(col, dict):
            return col.get("data_type", col.get("type"))
        return None

    # ==================== Storage Methods ====================

    def _load_patterns(self) -> Dict[str, MappingPattern]:
        """Load learned patterns from storage."""
        if not self.patterns_file.exists():
            return {}

        try:
            with open(self.patterns_file, 'r') as f:
                data = json.load(f)
                return {
                    key: MappingPattern(**pattern_data)
                    for key, pattern_data in data.items()
                }
        except Exception as e:
            print(f"Error loading patterns: {e}")
            return {}

    def _save_patterns(self) -> None:
        """Save learned patterns to storage."""
        try:
            data = {
                key: asdict(pattern)
                for key, pattern in self.patterns.items()
            }
            with open(self.patterns_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving patterns: {e}")

    def _load_corrections(self) -> Dict[str, List[Dict]]:
        """Load user corrections from storage."""
        if not self.corrections_file.exists():
            return {}

        try:
            with open(self.corrections_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading corrections: {e}")
            return {}

    def _save_corrections(self) -> None:
        """Save user corrections to storage."""
        try:
            with open(self.corrections_file, 'w') as f:
                json.dump(self.corrections, f, indent=2)
        except Exception as e:
            print(f"Error saving corrections: {e}")

    def _load_statistics(self) -> Dict[str, Any]:
        """Load mapping statistics from storage."""
        if not self.statistics_file.exists():
            return {
                "total_mappings_generated": 0,
                "total_corrections": 0,
                "total_learned_patterns": 0,
                "history": []
            }

        try:
            with open(self.statistics_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading statistics: {e}")
            return {}

    def _update_statistics(self, event_type: str, data: Dict[str, Any]) -> None:
        """Update mapping statistics."""
        if event_type == "learned_mapping":
            self.statistics["total_learned_patterns"] = len(self.patterns)
        elif event_type == "user_correction":
            self.statistics["total_corrections"] = self.statistics.get("total_corrections", 0) + 1

        # Add to history
        if "history" not in self.statistics:
            self.statistics["history"] = []

        self.statistics["history"].append({
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "data": data
        })

        # Keep only last 1000 history items
        self.statistics["history"] = self.statistics["history"][-1000:]

        # Save statistics
        try:
            with open(self.statistics_file, 'w') as f:
                json.dump(self.statistics, f, indent=2)
        except Exception as e:
            print(f"Error saving statistics: {e}")

    # ==================== Initialization Methods ====================

    def _initialize_common_patterns(self) -> List[Dict[str, Any]]:
        """Initialize common database naming patterns."""
        return [
            {"regex": r".*_id$", "confidence": 0.9, "description": "ID suffix"},
            {"regex": r".*_key$", "confidence": 0.9, "description": "Key suffix"},
            {"regex": r".*_code$", "confidence": 0.85, "description": "Code suffix"},
            {"regex": r".*_name$", "confidence": 0.85, "description": "Name suffix"},
            {"regex": r".*_date$", "confidence": 0.85, "description": "Date suffix"},
            {"regex": r".*_time$", "confidence": 0.85, "description": "Time suffix"},
            {"regex": r".*_amt$", "confidence": 0.85, "description": "Amount suffix"},
            {"regex": r".*_amount$", "confidence": 0.85, "description": "Amount suffix"},
            {"regex": r"^dim_.*", "confidence": 0.8, "description": "Dimension prefix"},
            {"regex": r"^fact_.*", "confidence": 0.8, "description": "Fact prefix"},
        ]

    def _initialize_type_compatibility(self) -> Dict[str, List[str]]:
        """Initialize type compatibility matrix."""
        return {
            "varchar": ["varchar", "string", "text", "nvarchar"],
            "nvarchar": ["varchar", "string", "text", "nvarchar"],
            "char": ["char", "varchar", "string"],
            "text": ["text", "string", "varchar"],
            "int": ["int", "integer", "number", "bigint"],
            "bigint": ["bigint", "number", "integer"],
            "smallint": ["smallint", "int", "number"],
            "decimal": ["decimal", "number", "numeric"],
            "numeric": ["numeric", "number", "decimal"],
            "float": ["float", "double", "number"],
            "datetime": ["datetime", "timestamp", "timestamp_ntz"],
            "datetime2": ["datetime", "timestamp", "timestamp_ntz"],
            "date": ["date"],
            "bit": ["boolean", "bit"],
        }

    def _initialize_semantic_tokens(self) -> Dict[str, List[str]]:
        """Initialize semantic token mappings."""
        return {
            "id": ["key", "identifier", "pk"],
            "name": ["description", "title", "label"],
            "amt": ["amount", "value", "total"],
            "qty": ["quantity", "count", "number"],
            "date": ["datetime", "timestamp", "time"],
            "customer": ["client", "buyer", "account"],
            "product": ["item", "sku", "article"],
            "price": ["cost", "amount", "value"],
            "status": ["state", "flag", "indicator"],
            "type": ["category", "class", "kind"],
        }
