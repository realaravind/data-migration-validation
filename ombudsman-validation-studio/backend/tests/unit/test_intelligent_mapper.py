"""
Unit tests for Intelligent Mapping System

Tests all ML algorithms and learning capabilities.
"""

import pytest
import sys
import os
from pathlib import Path

# Add backend directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from mapping.ml_mapper import IntelligentMapper, MappingPattern, MappingSuggestion


@pytest.fixture
def mapper():
    """Create a clean intelligent mapper for testing"""
    # Use a temporary directory for testing
    test_dir = "/tmp/test_intelligent_mapper"
    Path(test_dir).mkdir(parents=True, exist_ok=True)
    return IntelligentMapper(storage_dir=test_dir)


@pytest.fixture
def sample_source_columns():
    """Sample source columns"""
    return [
        {"name": "customer_id", "data_type": "int"},
        {"name": "customer_name", "data_type": "varchar(100)"},
        {"name": "order_date", "data_type": "datetime"},
        {"name": "total_amount", "data_type": "decimal(10,2)"},
        {"name": "product_code", "data_type": "varchar(50)"}
    ]


@pytest.fixture
def sample_target_columns():
    """Sample target columns"""
    return [
        {"name": "CUSTOMER_ID", "data_type": "number"},
        {"name": "CUSTOMER_NAME", "data_type": "varchar"},
        {"name": "ORDER_DATE", "data_type": "timestamp_ntz"},
        {"name": "TOTAL_AMT", "data_type": "number"},
        {"name": "PRODUCT_CODE", "data_type": "varchar"}
    ]


@pytest.mark.unit
class TestBasicScoring:
    """Test basic similarity scoring algorithms"""

    def test_exact_match_score(self, mapper):
        """Test exact match scoring"""
        score = mapper._exact_match_score("customer_id", "CUSTOMER_ID")
        assert score == 1.0

        score = mapper._exact_match_score("customer_id", "order_id")
        assert score == 0.0

    def test_levenshtein_score(self, mapper):
        """Test Levenshtein distance scoring"""
        # Exact match after normalization
        score = mapper._levenshtein_score("customer_id", "CUSTOMER_ID")
        assert score > 0.9

        # Similar names
        score = mapper._levenshtein_score("customer_name", "cust_name")
        assert 0.5 < score < 0.9

        # Different names
        score = mapper._levenshtein_score("customer_id", "product_code")
        assert score < 0.5

    def test_jaro_winkler_score(self, mapper):
        """Test Jaro-Winkler similarity"""
        # Same prefix
        score = mapper._jaro_winkler_score("customer_id", "customer_key")
        assert score > 0.7

        # Different
        score = mapper._jaro_winkler_score("customer_id", "product_code")
        assert score < 0.5

    def test_token_based_score(self, mapper):
        """Test token-based matching"""
        # All tokens match
        score = mapper._token_based_score("customer_id", "id_customer")
        assert score == 1.0

        # Partial match
        score = mapper._token_based_score("customer_order_id", "customer_id")
        assert 0.5 < score < 1.0

        # No match
        score = mapper._token_based_score("customer_id", "product_name")
        assert score < 0.5


@pytest.mark.unit
class TestPatternExtraction:
    """Test pattern extraction and matching"""

    def test_extract_pattern(self, mapper):
        """Test pattern extraction from column names"""
        pattern = mapper._extract_pattern("customer_id")
        assert pattern == "{word}_{word}"  # customer -> {word}, id -> {word}

        pattern = mapper._extract_pattern("DimProduct")
        # DimProduct becomes "dimproduct" (lowercase), then all letters -> {word}
        assert pattern == "{word}"

        pattern = mapper._extract_pattern("product_name_123")
        assert pattern == "{word}_{word}_{num}"

    def test_tokenize(self, mapper):
        """Test column name tokenization"""
        tokens = mapper._tokenize("customer_order_id")
        assert tokens == ["customer", "order", "id"]

        tokens = mapper._tokenize("DimProduct")
        assert tokens == ["dim", "product"]

    def test_normalize_name(self, mapper):
        """Test column name normalization"""
        normalized = mapper._normalize_name("SRC_Customer_ID")
        assert normalized == "customerid"

        normalized = mapper._normalize_name("dim_product_name")
        assert normalized == "productname"


@pytest.mark.unit
class TestTypeCompatibility:
    """Test type compatibility scoring"""

    def test_exact_type_match(self, mapper):
        """Test exact type matching"""
        score = mapper._type_compatibility_score("int", "int")
        assert score == 1.0

    def test_compatible_types(self, mapper):
        """Test compatible type matching"""
        # int to number
        score = mapper._type_compatibility_score("int", "number")
        assert score == 0.8

        # varchar to string
        score = mapper._type_compatibility_score("varchar", "string")
        assert score == 0.8

    def test_same_category(self, mapper):
        """Test same category types"""
        # Both numeric (varchar is compatible with text, so gets 0.8)
        score = mapper._type_compatibility_score("int", "decimal")
        assert score >= 0.6

        # Both string (varchar is compatible with text)
        score = mapper._type_compatibility_score("varchar", "text")
        assert score >= 0.6

    def test_incompatible_types(self, mapper):
        """Test incompatible types"""
        score = mapper._type_compatibility_score("int", "varchar")
        assert score == 0.2


@pytest.mark.unit
class TestMappingSuggestions:
    """Test mapping suggestion generation"""

    def test_suggest_mappings_exact_match(self, mapper, sample_source_columns, sample_target_columns):
        """Test suggestions with exact matches"""
        result = mapper.suggest_mappings(sample_source_columns, sample_target_columns)

        assert "suggestions" in result
        assert len(result["suggestions"]) >= 4  # Most columns should match

        # Check first suggestion
        first_suggestion = result["suggestions"][0]
        assert "source_column" in first_suggestion
        assert "target_column" in first_suggestion
        assert "confidence" in first_suggestion
        assert first_suggestion["confidence"] > 60  # Good confidence

    def test_suggest_mappings_partial_match(self, mapper):
        """Test suggestions with partial matches"""
        source = [
            {"name": "cust_id", "data_type": "int"},
            {"name": "cust_name", "data_type": "varchar"}
        ]
        target = [
            {"name": "customer_id", "data_type": "number"},
            {"name": "customer_name", "data_type": "varchar"}
        ]

        result = mapper.suggest_mappings(source, target)

        assert len(result["suggestions"]) == 2
        # Lower confidence due to name differences
        assert result["suggestions"][0]["confidence"] > 50

    def test_suggest_mappings_unmatched(self, mapper):
        """Test handling of unmatched columns"""
        source = [
            {"name": "customer_id", "data_type": "int"},
            {"name": "unknown_field", "data_type": "varchar"}
        ]
        target = [
            {"name": "customer_id", "data_type": "number"}
        ]

        result = mapper.suggest_mappings(source, target)

        assert len(result["unmatched_source"]) == 1
        assert "unknown_field" in result["unmatched_source"]

    def test_suggest_mappings_statistics(self, mapper, sample_source_columns, sample_target_columns):
        """Test statistics generation"""
        result = mapper.suggest_mappings(sample_source_columns, sample_target_columns)

        stats = result["statistics"]
        assert stats["total_source_columns"] == 5
        assert stats["total_target_columns"] == 5
        assert stats["mapping_percentage"] >= 70  # Most columns should map

    def test_reasoning_generation(self, mapper):
        """Test reasoning generation for suggestions"""
        scores = {
            "exact": 1.0,
            "levenshtein": 0.9,
            "token": 0.8,
            "type": 1.0
        }

        reasoning = mapper._generate_reasoning(scores, "customer_id", "CUSTOMER_ID")

        assert len(reasoning) > 0
        assert any("exact" in r.lower() for r in reasoning)


@pytest.mark.unit
class TestLearning:
    """Test learning from mappings and corrections"""

    def test_learn_from_mapping(self, mapper):
        """Test learning from a confirmed mapping"""
        # Use a unique column name to avoid conflicts with other tests
        import tempfile
        fresh_mapper = IntelligentMapper(storage_dir=tempfile.mkdtemp())
        initial_count = len(fresh_mapper.patterns)

        fresh_mapper.learn_from_mapping(
            source_column="unique_customer_id",
            target_column="UNIQUE_CUSTOMER_ID",
            source_type="int",
            target_type="number"
        )

        # Should have added a pattern
        assert len(fresh_mapper.patterns) > initial_count

        # Pattern should exist (customer_id extracts to {word}_{word}_{word})
        pattern_key = "{word}_{word}_{word}→{word}_{word}_{word}"
        assert pattern_key in fresh_mapper.patterns

        # Check pattern properties
        pattern = fresh_mapper.patterns[pattern_key]
        assert pattern.confidence > 0
        assert pattern.usage_count == 1

    def test_learn_multiple_times(self, mapper):
        """Test that learning multiple times increases confidence"""
        mapper.learn_from_mapping("customer_id", "CUSTOMER_ID")
        pattern_key = "{word}_{word}→{word}_{word}"
        first_confidence = mapper.patterns[pattern_key].confidence
        first_usage = mapper.patterns[pattern_key].usage_count

        mapper.learn_from_mapping("product_id", "PRODUCT_ID")
        second_confidence = mapper.patterns[pattern_key].confidence
        second_usage = mapper.patterns[pattern_key].usage_count

        # Confidence should increase
        assert second_confidence >= first_confidence
        # Usage count should increase
        assert second_usage == first_usage + 1

    def test_learn_from_correction(self, mapper):
        """Test learning from user corrections"""
        import tempfile
        fresh_mapper = IntelligentMapper(storage_dir=tempfile.mkdtemp())
        initial_corrections_count = sum(len(v) for v in fresh_mapper.corrections.values())

        suggested = {
            "source_column": "order_id",
            "target_column": "ord_id",
            "confidence": 75.0
        }

        fresh_mapper.learn_from_correction(
            suggested_mapping=suggested,
            corrected_target="ORDER_ID",
            reason="Incorrect suggestion"
        )

        # Should have stored correction
        new_corrections_count = sum(len(v) for v in fresh_mapper.corrections.values())
        assert new_corrections_count > initial_corrections_count
        assert "order_id" in fresh_mapper.corrections


@pytest.mark.unit
class TestPatternInsights:
    """Test pattern insights and statistics"""

    def test_get_pattern_insights_empty(self, mapper):
        """Test insights when no patterns learned"""
        # Create a completely clean mapper
        import tempfile
        clean_mapper = IntelligentMapper(storage_dir=tempfile.mkdtemp())
        insights = clean_mapper.get_pattern_insights()

        assert insights["total_patterns"] == 0
        assert "message" in insights

    def test_get_pattern_insights_with_data(self, mapper):
        """Test insights with learned patterns"""
        # Learn some patterns
        mapper.learn_from_mapping("customer_id", "CUSTOMER_ID")
        mapper.learn_from_mapping("product_id", "PRODUCT_ID")
        mapper.learn_from_mapping("order_date", "ORDER_DATE")

        insights = mapper.get_pattern_insights()

        assert insights["total_patterns"] > 0
        assert insights["total_usage"] > 0
        assert "average_confidence" in insights
        assert "top_patterns" in insights


@pytest.mark.unit
class TestEnsembleScoring:
    """Test ensemble scoring"""

    def test_ensemble_score(self, mapper):
        """Test weighted ensemble scoring"""
        scores = {
            "exact": 1.0,
            "levenshtein": 0.9,
            "jaro_winkler": 0.85,
            "token": 0.9,
            "semantic": 0.8,
            "pattern": 0.75,
            "type": 1.0,
            "affix": 0.7,
            "learned": 0.0
        }

        ensemble = mapper._ensemble_score(scores)

        # Should be weighted average
        assert 0.8 < ensemble < 1.0

    def test_ensemble_score_with_learning(self, mapper):
        """Test ensemble boost when learned pattern exists"""
        scores = {
            "exact": 0.8,
            "levenshtein": 0.7,
            "jaro_winkler": 0.7,
            "token": 0.7,
            "semantic": 0.6,
            "pattern": 0.6,
            "type": 0.8,
            "affix": 0.5,
            "learned": 0.9  # High learned score
        }

        ensemble = mapper._ensemble_score(scores)

        # Should get boost from learned pattern
        assert ensemble > 0.75


@pytest.mark.unit
class TestSemanticSimilarity:
    """Test semantic similarity scoring"""

    def test_semantic_score_identical(self, mapper):
        """Test semantic scoring for identical tokens"""
        score = mapper._semantic_score("customer_id", "customer_id")
        assert score == 1.0

    def test_semantic_score_synonyms(self, mapper):
        """Test semantic scoring for synonyms"""
        score = mapper._semantic_score("customer_id", "client_key")
        # "customer" and "client" are semantically similar
        # "id" and "key" are semantically similar
        assert score > 0.5

    def test_semantic_score_different(self, mapper):
        """Test semantic scoring for different terms"""
        score = mapper._semantic_score("customer_id", "product_name")
        assert score < 0.5


@pytest.mark.unit
class TestStoragePersistence:
    """Test pattern storage and persistence"""

    def test_save_and_load_patterns(self, mapper):
        """Test saving and loading patterns"""
        # Learn a pattern
        mapper.learn_from_mapping("customer_id", "CUSTOMER_ID")

        # Save patterns
        mapper._save_patterns()

        # Create new mapper with same storage
        new_mapper = IntelligentMapper(storage_dir=mapper.storage_dir)

        # Should have loaded the pattern
        pattern_key = "{word}_{word}→{word}_{word}"
        assert pattern_key in new_mapper.patterns
        assert new_mapper.patterns[pattern_key].usage_count >= 1

    def test_statistics_persistence(self, mapper):
        """Test statistics persistence"""
        # Update statistics
        mapper._update_statistics("test_event", {"test": "data"})

        # Create new mapper
        new_mapper = IntelligentMapper(storage_dir=mapper.storage_dir)

        # Should have loaded statistics
        assert len(new_mapper.statistics.get("history", [])) > 0


@pytest.mark.unit
class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_empty_columns(self, mapper):
        """Test with empty column lists"""
        result = mapper.suggest_mappings([], [])

        assert result["suggestions"] == []
        assert result["unmatched_source"] == []
        assert result["unmatched_target"] == []

    def test_missing_type_information(self, mapper):
        """Test with missing type information"""
        source = [{"name": "customer_id"}]  # No type
        target = [{"name": "CUSTOMER_ID"}]  # No type

        result = mapper.suggest_mappings(source, target)

        # Should still make suggestions
        assert len(result["suggestions"]) == 1

    def test_special_characters_in_names(self, mapper):
        """Test with special characters"""
        source = [{"name": "customer_#id", "data_type": "int"}]
        target = [{"name": "CUSTOMER_#ID", "data_type": "number"}]

        result = mapper.suggest_mappings(source, target)

        # Should handle special characters
        assert len(result["suggestions"]) == 1

    def test_very_long_column_names(self, mapper):
        """Test with very long column names"""
        source = [{"name": "a" * 100, "data_type": "int"}]
        target = [{"name": "A" * 100, "data_type": "number"}]

        result = mapper.suggest_mappings(source, target)

        # Should handle long names
        assert len(result["suggestions"]) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
