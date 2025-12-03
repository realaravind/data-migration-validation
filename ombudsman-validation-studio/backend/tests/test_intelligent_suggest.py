"""
Integration tests for Intelligent Pipeline Suggestion
"""
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


class TestSuggestForFact:
    """Test /pipelines/suggest-for-fact endpoint"""

    def test_salesfact_analysis(self):
        """Test SalesFact table analysis and suggestions"""
        request = {
            "fact_table": "SalesFact",
            "fact_schema": "fact",
            "database_type": "sql",
            "columns": [
                {"name": "SaleID", "type": "INT"},
                {"name": "OrderDate", "type": "DATE"},
                {"name": "ProductID", "type": "INT"},
                {"name": "CustomerID", "type": "INT"},
                {"name": "StoreID", "type": "INT"},
                {"name": "Quantity", "type": "INT"},
                {"name": "UnitPrice", "type": "DECIMAL(10,2)"},
                {"name": "TotalAmount", "type": "DECIMAL(10,2)"},
                {"name": "DiscountAmount", "type": "DECIMAL(10,2)"},
                {"name": "TaxAmount", "type": "DECIMAL(10,2)"},
                {"name": "NetAmount", "type": "DECIMAL(10,2)"}
            ],
            "relationships": [
                {
                    "fact_table": "SalesFact",
                    "fk_column": "ProductID",
                    "dim_table": "DimProduct"
                },
                {
                    "fact_table": "SalesFact",
                    "fk_column": "CustomerID",
                    "dim_table": "DimCustomer"
                },
                {
                    "fact_table": "SalesFact",
                    "fk_column": "StoreID",
                    "dim_table": "DimStore"
                }
            ]
        }

        response = client.post("/pipelines/suggest-for-fact", json=request)
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "success"
        assert data["fact_table"] == "SalesFact"

        # Check analysis
        analysis = data["analysis"]
        assert analysis["total_columns"] == 11
        assert analysis["numeric_columns"] == 6  # Quantity, UnitPrice, TotalAmount, DiscountAmount, TaxAmount, NetAmount
        assert analysis["date_columns"] == 1  # OrderDate
        assert analysis["fk_columns"] == 3  # ProductID, CustomerID, StoreID
        assert analysis["relationships"] == 3

        # Check suggested checks
        suggested = data["suggested_checks"]
        assert len(suggested) >= 6  # Should have at least 6 categories

        # Verify key categories are present
        categories = [s["category"] for s in suggested]
        assert "Schema Validation" in categories
        assert "Data Quality" in categories
        assert "Business Metrics" in categories
        assert "Referential Integrity" in categories
        assert "Time-Series Analysis" in categories

        # Check priorities
        priorities = [s["priority"] for s in suggested]
        assert "CRITICAL" in priorities
        assert "HIGH" in priorities

        # Verify Business Metrics has sum columns
        business_metrics = next((s for s in suggested if s["category"] == "Business Metrics"), None)
        assert business_metrics is not None
        assert "applicable_columns" in business_metrics
        assert "sum_columns" in business_metrics["applicable_columns"]
        sum_cols = business_metrics["applicable_columns"]["sum_columns"]
        assert "TotalAmount" in sum_cols
        assert "Quantity" in sum_cols

        # Verify pipeline YAML is generated
        assert "pipeline_yaml" in data
        assert len(data["pipeline_yaml"]) > 0

        # Verify total validations
        assert data["total_validations"] >= 18


    def test_no_relationships(self):
        """Test fact table with no relationships"""
        request = {
            "fact_table": "SimpleFact",
            "fact_schema": "fact",
            "database_type": "sql",
            "columns": [
                {"name": "FactID", "type": "INT"},
                {"name": "Date", "type": "DATE"},
                {"name": "Amount", "type": "DECIMAL"}
            ],
            "relationships": []
        }

        response = client.post("/pipelines/suggest-for-fact", json=request)
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "success"

        # Should still suggest schema and DQ checks
        categories = [s["category"] for s in data["suggested_checks"]]
        assert "Schema Validation" in categories
        assert "Data Quality" in categories

        # Should NOT suggest RI checks
        assert "Referential Integrity" not in categories


    def test_no_numeric_columns(self):
        """Test fact table with no numeric columns"""
        request = {
            "fact_table": "LogFact",
            "fact_schema": "fact",
            "database_type": "sql",
            "columns": [
                {"name": "LogID", "type": "INT"},
                {"name": "LogDate", "type": "DATE"},
                {"name": "Message", "type": "VARCHAR"}
            ],
            "relationships": []
        }

        response = client.post("/pipelines/suggest-for-fact", json=request)
        assert response.status_code == 200

        data = response.json()

        # Should NOT suggest Business Metrics or Statistical Analysis
        categories = [s["category"] for s in data["suggested_checks"]]
        assert "Business Metrics" not in categories
        assert "Statistical Analysis" not in categories


class TestCreateFromNL:
    """Test /pipelines/create-from-nl endpoint"""

    def test_simple_sum_validation(self):
        """Test: 'Validate total sales amount'"""
        request = {
            "description": "Validate total sales amount",
            "context": {
                "sql_database": "SampleDW",
                "table": "SalesFact"
            }
        }

        response = client.post("/pipelines/create-from-nl", json=request)
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "success"

        checks = data["detected_intent"]["checks"]
        assert len(checks) >= 1

        # Should detect metric_sums
        check_names = [c["check"] for c in checks]
        assert "validate_metric_sums" in check_names


    def test_orphaned_fk_validation(self):
        """Test: 'Check for orphaned products'"""
        request = {
            "description": "Check for orphaned products and customers"
        }

        response = client.post("/pipelines/create-from-nl", json=request)
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "success"

        checks = data["detected_intent"]["checks"]
        check_names = [c["check"] for c in checks]

        # Should detect FK validation
        assert "validate_foreign_keys" in check_names
        assert "validate_fact_dim_conformance" in check_names


    def test_date_continuity(self):
        """Test: 'Ensure no gaps in daily sales data'"""
        request = {
            "description": "Ensure no gaps in daily sales data"
        }

        response = client.post("/pipelines/create-from-nl", json=request)
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "success"

        checks = data["detected_intent"]["checks"]
        check_names = [c["check"] for c in checks]

        # Should detect time-series continuity
        assert "validate_ts_continuity" in check_names


    def test_comprehensive_validation(self):
        """Test: 'Full validation of sales fact'"""
        request = {
            "description": "Complete validation of sales fact table"
        }

        response = client.post("/pipelines/create-from-nl", json=request)
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "success"

        checks = data["detected_intent"]["checks"]

        # Should have multiple checks
        assert len(checks) >= 3

        check_names = [c["check"] for c in checks]
        assert "validate_schema_columns" in check_names
        assert "validate_record_counts" in check_names
        assert "validate_metric_sums" in check_names


    def test_multi_intent(self):
        """Test: Complex query with multiple intents"""
        request = {
            "description": "Validate row counts, total revenue, and check for orphaned customers"
        }

        response = client.post("/pipelines/create-from-nl", json=request)
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "success"

        checks = data["detected_intent"]["checks"]
        check_names = [c["check"] for c in checks]

        # Should detect all three intents
        assert "validate_record_counts" in check_names  # row counts
        assert "validate_metric_sums" in check_names     # revenue
        assert "validate_foreign_keys" in check_names    # orphaned

        # Should have high confidence
        assert data["confidence"] in ["medium", "high"]


    def test_unclear_request(self):
        """Test: Unclear natural language"""
        request = {
            "description": "Something about data"
        }

        response = client.post("/pipelines/create-from-nl", json=request)
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "unclear"
        assert "suggestions" in data


    def test_duplicate_removal(self):
        """Test: Same validation requested multiple ways"""
        request = {
            "description": "Validate total sales amount and check sum of revenue"
        }

        response = client.post("/pipelines/create-from-nl", json=request)
        assert response.status_code == 200

        data = response.json()
        checks = data["detected_intent"]["checks"]
        check_names = [c["check"] for c in checks]

        # Should only have validate_metric_sums ONCE
        assert check_names.count("validate_metric_sums") == 1


    def test_statistical_keywords(self):
        """Test: Statistical analysis keywords"""
        request = {
            "description": "Check for outliers and validate distribution"
        }

        response = client.post("/pipelines/create-from-nl", json=request)
        assert response.status_code == 200

        data = response.json()
        checks = data["detected_intent"]["checks"]
        check_names = [c["check"] for c in checks]

        assert "validate_outliers" in check_names
        assert "validate_distribution" in check_names


    def test_scd_detection(self):
        """Test: SCD dimension validation"""
        request = {
            "description": "Validate SCD2 dimension history"
        }

        response = client.post("/pipelines/create-from-nl", json=request)
        assert response.status_code == 200

        data = response.json()
        checks = data["detected_intent"]["checks"]
        check_names = [c["check"] for c in checks]

        assert "validate_scd2" in check_names


    def test_schema_validation(self):
        """Test: Schema structure keywords"""
        request = {
            "description": "Validate table structure and column data types"
        }

        response = client.post("/pipelines/create-from-nl", json=request)
        assert response.status_code == 200

        data = response.json()
        checks = data["detected_intent"]["checks"]
        check_names = [c["check"] for c in checks]

        assert "validate_schema_columns" in check_names
        assert "validate_schema_datatypes" in check_names


class TestPipelineYAMLGeneration:
    """Test YAML generation quality"""

    def test_yaml_structure(self):
        """Test generated YAML has correct structure"""
        request = {
            "description": "Validate total sales"
        }

        response = client.post("/pipelines/create-from-nl", json=request)
        assert response.status_code == 200

        data = response.json()
        yaml_content = data["pipeline_yaml"]

        # Check key YAML components are present
        assert "pipeline:" in yaml_content
        assert "name:" in yaml_content
        assert "steps:" in yaml_content
        assert "execution:" in yaml_content


    def test_yaml_parseable(self):
        """Test generated YAML is valid"""
        import yaml

        request = {
            "description": "Validate row counts and totals"
        }

        response = client.post("/pipelines/create-from-nl", json=request)
        data = response.json()
        yaml_content = data["pipeline_yaml"]

        # Should be parseable
        try:
            parsed = yaml.safe_load(yaml_content)
            assert "pipeline" in parsed
            assert "steps" in parsed["pipeline"]
        except yaml.YAMLError:
            pytest.fail("Generated YAML is not parseable")


class TestConfidenceScoring:
    """Test confidence level calculation"""

    def test_high_confidence(self):
        """Test high confidence with 4+ matches"""
        request = {
            "description": "Validate row counts, total sales, null values, and check for duplicates"
        }

        response = client.post("/pipelines/create-from-nl", json=request)
        data = response.json()

        assert data["confidence"] == "high"


    def test_medium_confidence(self):
        """Test medium confidence with 2-3 matches"""
        request = {
            "description": "Check total sales and row counts"
        }

        response = client.post("/pipelines/create-from-nl", json=request)
        data = response.json()

        assert data["confidence"] in ["medium", "high"]


    def test_low_confidence(self):
        """Test low confidence with 1 match"""
        request = {
            "description": "Check totals"
        }

        response = client.post("/pipelines/create-from-nl", json=request)
        data = response.json()

        if data["status"] == "success":
            assert data["confidence"] in ["low", "medium"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
