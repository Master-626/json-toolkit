import json

from json_toolkit.core import format_json, validate_json


def test_duplicate_keys_are_valid_by_default_and_last_value_wins(tmp_path):
    source = tmp_path / "dup.json"
    source.write_text('{"a": 1, "a": 2, "nested": {"b": 3, "b": 4}}')
    valid, error = validate_json(str(source))
    assert valid is True
    assert error is None
    output = tmp_path / "out.json"
    format_json(str(source), str(output))
    assert json.loads(output.read_text()) == {"a": 2, "nested": {"b": 4}}


def test_reject_duplicate_keys_reports_the_key(tmp_path):
    source = tmp_path / "dup.json"
    source.write_text('{"keep": 1, "id": 1, "id": 2}')
    valid, error = validate_json(str(source), reject_duplicate_keys=True)
    assert valid is False
    assert error == "Duplicate key 'id'"


def test_reject_duplicate_keys_finds_nested_and_escaped_duplicates(tmp_path):
    nested = tmp_path / "nested.json"
    nested.write_text('{"outer": {"a": 1, "a": 2}}')
    valid, error = validate_json(str(nested), reject_duplicate_keys=True)
    assert valid is False
    assert error == "Duplicate key 'a'"

    escaped = tmp_path / "escaped.json"
    escaped.write_text('{"a": 1, "\\u0061": 2}')
    valid, error = validate_json(str(escaped), reject_duplicate_keys=True)
    assert valid is False
    assert error == "Duplicate key 'a'"


def test_same_key_in_different_objects_is_not_a_duplicate(tmp_path):
    source = tmp_path / "ok.json"
    source.write_text('{"left": {"id": 1}, "right": {"id": 2}, "items": [{"id": 3}]}')
    valid, error = validate_json(str(source), reject_duplicate_keys=True)
    assert valid is True
    assert error is None


def test_duplicate_inside_array_object_is_rejected(tmp_path):
    source = tmp_path / "arr.json"
    source.write_text('[{"id": 1}, {"id": 2, "id": 3}]')
    valid, error = validate_json(str(source), reject_duplicate_keys=True)
    assert valid is False
    assert error == "Duplicate key 'id'"
