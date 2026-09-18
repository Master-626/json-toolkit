"""
Core JSON processing logic.
"""

import json
from pathlib import Path
from typing import Any, Optional


def read_json(file_path: Path) -> Any:
    """Read and parse JSON file."""
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json(file_path: Path, data: Any, indent: int = 2):
    """Write data to JSON file."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=indent, ensure_ascii=False)


def format_json(input_path: str, output_path: str, indent: int = 2, sort_keys: bool = False):
    """Format/minify JSON file with pretty printing."""
    data = read_json(Path(input_path))
    write_json(Path(output_path), data, indent=indent)
    return len(json.dumps(data))


def minify_json(input_path: str, output_path: str):
    """Minify JSON file (remove whitespace)."""
    data = read_json(Path(input_path))
    output_p = Path(output_path)
    output_p.parent.mkdir(parents=True, exist_ok=True)
    with open(output_p, "w", encoding="utf-8") as f:
        json.dump(data, f, separators=(",", ":"), ensure_ascii=False)
    return output_p.stat().st_size


def validate_json(input_path: str) -> tuple[bool, Optional[str]]:
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
