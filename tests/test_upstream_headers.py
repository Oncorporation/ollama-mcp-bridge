"""Tests for the --upstream-header flag and UPSTREAM_HEADERS env var"""

import re

import pytest
import typer
from typer import BadParameter
from typer.testing import CliRunner
from unittest.mock import patch

from ollama_mcp_bridge.utils import parse_upstream_headers

_ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*m")


def _invoke(args):
    """Run cli_app via CliRunner with server startup mocked out."""
    import ollama_mcp_bridge.main as main_module

    app = typer.Typer()
    app.command()(main_module.cli_app)
    with (
        patch("ollama_mcp_bridge.main.is_port_in_use", return_value=(False, "")),
        patch("ollama_mcp_bridge.main.check_ollama_health", return_value=True),
        patch("ollama_mcp_bridge.main.check_for_updates"),
        patch("ollama_mcp_bridge.main.uvicorn.run") as mock_uvicorn,
    ):
        result = CliRunner().invoke(app, args)
    return result, mock_uvicorn


# --- parse_upstream_headers unit tests ---------------------------------------


def test_parse_none_when_no_input():
    assert parse_upstream_headers(None, []) is None
    assert parse_upstream_headers("", None) is None


def test_parse_env_json():
    assert parse_upstream_headers('{"Authorization": "Bearer xxx"}', []) == {"Authorization": "Bearer xxx"}


def test_parse_repeatable_flags():
    headers = parse_upstream_headers(None, ["Authorization: Bearer xxx", "X-API-Key: yyy"])
    assert headers == {"Authorization": "Bearer xxx", "X-API-Key": "yyy"}


def test_parse_flags_override_env_per_key():
    headers = parse_upstream_headers('{"X-API-Key": "env", "Keep": "1"}', ["X-API-Key: cli"])
    assert headers == {"X-API-Key": "cli", "Keep": "1"}


def test_parse_strips_flag_whitespace():
    assert parse_upstream_headers(None, ["Authorization:  Bearer xyz "]) == {"Authorization": "Bearer xyz"}


def test_parse_keeps_value_colons():
    assert parse_upstream_headers(None, ["X-Url: http://h:11434"]) == {"X-Url": "http://h:11434"}


def test_parse_rejects_flag_without_colon():
    with pytest.raises(BadParameter):
        parse_upstream_headers(None, ["missing-colon"])


def test_parse_rejects_empty_flag_name():
    with pytest.raises(BadParameter):
        parse_upstream_headers(None, [": value"])


def test_parse_rejects_invalid_json():
    with pytest.raises(BadParameter):
        parse_upstream_headers("not json", None)


def test_parse_rejects_non_object_json():
    with pytest.raises(BadParameter):
        parse_upstream_headers('["a", "b"]', None)


# --- CLI integration tests ----------------------------------------------------


def test_cli_headers_from_env_json(monkeypatch):
    monkeypatch.setenv("UPSTREAM_HEADERS", '{"Authorization": "Bearer test-token"}')
    from ollama_mcp_bridge.api import app as fastapi_app

    result, mock_uvicorn = _invoke(["--config", "mcp-config.json"])

    assert result.exit_code == 0, result.output
    mock_uvicorn.assert_called_once()
    assert fastapi_app.state.ollama_headers == {"Authorization": "Bearer test-token"}


def test_cli_headers_from_repeatable_flags(monkeypatch):
    monkeypatch.delenv("UPSTREAM_HEADERS", raising=False)
    from ollama_mcp_bridge.api import app as fastapi_app

    result, mock_uvicorn = _invoke(
        [
            "--config",
            "mcp-config.json",
            "--upstream-header",
            "Authorization: Bearer xxx",
            "--upstream-header",
            "X-API-Key: yyy",
        ]
    )

    assert result.exit_code == 0, result.output
    mock_uvicorn.assert_called_once()
    assert fastapi_app.state.ollama_headers == {"Authorization": "Bearer xxx", "X-API-Key": "yyy"}


def test_cli_flags_override_env(monkeypatch):
    monkeypatch.setenv("UPSTREAM_HEADERS", '{"Authorization": "Bearer env", "X-API-Key": "keep"}')
    from ollama_mcp_bridge.api import app as fastapi_app

    result, _ = _invoke(["--config", "mcp-config.json", "--upstream-header", "Authorization: Bearer cli"])

    assert result.exit_code == 0, result.output
    assert fastapi_app.state.ollama_headers == {"Authorization": "Bearer cli", "X-API-Key": "keep"}


def test_cli_headers_unset(monkeypatch):
    monkeypatch.delenv("UPSTREAM_HEADERS", raising=False)
    from ollama_mcp_bridge.api import app as fastapi_app

    result, _ = _invoke(["--config", "mcp-config.json"])

    assert result.exit_code == 0, result.output
    assert fastapi_app.state.ollama_headers is None


def test_cli_invalid_flag_format(monkeypatch):
    monkeypatch.delenv("UPSTREAM_HEADERS", raising=False)

    result, _ = _invoke(["--config", "mcp-config.json", "--upstream-header", "missing-colon"])

    assert result.exit_code == 2
    output = _ANSI_ESCAPE_RE.sub("", result.output)
    assert "--upstream-header" in output


def test_cli_invalid_env_json(monkeypatch):
    monkeypatch.setenv("UPSTREAM_HEADERS", "not json")

    result, _ = _invoke(["--config", "mcp-config.json"])

    assert result.exit_code == 2
    output = _ANSI_ESCAPE_RE.sub("", result.output)
    assert "UPSTREAM_HEADERS" in output
