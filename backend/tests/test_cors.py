"""
Tests for CORS middleware configuration.

Verifies that the frontend origin is allowed and that OPTIONS preflight
requests work as expected.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


def test_cors_headers_on_get_request(client: TestClient):
    """
    Verify that GET requests from the frontend origin receive proper
    Access-Control-Allow-Origin header.
    """
    response = client.get(
        "/health",
        headers={"Origin": "http://localhost:5173"}
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_cors_preflight_options_request(client: TestClient):
    """
    Verify that OPTIONS preflight requests work correctly.
    """
    response = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        }
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert "GET" in response.headers.get("access-control-allow-methods", "")


def test_cors_allows_common_methods(client: TestClient):
    """
    Verify that common HTTP methods are allowed in CORS configuration.
    """
    response = client.options(
        "/api/matters/search",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
        }
    )
    assert response.status_code == 200
    allowed_methods = response.headers.get("access-control-allow-methods", "")
    assert "POST" in allowed_methods
    assert "GET" in allowed_methods
    assert "PUT" in allowed_methods
    assert "DELETE" in allowed_methods


def test_cors_does_not_allow_credentials(client: TestClient):
    """
    Verify that credentials are not allowed (allow_credentials=False).
    """
    response = client.get(
        "/health",
        headers={"Origin": "http://localhost:5173"}
    )
    # When allow_credentials is False, the header should not be present or be "false"
    credentials_header = response.headers.get("access-control-allow-credentials")
    assert credentials_header is None or credentials_header.lower() == "false"


def test_cors_rejects_other_origins(client: TestClient):
    """
    Verify that requests from origins other than localhost:5173 do not
    receive the Access-Control-Allow-Origin header.
    """
    response = client.get(
        "/health",
        headers={"Origin": "http://evil.com"}
    )
    assert response.status_code == 200  # Request still succeeds
    # But the CORS header should not match the origin
    assert response.headers.get("access-control-allow-origin") != "http://evil.com"
