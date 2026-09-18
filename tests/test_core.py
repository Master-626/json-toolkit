import pytest
import json
from pathlib import Path
from json_toolkit.core import format_json, minify_json, validate_json, query_path


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
