"""CLI command tests using Click test runner."""
import pytest
from click.testing import CliRunner
from mycelium.cli import cli


@pytest.fixture
def runner():
    return CliRunner()


def test_cli_help(runner):
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "Mycelium" in result.output


def test_init_no_config(runner, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(cli, ["init"])
    assert result.exit_code == 0 or "not found" in result.output.lower()


def test_status_no_config(runner, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(cli, ["status"])
    # Should fail gracefully without config
    assert result.exit_code != 0 or "not found" in result.output.lower() or "Error" in result.output


def test_agents_help(runner):
    result = runner.invoke(cli, ["agents", "--help"])
    assert result.exit_code == 0
    assert "list" in result.output


def test_learn_help(runner):
    result = runner.invoke(cli, ["learn", "--help"])
    assert result.exit_code == 0
    assert "calls" in result.output
    assert "quick" in result.output
    assert "deep" in result.output
