"""Tests for API endpoints."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock

from app.main import app

client = TestClient(app)


class TestHealthEndpoints:
    """Test health check endpoints."""
    
    def test_root_endpoint(self):
        """Test root health check."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "active"
        assert "timestamp" in data
    
    def test_health_endpoint(self):
        """Test detailed health check."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "services" in data


class TestAnalysisEndpoints:
    """Test analysis endpoints."""
    
    @patch('app.celery_app.analyze_pr_task.delay')
    def test_analyze_pr_endpoint(self, mock_celery_task):
        """Test PR analysis endpoint."""
        # Mock Celery task
        mock_task = Mock()
        mock_task.id = "test-task-id"
        mock_celery_task.return_value = mock_task
        
        payload = {
            "repo_url": "https://github.com/test/repo",
            "pr_number": 123
        }
        
        response = client.post("/analyze-pr", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert "task_id" in data
        assert data["status"] == "pending"
    
    def test_analyze_pr_invalid_payload(self):
        """Test PR analysis with invalid payload."""
        payload = {
            "repo_url": "invalid-url",
            "pr_number": -1
        }
        
        response = client.post("/analyze-pr", json=payload)
        assert response.status_code == 422  # Validation error
    
    def test_status_endpoint_not_found(self):
        """Test status endpoint with non-existent task."""
        response = client.get("/status/non-existent-task")
        assert response.status_code == 404
    
    def test_results_endpoint_not_found(self):
        """Test results endpoint with non-existent task."""
        response = client.get("/results/non-existent-task")
        assert response.status_code == 404


class TestAdminEndpoints:
    """Test admin endpoints."""
    
    def test_admin_health_check(self):
        """Test admin health check endpoint."""
        response = client.get("/admin/health")
        assert response.status_code == 200
        data = response.json()
        assert "components" in data
        assert "status" in data
    
    def test_cache_stats_endpoint(self):
        """Test cache statistics endpoint."""
        response = client.get("/admin/cache/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total_entries" in data
    
    def test_system_info_endpoint(self):
        """Test system info endpoint."""
        response = client.get("/admin/system/info")
        assert response.status_code == 200
        data = response.json()
        assert "version" in data
        assert "features" in data
        assert "configuration" in data