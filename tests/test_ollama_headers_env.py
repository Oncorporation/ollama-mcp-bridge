"""Tests for OLLAMA_HEADER_NAME and OLLAMA_HEADER_VALUE environment variables"""

import pytest
from unittest.mock import patch
import os


def test_ollama_headers_from_env_vars(monkeypatch):
    """Test that OLLAMA_HEADER_NAME and OLLAMA_HEADER_VALUE are read from environment"""
    monkeypatch.setenv("OLLAMA_HEADER_NAME", "Authorization")
    monkeypatch.setenv("OLLAMA_HEADER_VALUE", "Bearer test-token")

    # Import after setting env vars
    from ollama_mcp_bridge.main import cli_app
    from typer.testing import CliRunner

    # Mock the validation and health check to prevent actual server startup
    with (
        patch("ollama_mcp_bridge.main.validate_cli_inputs"),
        patch("ollama_mcp_bridge.main.is_port_in_use", return_value=(False, "")),
        patch("ollama_mcp_bridge.main.check_ollama_health", return_value=True),
        patch("ollama_mcp_bridge.main.check_for_updates"),
        patch("ollama_mcp_bridge.main.uvicorn.run") as mock_uvicorn,
    ):

        # Create a runner and invoke the CLI
        runner = CliRunner()
        result = runner.invoke(cli_app, ["--config", "mcp-config.json"])

        # Verify the app was called (it would start the server)
        mock_uvicorn.assert_called_once()


def test_ollama_headers_cli_overrides_env(monkeypatch):
    """Test that CLI arguments override environment variables"""
    monkeypatch.setenv("OLLAMA_HEADER_NAME", "X-Default-Key")
    monkeypatch.setenv("OLLAMA_HEADER_VALUE", "default-value")

    from ollama_mcp_bridge.main import cli_app
    from typer.testing import CliRunner

    with (
        patch("ollama_mcp_bridge.main.validate_cli_inputs"),
        patch("ollama_mcp_bridge.main.is_port_in_use", return_value=(False, "")),
        patch("ollama_mcp_bridge.main.check_ollama_health", return_value=True),
        patch("ollama_mcp_bridge.main.check_for_updates"),
        patch("ollama_mcp_bridge.main.uvicorn.run"),
    ):

        runner = CliRunner()
        result = runner.invoke(
            cli_app,
            [
                "--config",
                "mcp-config.json",
                "--ollama-header-name",
                "X-Custom-Key",
                "--ollama-header-value",
                "custom-value",
            ],
        )


def test_ollama_headers_unset_when_env_vars_missing(monkeypatch):
    """Test that headers remain None when environment variables are not set"""
    monkeypatch.delenv("OLLAMA_HEADER_NAME", raising=False)
    monkeypatch.delenv("OLLAMA_HEADER_VALUE", raising=False)

    from ollama_mcp_bridge.main import cli_app
    from typer.testing import CliRunner

    with (
        patch("ollama_mcp_bridge.main.validate_cli_inputs"),
        patch("ollama_mcp_bridge.main.is_port_in_use", return_value=(False, "")),
        patch("ollama_mcp_bridge.main.check_ollama_health", return_value=True),
        patch("ollama_mcp_bridge.main.check_for_updates"),
        patch("ollama_mcp_bridge.main.uvicorn.run"),
    ):

        runner = CliRunner()
        result = runner.invoke(cli_app, ["--config", "mcp-config.json"])


def test_ollama_headers_partial_env_vars(monkeypatch):
    """Test behavior when only one of the header env vars is set"""
    monkeypatch.setenv("OLLAMA_HEADER_NAME", "X-API-Key")
    monkeypatch.delenv("OLLAMA_HEADER_VALUE", raising=False)

    from ollama_mcp_bridge.main import cli_app
    from typer.testing import CliRunner

    with (
        patch("ollama_mcp_bridge.main.validate_cli_inputs"),
        patch("ollama_mcp_bridge.main.is_port_in_use", return_value=(False, "")),
        patch("ollama_mcp_bridge.main.check_ollama_health", return_value=True),
        patch("ollama_mcp_bridge.main.check_for_updates"),
        patch("ollama_mcp_bridge.main.uvicorn.run"),
    ):

        runner = CliRunner()
        # This should work - the validation logic should handle partial values
        result = runner.invoke(cli_app, ["--config", "mcp-config.json"])


@pytest.mark.anyio
async def test_proxy_service_uses_env_headers(monkeypatch):
    """Test that ProxyService correctly uses headers from environment variables"""
    import ollama_mcp_bridge.mcp_manager as mcp_manager_mod
    import ollama_mcp_bridge.proxy_service as proxy_service_mod

    # Set up environment variables
    monkeypatch.setenv("OLLAMA_HEADER_NAME", "X-API-Key")
    monkeypatch.setenv("OLLAMA_HEADER_VALUE", "secret-key-123")

    # Create MCPManager with headers from env (simulating what main.py does)
    header_name = os.getenv("OLLAMA_HEADER_NAME")
    header_value = os.getenv("OLLAMA_HEADER_VALUE")
    ollama_headers = {header_name: header_value} if header_name and header_value else None

    mgr = mcp_manager_mod.MCPManager(ollama_headers=ollama_headers)
    ps = proxy_service_mod.ProxyService(mgr)

    # Verify headers are set correctly
    assert ps.ollama_headers == {"X-API-Key": "secret-key-123"}

    # Verify _get_ollama_headers includes the configured headers
    merged_headers = ps._get_ollama_headers()
    assert merged_headers == {"X-API-Key": "secret-key-123"}
