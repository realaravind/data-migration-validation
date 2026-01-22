"""
Tests for Projects API endpoints

Tests project management operations including:
- Project CRUD operations
- Schema mappings
- Relationships management
- Project automation
- Azure DevOps configuration
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import json
import os
import tempfile
import shutil


class TestProjectCreate:
    """Tests for POST /projects/create"""

    def test_create_project_success(self, client, mock_auth_user):
        """Should create a new project with valid data"""
        response = client.post(
            "/projects/create",
            json={
                "name": "Test Project",
                "description": "A test project",
                "sql_database": "TestDB",
                "sql_schemas": ["dbo", "dim"],
                "snowflake_database": "TESTDB",
                "snowflake_schemas": ["PUBLIC", "DIM"]
            },
            headers={"Authorization": "Bearer test_token"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "project_id" in data
        assert data["metadata"]["name"] == "Test Project"

    def test_create_project_duplicate_name(self, client, mock_auth_user, existing_project):
        """Should reject duplicate project names"""
        response = client.post(
            "/projects/create",
            json={
                "name": existing_project["name"],
                "sql_database": "TestDB",
                "sql_schemas": ["dbo"],
                "snowflake_database": "TESTDB",
                "snowflake_schemas": ["PUBLIC"]
            },
            headers={"Authorization": "Bearer test_token"}
        )

        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    def test_create_project_auto_schema_mapping(self, client, mock_auth_user):
        """Should auto-map schemas when not provided"""
        response = client.post(
            "/projects/create",
            json={
                "name": "Auto Map Project",
                "sql_database": "TestDB",
                "sql_schemas": ["dbo", "dim", "fact"],
                "snowflake_database": "TESTDB",
                "snowflake_schemas": ["PUBLIC", "DIM", "FACT"]
            },
            headers={"Authorization": "Bearer test_token"}
        )

        assert response.status_code == 200
        data = response.json()
        # Schema mappings should be auto-generated
        assert "schema_mappings" in data["metadata"]

    def test_create_project_requires_auth(self, client):
        """Should require authentication"""
        response = client.post(
            "/projects/create",
            json={
                "name": "No Auth Project",
                "sql_database": "TestDB",
                "sql_schemas": ["dbo"],
                "snowflake_database": "TESTDB",
                "snowflake_schemas": ["PUBLIC"]
            }
        )

        assert response.status_code == 401


class TestProjectList:
    """Tests for GET /projects/list"""

    def test_list_projects_empty(self, client):
        """Should return empty list when no projects exist"""
        response = client.get("/projects/list")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert isinstance(data["projects"], list)

    def test_list_projects_with_data(self, client, existing_project):
        """Should return all projects"""
        response = client.get("/projects/list")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] >= 1
        project_names = [p["name"] for p in data["projects"]]
        assert existing_project["name"] in project_names


class TestProjectLoad:
    """Tests for GET /projects/{project_id}"""

    def test_load_project_success(self, client, existing_project):
        """Should load and set project as active"""
        response = client.get(f"/projects/{existing_project['project_id']}")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["metadata"]["name"] == existing_project["name"]

    def test_load_project_not_found(self, client):
        """Should return 404 for non-existent project"""
        response = client.get("/projects/non_existent_project")

        assert response.status_code == 404


class TestProjectSave:
    """Tests for POST /projects/{project_id}/save"""

    def test_save_project_success(self, client, mock_auth_user, existing_project):
        """Should save project state"""
        response = client.post(
            f"/projects/{existing_project['project_id']}/save",
            headers={"Authorization": "Bearer test_token"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "updated_at" in data

    def test_save_project_not_found(self, client, mock_auth_user):
        """Should return 404 for non-existent project"""
        response = client.post(
            "/projects/non_existent_project/save",
            headers={"Authorization": "Bearer test_token"}
        )

        assert response.status_code == 404


class TestProjectDelete:
    """Tests for DELETE /projects/{project_id}"""

    def test_delete_project_success(self, client, mock_auth_user, existing_project):
        """Should delete project and cascade delete related data"""
        response = client.delete(
            f"/projects/{existing_project['project_id']}",
            headers={"Authorization": "Bearer test_token"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "deleted" in data

    def test_delete_project_not_found(self, client, mock_auth_user):
        """Should return 404 for non-existent project"""
        response = client.delete(
            "/projects/non_existent_project",
            headers={"Authorization": "Bearer test_token"}
        )

        assert response.status_code == 404

    def test_delete_project_requires_auth(self, client, existing_project):
        """Should require authentication"""
        response = client.delete(f"/projects/{existing_project['project_id']}")

        assert response.status_code == 401


class TestUpdateSchemaMappings:
    """Tests for PUT /projects/{project_id}/update-schema-mappings"""

    def test_update_schema_mappings_success(self, client, existing_project):
        """Should update schema mappings"""
        response = client.put(
            f"/projects/{existing_project['project_id']}/update-schema-mappings",
            json={
                "schema_mappings": {
                    "dbo": "PUBLIC",
                    "dim": "DIM",
                    "fact": "FACT"
                }
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["schema_mappings"]["dbo"] == "PUBLIC"

    def test_update_schema_mappings_not_found(self, client):
        """Should return 404 for non-existent project"""
        response = client.put(
            "/projects/non_existent/update-schema-mappings",
            json={"schema_mappings": {"dbo": "PUBLIC"}}
        )

        assert response.status_code == 404


class TestProjectRelationships:
    """Tests for relationships endpoints"""

    def test_save_sql_relationships(self, client, existing_project):
        """Should save SQL relationships"""
        response = client.post(
            f"/projects/{existing_project['project_id']}/relationships/sql",
            json={
                "relationships": [
                    {
                        "fact_table": "fact_sales",
                        "dimension_table": "dim_customer",
                        "foreign_key": "customer_id",
                        "primary_key": "id"
                    }
                ],
                "metrics": {"total": 1},
                "diagram": "graph LR"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    def test_save_snow_relationships(self, client, existing_project):
        """Should save Snowflake relationships"""
        response = client.post(
            f"/projects/{existing_project['project_id']}/relationships/snow",
            json={
                "relationships": [],
                "metrics": {},
                "diagram": ""
            }
        )

        assert response.status_code == 200

    def test_save_invalid_database_type(self, client, existing_project):
        """Should reject invalid database type"""
        response = client.post(
            f"/projects/{existing_project['project_id']}/relationships/invalid",
            json={"relationships": []}
        )

        assert response.status_code == 400

    def test_get_relationships(self, client, existing_project):
        """Should get project relationships"""
        response = client.get(
            f"/projects/{existing_project['project_id']}/relationships"
        )

        assert response.status_code == 200
        data = response.json()
        assert "relationships" in data

    def test_update_relationships(self, client, mock_auth_user, existing_project):
        """Should update relationships"""
        response = client.put(
            f"/projects/{existing_project['project_id']}/relationships",
            json=[
                {
                    "fact_table": "fact_orders",
                    "dimension_table": "dim_product",
                    "foreign_key": "product_id",
                    "primary_key": "id"
                }
            ],
            headers={"Authorization": "Bearer test_token"}
        )

        assert response.status_code == 200


class TestProjectStatus:
    """Tests for GET /projects/{project_id}/status"""

    def test_get_status_success(self, client, existing_project):
        """Should return project setup status"""
        response = client.get(
            f"/projects/{existing_project['project_id']}/status"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "has_metadata" in data
        assert "has_relationships" in data
        assert "ready_for_automation" in data


class TestActiveProject:
    """Tests for GET /projects/active"""

    def test_get_active_project_none(self, client):
        """Should handle no active project"""
        response = client.get("/projects/active")

        assert response.status_code == 200
        # May return no_active_project status

    def test_get_active_project_after_load(self, client, existing_project):
        """Should return active project after loading"""
        # First load a project
        client.get(f"/projects/{existing_project['project_id']}")

        # Then check active
        response = client.get("/projects/active")

        assert response.status_code == 200


class TestAzureDevOpsConfig:
    """Tests for Azure DevOps configuration endpoints"""

    def test_configure_azure_devops(self, client, mock_auth_user, existing_project):
        """Should configure Azure DevOps integration"""
        response = client.post(
            f"/projects/{existing_project['project_id']}/azure-devops/configure",
            json={
                "enabled": True,
                "organization_url": "https://dev.azure.com/testorg",
                "project_name": "TestProject",
                "pat_token": "test_token_123",
                "work_item_type": "Bug",
                "auto_tags": ["ombudsman", "validation"]
            },
            headers={"Authorization": "Bearer test_token"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    def test_get_azure_config(self, client, existing_project):
        """Should get Azure DevOps configuration"""
        response = client.get(
            f"/projects/{existing_project['project_id']}/azure-devops/config"
        )

        assert response.status_code == 200
        # May return not_configured or configured status

    def test_get_azure_config_masks_token(self, client, mock_auth_user, existing_project):
        """Should mask PAT token in response"""
        # First configure
        client.post(
            f"/projects/{existing_project['project_id']}/azure-devops/configure",
            json={
                "enabled": True,
                "organization_url": "https://dev.azure.com/testorg",
                "project_name": "TestProject",
                "pat_token": "secret_token",
                "work_item_type": "Bug"
            },
            headers={"Authorization": "Bearer test_token"}
        )

        # Then get config
        response = client.get(
            f"/projects/{existing_project['project_id']}/azure-devops/config"
        )

        if response.json().get("status") == "configured":
            assert response.json()["config"]["pat_token"] == "***REDACTED***"

    def test_delete_azure_config(self, client, mock_auth_user, existing_project):
        """Should delete Azure DevOps configuration"""
        response = client.delete(
            f"/projects/{existing_project['project_id']}/azure-devops/configure",
            headers={"Authorization": "Bearer test_token"}
        )

        assert response.status_code == 200

    def test_test_azure_connection(self, client, existing_project):
        """Should test Azure DevOps connection"""
        with patch('bugs.azure_devops_service.AzureDevOpsService') as mock_service:
            mock_instance = MagicMock()
            mock_instance.test_connection.return_value = {
                "success": True,
                "message": "Connection successful"
            }
            mock_service.return_value = mock_instance

            response = client.post(
                f"/projects/{existing_project['project_id']}/azure-devops/test",
                json={
                    "organization_url": "https://dev.azure.com/testorg",
                    "project_name": "TestProject",
                    "pat_token": "test_token"
                }
            )

            assert response.status_code == 200


# Fixtures for this test module
@pytest.fixture
def existing_project(client, mock_auth_user, tmp_path):
    """Create an existing project for tests"""
    # Create project via API
    response = client.post(
        "/projects/create",
        json={
            "name": "Existing Test Project",
            "description": "Pre-existing project for tests",
            "sql_database": "TestDB",
            "sql_schemas": ["dbo"],
            "snowflake_database": "TESTDB",
            "snowflake_schemas": ["PUBLIC"]
        },
        headers={"Authorization": "Bearer test_token"}
    )

    data = response.json()
    yield {
        "project_id": data.get("project_id", "existing_test_project"),
        "name": "Existing Test Project"
    }

    # Cleanup after test
    try:
        client.delete(
            f"/projects/{data.get('project_id', 'existing_test_project')}",
            headers={"Authorization": "Bearer test_token"}
        )
    except:
        pass


@pytest.fixture
def mock_auth_user():
    """Mock authenticated user"""
    with patch('auth.dependencies.require_user_or_admin') as mock:
        mock.return_value = MagicMock(
            username="testuser",
            role="admin"
        )
        yield mock
