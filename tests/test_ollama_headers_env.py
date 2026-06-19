"""Tests for OLLAMA_HEADER_NAME and OLLAMA_HEADER_VALUE environment variables"""

import importlib
import os

import pytest
import typer
from typer.testing import CliRunner
from unittest.mock import patch


@pytest.fixture(autouse=True)
def reload_main_module():
    """cli_app's typer.Option defaults capture os.getenv(...) at import time, so reload
    the module after each test to avoid leaking env-var-bound defaults into later tests.
    """
    yield
    import ollama_mcp_bridge.main

    importlib.reload(ollama_mcp_bridge.main)


def _invoke_cli_app(args):
    """CliRunner needs a real Typer app, not the raw function used by typer.run()."""
    import ollama_mcp_bridge.main

    importlib.reload(ollama_mcp_bridge.main)  # re-bind os.getenv(...) defaults to current env
    app = typer.Typer()
    app.command()(ollama_mcp_bridge.main.cli_app)
    return CliRunner().invoke(app, args)


def test_ollama_headers_from_env_vars(monkeypatch):
    """Test that OLLAMA_HEADER_NAME and OLLAMA_HEADER_VALUE are read from environment"""
    monkeypatch.setenv("OLLAMA_HEADER_NAME", "Authorization")
    monkeypatch.setenv("OLLAMA_HEADER_VALUE", "Bearer test-token")

    from ollama_mcp_bridge.api import app as fastapi_app

    # Mock the validation and health check to prevent actual server startup
    with (
        patch("ollama_mcp_bridge.main.validate_cli_inputs"),
        patch("ollama_mcp_bridge.main.is_port_in_use", return_value=(False, "")),
        patch("ollama_mcp_bridge.main.check_ollama_health", return_value=True),
        patch("ollama_mcp_bridge.main.check_for_updates"),
        patch("ollama_mcp_bridge.main.uvicorn.run") as mock_uvicorn,
    ):
        result = _invoke_cli_app(["--config", "mcp-config.json"])

    assert result.exit_code == 0, result.output
    mock_uvicorn.assert_called_once()
    assert fastapi_app.state.ollama_headers == {"Authorization": "Bearer test-token"}


def test_ollama_headers_cli_overrides_env(monkeypatch):
    """Test that CLI arguments override environment variables"""
    monkeypatch.setenv("OLLAMA_HEADER_NAME", "X-Default-Key")
    monkeypatch.setenv("OLLAMA_HEADER_VALUE", "default-value")

    from ollama_mcp_bridge.api import app as fastapi_app

    with (
        patch("ollama_mcp_bridge.main.validate_cli_inputs"),
        patch("ollama_mcp_bridge.main.is_port_in_use", return_value=(False, "")),
        patch("ollama_mcp_bridge.main.check_ollama_health", return_value=True),
        patch("ollama_mcp_bridge.main.check_for_updates"),
        patch("ollama_mcp_bridge.main.uvicorn.run") as mock_uvicorn,
    ):
        result = _invoke_cli_app(
            [
                "--config",
                "mcp-config.json",
                "--ollama-header-name",
                "X-Custom-Key",
                "--ollama-header-value",
                "custom-value",
            ]
        )

    assert result.exit_code == 0, result.output
    mock_uvicorn.assert_called_once()
    assert fastapi_app.state.ollama_headers == {"X-Custom-Key": "custom-value"}


def test_ollama_headers_unset_when_env_vars_missing(monkeypatch):
    """Test that headers remain None when environment variables are not set"""
    monkeypatch.delenv("OLLAMA_HEADER_NAME", raising=False)
    monkeypatch.delenv("OLLAMA_HEADER_VALUE", raising=False)

    from ollama_mcp_bridge.api import app as fastapi_app

    with (
        patch("ollama_mcp_bridge.main.validate_cli_inputs"),
        patch("ollama_mcp_bridge.main.is_port_in_use", return_value=(False, "")),
        patch("ollama_mcp_bridge.main.check_ollama_health", return_value=True),
        patch("ollama_mcp_bridge.main.check_for_updates"),
        patch("ollama_mcp_bridge.main.uvicorn.run") as mock_uvicorn,
    ):
        result = _invoke_cli_app(["--config", "mcp-config.json"])

    assert result.exit_code == 0, result.output
    mock_uvicorn.assert_called_once()
    assert fastapi_app.state.ollama_headers is None


def test_ollama_headers_partial_env_vars(monkeypatch):
    """Test that validation rejects a header name set without a matching header value"""
    monkeypatch.setenv("OLLAMA_HEADER_NAME", "X-API-Key")
    monkeypatch.delenv("OLLAMA_HEADER_VALUE", raising=False)

    # validate_cli_inputs is intentionally left unmocked here: this test exists to
    # confirm it actually rejects a lone header name, not just that the CLI doesn't crash.
    with (
        patch("ollama_mcp_bridge.main.is_port_in_use", return_value=(False, "")),
        patch("ollama_mcp_bridge.main.check_ollama_health", return_value=True),
        patch("ollama_mcp_bridge.main.check_for_updates"),
        patch("ollama_mcp_bridge.main.uvicorn.run"),
    ):
        result = _invoke_cli_app(["--config", "mcp-config.json"])

    assert result.exit_code == 2
    # Rich wraps the error text across lines, so check for the flags rather than the full sentence.
    assert "--ollama-header-name" in result.output
    assert "--ollama-header-value" in result.output
    assert "must be" in result.output


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
