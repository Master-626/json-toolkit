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


def test_cli_validate_exit_codes(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{")
    result = CliRunner().invoke(main, ["validate", "-i", str(bad)])
    assert result.exit_code == 1
    assert "Invalid JSON" in result.output
    assert "line 1" in result.output
    assert "Traceback" not in result.output
    assert "Aborted" not in result.output

    missing = CliRunner().invoke(main, ["validate", "-i", str(tmp_path / "missing.json")])
    assert missing.exit_code == 1
    assert "Invalid JSON" in missing.output
    assert "Traceback" not in missing.output

    good = tmp_path / "bom.json"
    good.write_bytes(b'\xef\xbb\xbf{"ok": true}')
    result = CliRunner().invoke(main, ["validate", "-i", str(good)])
    assert result.exit_code == 0
    assert "Valid JSON" in result.output


def test_cli_validate_reject_duplicates(tmp_path):
    source = tmp_path / "dup.json"
    source.write_text('{"id": 1, "id": 2}')
    default = CliRunner().invoke(main, ["validate", "-i", str(source)])
    assert default.exit_code == 0
    assert "Valid JSON" in default.output

    strict = CliRunner().invoke(
        main, ["validate", "-i", str(source), "--reject-duplicates"]
    )
    assert strict.exit_code == 1
    assert "Duplicate key 'id'" in strict.output
    assert "Traceback" not in strict.output

    clean = tmp_path / "clean.json"
    clean.write_text('{"left": {"id": 1}, "right": {"id": 2}}')
    accepted = CliRunner().invoke(
        main, ["validate", "-i", str(clean), "--reject-duplicates"]
    )
    assert accepted.exit_code == 0
    assert "Valid JSON" in accepted.output


def test_cli_validate_help_mentions_duplicate_option():
    result = CliRunner().invoke(main, ["validate", "--help"])
    assert result.exit_code == 0
    assert "--reject-duplicates" in result.output


def test_cli_query_prints_json_and_hides_tracebacks(tmp_path):
    source = tmp_path / "input.json"
    source.write_text('{"user":{"name":"你好"},"tags":["a","b"]}', encoding="utf-8")
    found = CliRunner().invoke(main, ["query", "-i", str(source), "-p", "user.name"])
    assert found.exit_code == 0
    assert found.output.strip() == '"你好"'
    last = CliRunner().invoke(main, ["query", "-i", str(source), "-p", "tags.-1"])
    assert last.exit_code == 0
    assert json.loads(last.output) == "b"

    bad = CliRunner().invoke(main, ["query", "-i", str(source), "-p", "tags.1_0"])
    assert bad.exit_code == 0
    assert bad.output.strip() == "null"

    invalid = tmp_path / "bad.json"
    invalid.write_text("{")
    failed = CliRunner().invoke(main, ["query", "-i", str(invalid), "-p", "a"])
    assert failed.exit_code == 1
    assert "Error:" in failed.output
    assert "Traceback" not in failed.output

    missing = CliRunner().invoke(
        main, ["query", "-i", str(tmp_path / "missing.json"), "-p", "a"]
    )
    assert missing.exit_code == 1
    assert "Error:" in missing.output
    assert "Traceback" not in missing.output


def test_cli_query_unpaired_surrogate_is_utf8(tmp_path):
    source = tmp_path / "input.json"
    source.write_text('{"bad":"\\ud800"}', encoding="utf-8")
    result = CliRunner().invoke(main, ["query", "-i", str(source), "-p", "bad"])
    assert result.exit_code == 0, result.output
    assert result.output.strip() == '"\\ud800"'
    assert "Traceback" not in result.output


def test_cli_minify_reports_utf8_size(tmp_path):
    source = tmp_path / "input.json"
    output = tmp_path / "output.json"
    source.write_text('{"city":"北京"}', encoding="utf-8")
    result = CliRunner().invoke(main, ["minify", "-i", str(source), "-o", str(output)])
    assert result.exit_code == 0, result.output
    assert f"({output.stat().st_size} bytes)" in result.output
