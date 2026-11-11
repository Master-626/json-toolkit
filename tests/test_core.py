import json
from pathlib import Path

import pytest

from json_toolkit.core import format_json, minify_json, query_path, validate_json


@pytest.fixture
def sample_json_file(tmp_path: Path):
    """Create a sample JSON file for testing."""
    data = {
        "name": "Test User",
        "age": 25,
        "address": {
            "city": "Beijing",
            "zip": "100000"
        },
        "tags": ["python", "cli", "json"]
    }
    json_file = tmp_path / "test.json"
    json_file.write_text(json.dumps(data))
    return json_file


def test_format_json(sample_json_file, tmp_path):
    """Test JSON formatting."""
    output = tmp_path / "formatted.json"
    format_json(str(sample_json_file), str(output))
    assert output.exists()


def test_minify_json(sample_json_file, tmp_path):
    """Test JSON minification."""
    output = tmp_path / "minified.json"
    minify_json(str(sample_json_file), str(output))
    content = output.read_text()
    assert "\n" not in content


def test_validate_json(sample_json_file):
    """Test JSON validation."""
    valid, error = validate_json(str(sample_json_file))
    assert valid is True


def test_query_path(sample_json_file):
    """Test JSON path query."""
    result = query_path(str(sample_json_file), "address.city")
    assert result == "Beijing"


def test_format_json_returns_written_utf8_size(tmp_path):
    """The returned size is the formatted file, not a second serialization."""
    source = tmp_path / "input.json"
    output = tmp_path / "output.json"
    source.write_text('{"z":"你好","a":1}', encoding="utf-8")
    parsed = json.loads(source.read_text(encoding="utf-8"))
    size = format_json(str(source), str(output), indent=4, sort_keys=True)
    blob = output.read_bytes()
    assert size == len(blob)
    assert list(json.loads(blob.decode("utf-8"))) == ["a", "z"]
    assert "你好".encode() in blob
    assert size != len(json.dumps(parsed))


def test_minify_keeps_string_spaces_and_reports_bytes(tmp_path):
    source = tmp_path / "input.json"
    output = tmp_path / "output.json"
    source.write_text('{\n  "msg": "a b",\n  "n": 1\n}\n', encoding="utf-8")
    size = minify_json(str(source), str(output))
    blob = output.read_bytes()
    assert blob == b'{"msg":"a b","n":1}'
    assert size == len(blob)


def test_utf8_bom_is_accepted(tmp_path):
    source = tmp_path / "bom.json"
    source.write_bytes(b'\xef\xbb\xbf{"city":"\xe5\x8c\x97\xe4\xba\xac"}')
    valid, error = validate_json(str(source))
    assert valid is True
    assert error is None
    assert query_path(str(source), "city") == "北京"
    output = tmp_path / "out.json"
    format_json(str(source), str(output))
    assert json.loads(output.read_text(encoding="utf-8")) == {"city": "北京"}
    assert not output.read_bytes().startswith(b"\xef\xbb\xbf")


@pytest.mark.parametrize(
    "text",
    ["", "   ", "{", "[1, 2,]", '{"a": 1}{"b": 2}'],
)
def test_validate_rejects_invalid_syntax(tmp_path, text):
    source = tmp_path / "bad.json"
    source.write_text(text)
    valid, error = validate_json(str(source))
    assert valid is False
    assert "JSON decode error at line" in error


def test_validate_reports_decode_location(tmp_path):
    source = tmp_path / "bad.json"
    source.write_text('{\n  "a":\n')
    valid, error = validate_json(str(source))
    assert valid is False
    assert "line 3" in error


def test_validate_missing_file(tmp_path):
    valid, error = validate_json(str(tmp_path / "missing.json"))
    assert valid is False
    assert "No such file" in error


def test_missing_path_and_json_null_both_return_none(tmp_path):
    source = tmp_path / "obj.json"
    source.write_text('{"name": null, "tags": ["x"]}')
    assert query_path(str(source), "name") is None
    assert query_path(str(source), "missing") is None
    assert query_path(str(source), "name.extra") is None
    assert query_path(str(source), "tags.0") == "x"
    assert query_path(str(source), "tags.2") is None


def test_list_indexes_are_canonical_decimal(tmp_path):
    source = tmp_path / "arr.json"
    source.write_text(
        json.dumps({"items": list(range(13)), "1_0": "key", "01": "padded"})
    )
    assert query_path(str(source), "items.0") == 0
    assert query_path(str(source), "items.12") == 12
    assert query_path(str(source), "items.-1") == 12
    assert query_path(str(source), "items.-13") == 0
    assert query_path(str(source), "items.1_0") is None
    assert query_path(str(source), "items.+1") is None
    assert query_path(str(source), "items. 1") is None
    assert query_path(str(source), "items.01") is None
    assert query_path(str(source), "items.-0") is None
    assert query_path(str(source), "items.13") is None
    assert query_path(str(source), "items.-14") is None
    assert query_path(str(source), "1_0") == "key"
    assert query_path(str(source), "01") == "padded"
