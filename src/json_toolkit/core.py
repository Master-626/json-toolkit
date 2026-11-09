"""
Core JSON processing logic.
"""

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any, Optional, Tuple


def read_json(file_path: Path) -> Any:
    """Read and parse JSON file."""
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_text_exclusively(file_path: Path, text: str) -> int:
    """Publish a complete UTF-8 file without replacing any existing path.

    A sibling temporary file is linked into place only after writing succeeds.
    Filesystems without hard-link support fail safely, without a partial output.
    """
    payload = text.encode("utf-8")
    exists_message = (
        f"Refusing to overwrite existing output: {file_path}. "
        "Choose a new output path."
    )
    if os.path.lexists(str(file_path)):
        raise FileExistsError(exists_message)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None
    published = False
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=str(file_path.parent),
            prefix=".json-toolkit-",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            temporary.write(payload)
            temporary.flush()
            os.fsync(temporary.fileno())
        try:
            os.link(str(temporary_path), str(file_path))
        except FileExistsError as error:
            raise FileExistsError(exists_message) from error
        published = True
    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink()
            except FileNotFoundError:
                pass
            except OSError as error:
                logging.getLogger(__name__).warning(
                    "%s; could not remove temporary file %s: %s",
                    f"Output saved to {file_path}" if published else "Output not saved",
                    temporary_path,
                    error,
                )
    return len(payload)


def write_json(
    file_path: Path, data: Any, indent: int = 2, *, sort_keys: bool = False
):
    """Write JSON to a new path, refusing to overwrite existing files or links."""
    text = json.dumps(data, indent=indent, ensure_ascii=False, sort_keys=sort_keys)
    _write_text_exclusively(Path(file_path), text)


def format_json(input_path: str, output_path: str, indent: int = 2, sort_keys: bool = False):
    """Pretty-print JSON to a new output path, optionally sorting all object keys."""
    data = read_json(Path(input_path))
    write_json(Path(output_path), data, indent=indent, sort_keys=sort_keys)
    return len(json.dumps(data))


def minify_json(input_path: str, output_path: str):
    """Minify JSON to a new output path and return its UTF-8 byte count."""
    data = read_json(Path(input_path))
    text = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
    return _write_text_exclusively(Path(output_path), text)


def validate_json(input_path: str) -> Tuple[bool, Optional[str]]:
    """Validate JSON file syntax."""
    try:
        read_json(Path(input_path))
        return True, None
    except json.JSONDecodeError as e:
        return False, f"JSON decode error at line {e.lineno}, col {e.colno}: {e.msg}"
    except Exception as e:
        return False, str(e)


def query_path(input_path: str, path: str) -> Any:
    """Query JSON by dot-separated path (e.g. 'user.name')."""
    data = read_json(Path(input_path))

    keys = path.split(".")
    current = data

    for key in keys:
        if isinstance(current, dict):
            if key not in current:
                return None
            current = current[key]
        elif isinstance(current, list):
            try:
                idx = int(key)
                current = current[idx]
            except (ValueError, IndexError):
                return None
        else:
            return None

    return current
