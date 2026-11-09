import json

import pytest
from click.testing import CliRunner

from json_toolkit.cli import main


@pytest.mark.parametrize("command", ["format", "minify"])
def test_cli_new_output(command, tmp_path):
    source = tmp_path / "input.json"
    output = tmp_path / "output.json"
    source.write_text('{"z":1,"a":2}')
    result = CliRunner().invoke(main, [command, "-i", str(source), "-o", str(output)])
    assert result.exit_code == 0, result.output
    assert json.loads(output.read_text()) == {"z": 1, "a": 2}


def test_cli_sort_writes_sorted_nested_keys(tmp_path):
    source = tmp_path / "input.json"
    output = tmp_path / "output.json"
    source.write_text('{"z":1,"a":{"z":2,"a":3}}')
    result = CliRunner().invoke(
        main, ["format", "-i", str(source), "-o", str(output), "--sort"]
    )
    assert result.exit_code == 0, result.output
    data = json.loads(output.read_text())
    assert list(data) == ["a", "z"]
    assert list(data["a"]) == ["a", "z"]


@pytest.mark.parametrize("command", ["format", "minify"])
@pytest.mark.parametrize("same_path", [False, True])
def test_cli_existing_output_fails_without_success_message(command, same_path, tmp_path):
    source = tmp_path / "input.json"
    source.write_text('{"z":1,"a":2}')
    output = source if same_path else tmp_path / "output.json"
    if not same_path:
        output.write_bytes(b"KEEP")
    original = output.read_bytes()
    result = CliRunner().invoke(main, [command, "-i", str(source), "-o", str(output)])
    assert result.exit_code == 1
    assert "Refusing to overwrite" in result.output
    assert "Error:" in result.output
    assert "Traceback" not in result.output
    assert "✅" not in result.output
    assert output.read_bytes() == original
    assert list(tmp_path.glob(".json-toolkit-*.tmp")) == []


@pytest.mark.parametrize("command", ["format", "minify"])
@pytest.mark.parametrize("invalid", [True, False])
def test_cli_bad_input_has_clean_error(command, invalid, tmp_path):
    source = tmp_path / "input.json"
    output = tmp_path / "output.json"
    if invalid:
        source.write_text("not JSON")
    result = CliRunner().invoke(main, [command, "-i", str(source), "-o", str(output)])
    assert result.exit_code == 1
    assert "Error:" in result.output
    assert "Traceback" not in result.output
    assert "✅" not in result.output
    assert not output.exists()


@pytest.mark.parametrize("command", ["format", "minify"])
def test_cli_help_explains_new_output_requirement(command):
    result = CliRunner().invoke(main, [command, "--help"])
    assert result.exit_code == 0
    assert "must not exist" in result.output
