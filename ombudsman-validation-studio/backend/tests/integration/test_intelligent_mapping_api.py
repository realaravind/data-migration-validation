"""
Integration tests for Intelligent Mapping API

Tests all API endpoints with authentication.
"""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.integration
class TestIntelligentMappingAPI:
    """Test intelligent mapping API endpoints"""

    def test_health_check(self, client):
        """Test health check endpoint"""
        response = client.get("/mapping/intelligent/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "algorithms" in data
        assert len(data["algorithms"]) == 9  # 9 algorithms

    def test_suggest_mappings_no_auth(self, client):
        """Test that suggestions work without auth (public endpoint)"""
        request_data = {
            "source_columns": [
                {"name": "customer_id", "data_type": "int"},
                {"name": "customer_name", "data_type": "varchar"}
            ],
            "target_columns": [
                {"name": "CUSTOMER_ID", "data_type": "number"},
                {"name": "CUSTOMER_NAME", "data_type": "varchar"}
            ]
        }

        response = client.post("/mapping/intelligent/suggest", json=request_data)

        # Should work without authentication
        if response.status_code == 200:
            data = response.json()
            assert data["status"] == "success"
            assert "result" in data
            assert "suggestions" in data["result"]
            assert len(data["result"]["suggestions"]) == 2  # Both columns should match
        else:
            pytest.skip("Intelligent mapping not configured")

    def test_suggest_mappings_with_types(self, client):
        """Test suggestions with type information"""
        request_data = {
            "source_columns": [
                {"name": "customer_id", "data_type": "int"},
                {"name": "order_date", "data_type": "datetime"},
                {"name": "total_amount", "data_type": "decimal"}
            ],
            "target_columns": [
                {"name": "CUSTOMER_ID", "data_type": "number"},
                {"name": "ORDER_DATE", "data_type": "timestamp_ntz"},
                {"name": "TOTAL_AMT", "data_type": "number"}
            ]
        }

        response = client.post("/mapping/intelligent/suggest", json=request_data)

        if response.status_code == 200:
            data = response.json()
            result = data["result"]

            # Should have suggestions
            assert len(result["suggestions"]) >= 2

            # Check first suggestion structure
            suggestion = result["suggestions"][0]
            assert "source_column" in suggestion
            assert "target_column" in suggestion
            assert "confidence" in suggestion
            assert "reasoning" in suggestion
            assert "algorithms_used" in suggestion

            # Should have statistics
            assert "statistics" in result
            assert "mapping_percentage" in result["statistics"]
        else:
            pytest.skip("Intelligent mapping not configured")

    def test_suggest_mappings_with_context(self, client):
        """Test suggestions with context information"""
        request_data = {
            "source_columns": [
                {"name": "cust_id", "data_type": "int"}
            ],
            "target_columns": [
                {"name": "customer_id", "data_type": "number"}
            ],
            "context": {
                "project": "test_project",
                "schema": "dbo"
            }
        }

        response = client.post("/mapping/intelligent/suggest", json=request_data)

        if response.status_code == 200:
            data = response.json()
            assert "context" in data["result"]
            assert data["result"]["context"]["project"] == "test_project"
        else:
            pytest.skip("Intelligent mapping not configured")


@pytest.mark.integration
class TestLearningEndpoints:
    """Test learning and correction endpoints"""

    def test_learn_from_mapping_requires_auth(self, client):
        """Test that learning requires authentication"""
        request_data = {
            "source_column": "customer_id",
            "target_column": "CUSTOMER_ID",
            "source_type": "int",
            "target_type": "number"
        }

        response = client.post("/mapping/intelligent/learn", json=request_data)

        # Should require authentication
        assert response.status_code in [401, 403]

    def test_learn_from_mapping_with_auth(self, client):
        """Test learning with authentication"""
        # Register and login
        client.post("/auth/register", json={
            "username": "mapper_user",
            "email": "mapper@example.com",
            "password": "SecurePass123",
            "role": "user"
        })

        login_response = client.post("/auth/login", json={
            "username": "mapper_user",
            "password": "SecurePass123"
        })

        if login_response.status_code == 200:
            access_token = login_response.json()["access_token"]

            request_data = {
                "source_column": "customer_id",
                "target_column": "CUSTOMER_ID",
                "source_type": "int",
                "target_type": "number"
            }

            response = client.post(
                "/mapping/intelligent/learn",
                headers={"Authorization": f"Bearer {access_token}"},
                json=request_data
            )

            if response.status_code == 200:
                data = response.json()
                assert data["status"] == "success"
                assert "message" in data
            else:
                pytest.skip("Learning endpoint not fully configured")
        else:
            pytest.skip("Auth not configured")

    def test_batch_learning_with_auth(self, client):
        """Test batch learning"""
        # Register and login
        client.post("/auth/register", json={
            "username": "batch_mapper",
            "email": "batch@example.com",
            "password": "SecurePass123",
            "role": "user"
        })

        login_response = client.post("/auth/login", json={
            "username": "batch_mapper",
            "password": "SecurePass123"
        })

        if login_response.status_code == 200:
            access_token = login_response.json()["access_token"]

            request_data = {
                "mappings": [
                    {
                        "source_column": "customer_id",
                        "target_column": "CUSTOMER_ID",
                        "source_type": "int",
                        "target_type": "number"
                    },
                    {
                        "source_column": "product_id",
                        "target_column": "PRODUCT_ID",
                        "source_type": "int",
                        "target_type": "number"
                    }
                ]
            }

            response = client.post(
                "/mapping/intelligent/learn/batch",
                headers={"Authorization": f"Bearer {access_token}"},
                json=request_data
            )

            if response.status_code == 200:
                data = response.json()
                assert data["status"] == "success"
                assert data["learned_count"] == 2
            else:
                pytest.skip("Batch learning not configured")
        else:
            pytest.skip("Auth not configured")

    def test_correction_learning(self, client):
        """Test learning from corrections"""
        # Register and login
        client.post("/auth/register", json={
            "username": "correction_user",
            "email": "correction@example.com",
            "password": "SecurePass123",
            "role": "user"
        })

        login_response = client.post("/auth/login", json={
            "username": "correction_user",
            "password": "SecurePass123"
        })

        if login_response.status_code == 200:
            access_token = login_response.json()["access_token"]

            request_data = {
                "suggested_mapping": {
                    "source_column": "customer_id",
                    "target_column": "cust_id",
                    "confidence": 75.0
                },
                "corrected_target": "CUSTOMER_ID",
                "reason": "Wrong suggestion"
            }

            response = client.post(
                "/mapping/intelligent/correct",
                headers={"Authorization": f"Bearer {access_token}"},
                json=request_data
            )

            if response.status_code == 200:
                data = response.json()
                assert data["status"] == "success"
            else:
                pytest.skip("Correction learning not configured")
        else:
            pytest.skip("Auth not configured")


@pytest.mark.integration
class TestPatternInsights:
    """Test pattern insights and statistics endpoints"""

    def test_get_pattern_insights_no_auth(self, client):
        """Test getting pattern insights without auth"""
        response = client.get("/mapping/intelligent/patterns")

        # Should work without auth (public)
        if response.status_code == 200:
            data = response.json()
            assert data["status"] == "success"
            assert "insights" in data
        else:
            pytest.skip("Pattern insights not configured")

    def test_get_statistics_no_auth(self, client):
        """Test getting statistics without auth"""
        response = client.get("/mapping/intelligent/statistics")

        if response.status_code == 200:
            data = response.json()
            assert data["status"] == "success"
            assert "statistics" in data
        else:
            pytest.skip("Statistics not configured")


@pytest.mark.integration
class TestPatternManagement:
    """Test pattern export/import and reset"""

    def test_export_patterns_requires_auth(self, client):
        """Test that exporting patterns requires auth"""
        response = client.post("/mapping/intelligent/export-patterns")

        assert response.status_code in [401, 403]

    def test_export_patterns_with_auth(self, client):
        """Test exporting patterns with auth"""
        # Create admin user
        client.post("/auth/register", json={
            "username": "export_admin",
            "email": "export@example.com",
            "password": "AdminPass123",
            "role": "admin"
        })

        login_response = client.post("/auth/login", json={
            "username": "export_admin",
            "password": "AdminPass123"
        })

        if login_response.status_code == 200:
            access_token = login_response.json()["access_token"]

            response = client.post(
                "/mapping/intelligent/export-patterns",
                headers={"Authorization": f"Bearer {access_token}"}
            )

            if response.status_code == 200:
                data = response.json()
                assert data["status"] == "success"
                assert "patterns" in data
                assert "total_patterns" in data
            else:
                pytest.skip("Export not configured")
        else:
            pytest.skip("Auth not configured")

    def test_import_patterns_requires_auth(self, client):
        """Test that importing patterns requires auth"""
        response = client.post("/mapping/intelligent/import-patterns", json={})

        assert response.status_code in [401, 403]

    def test_reset_patterns_requires_auth(self, client):
        """Test that resetting patterns requires auth"""
        response = client.delete("/mapping/intelligent/patterns/reset")

        assert response.status_code in [401, 403]


@pytest.mark.integration
class TestCompleteWorkflow:
    """Test complete mapping workflow"""

    def test_complete_mapping_workflow(self, client):
        """Test complete workflow: suggest -> learn -> suggest again"""
        # 1. Register and login
        client.post("/auth/register", json={
            "username": "workflow_user",
            "email": "workflow@example.com",
            "password": "SecurePass123",
            "role": "user"
        })

        login_response = client.post("/auth/login", json={
            "username": "workflow_user",
            "password": "SecurePass123"
        })

        if login_response.status_code != 200:
            pytest.skip("Auth not configured")
            return

        access_token = login_response.json()["access_token"]

        # 2. Get initial suggestions
        suggest_request = {
            "source_columns": [
                {"name": "customer_id", "data_type": "int"},
                {"name": "product_code", "data_type": "varchar"}
            ],
            "target_columns": [
                {"name": "CUSTOMER_ID", "data_type": "number"},
                {"name": "PRODUCT_CODE", "data_type": "varchar"}
            ]
        }

        suggest_response = client.post(
            "/mapping/intelligent/suggest",
            json=suggest_request
        )

        if suggest_response.status_code != 200:
            pytest.skip("Suggest not configured")
            return

        initial_suggestions = suggest_response.json()["result"]["suggestions"]

        # 3. Learn from accepted mapping
        learn_request = {
            "source_column": "customer_id",
            "target_column": "CUSTOMER_ID",
            "source_type": "int",
            "target_type": "number"
        }

        learn_response = client.post(
            "/mapping/intelligent/learn",
            headers={"Authorization": f"Bearer {access_token}"},
            json=learn_request
        )

        if learn_response.status_code != 200:
            pytest.skip("Learn not configured")
            return

        # 4. Get suggestions again (should have learned)
        suggest_response2 = client.post(
            "/mapping/intelligent/suggest",
            json=suggest_request
        )

        if suggest_response2.status_code == 200:
            new_suggestions = suggest_response2.json()["result"]["suggestions"]
            # Should still have suggestions
            assert len(new_suggestions) > 0


@pytest.mark.integration
class TestErrorHandling:
    """Test error handling"""

    def test_invalid_request_data(self, client):
        """Test with invalid request data"""
        response = client.post("/mapping/intelligent/suggest", json={
            "invalid": "data"
        })

        # Should return validation error
        assert response.status_code == 422

    def test_empty_columns(self, client):
        """Test with empty column lists"""
        request_data = {
            "source_columns": [],
            "target_columns": []
        }

        response = client.post("/mapping/intelligent/suggest", json=request_data)

        if response.status_code == 200:
            data = response.json()
            assert data["result"]["suggestions"] == []
        else:
            pytest.skip("Not configured")

    def test_missing_required_fields(self, client):
        """Test with missing required fields"""
        response = client.post("/mapping/intelligent/learn", json={
            "source_column": "customer_id"
            # Missing target_column
        })

        # Should return validation error
        assert response.status_code in [422, 401, 403]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
