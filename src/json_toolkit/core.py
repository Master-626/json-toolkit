"""
Core JSON processing logic.
"""

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any, Optional, Tuple


def _reject_duplicate_pairs(pairs: list) -> dict:
    """Build an object and reject a key that appears more than once."""
    data = {}
    for key, value in pairs:
        if key in data:
            raise ValueError(f"Duplicate key {key!r}")
        data[key] = value
    return data


def _canonical_list_index(key: str) -> Optional[int]:
    """Return a list index when ``key`` is its canonical decimal spelling.

    ``int("1_0")`` is ``10``, and ``int()`` also accepts spaces, a leading
    ``+``, and leading zeros. Those strings are not path indexes.
    """
    try:
        index = int(key, 10)
    except ValueError:
        return None
    if str(index) != key:
        return None
    return index


def _escape_unpaired_surrogates(text: str) -> str:
    """Replace unpaired surrogates with JSON ``\\uXXXX`` escapes."""
    pieces = []
    start = 0
    for index, char in enumerate(text):
        code = ord(char)
        if 0xD800 <= code <= 0xDFFF:
            pieces.append(text[start:index])
            pieces.append(f"\\u{code:04x}")
            start = index + 1
    pieces.append(text[start:])
    return "".join(pieces)


def _dumps_json(data: Any, **kwargs: Any) -> str:
    """Serialize JSON as text that can be encoded with UTF-8.

    Non-ASCII characters are preserved. Unpaired surrogates, which UTF-8 cannot
    store, are written with JSON ``\\uXXXX`` escapes.
    """
    kwargs.setdefault("ensure_ascii", False)
    text = json.dumps(data, **kwargs)
    try:
        text.encode("utf-8")
    except UnicodeEncodeError:
        text = _escape_unpaired_surrogates(text)
    return text


def _encode_utf8(text: str) -> bytes:
    """Encode JSON text as UTF-8, escaping unpaired surrogates if needed."""
    try:
        return text.encode("utf-8")
    except UnicodeEncodeError:
        return _escape_unpaired_surrogates(text).encode("utf-8")


def read_json(file_path: Path, *, reject_duplicate_keys: bool = False) -> Any:
    """Read and parse a JSON file.

    A leading UTF-8 byte-order mark is accepted. When ``reject_duplicate_keys``
    is true, a repeated key in the same object raises ``ValueError`` instead of
    keeping the last value.
    """
    load_options = {}
    if reject_duplicate_keys:
        load_options["object_pairs_hook"] = _reject_duplicate_pairs
    with open(file_path, encoding="utf-8-sig") as handle:
        return json.load(handle, **load_options)


def _write_text_exclusively(file_path: Path, text: str) -> int:
    """Publish a complete UTF-8 file without replacing any existing path.

    A sibling temporary file is linked into place only after writing succeeds.
    Filesystems without hard-link support fail safely, without a partial output.
    """
    payload = _encode_utf8(text)
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
) -> int:
    """Write JSON to a new path, refusing to overwrite existing files or links.

    Returns the UTF-8 byte count of the file written.
    """
    text = _dumps_json(data, indent=indent, sort_keys=sort_keys)
    return _write_text_exclusively(Path(file_path), text)


def format_json(
    input_path: str, output_path: str, indent: int = 2, sort_keys: bool = False
) -> int:
    """Pretty-print JSON to a new output path, optionally sorting all object keys.

    Returns the UTF-8 byte count of the file written.
    """
    data = read_json(Path(input_path))
    return write_json(Path(output_path), data, indent=indent, sort_keys=sort_keys)


def minify_json(input_path: str, output_path: str) -> int:
    """Minify JSON to a new output path and return its UTF-8 byte count."""
    data = read_json(Path(input_path))
    text = _dumps_json(data, separators=(",", ":"))
    return _write_text_exclusively(Path(output_path), text)


def validate_json(
    input_path: str, *, reject_duplicate_keys: bool = False
) -> Tuple[bool, Optional[str]]:
    """Validate JSON file syntax.

    Returns ``(True, None)`` when the file parses. By default a repeated key is
    accepted and the last value wins. Set ``reject_duplicate_keys`` to reject it.
    """
    try:
        read_json(Path(input_path), reject_duplicate_keys=reject_duplicate_keys)
        return True, None
    except json.JSONDecodeError as error:
        return (
            False,
            f"JSON decode error at line {error.lineno}, col {error.colno}: {error.msg}",
        )
    except Exception as error:
        return False, str(error)


def query_path(input_path: str, path: str) -> Any:
    """Query JSON by dot-separated path (e.g. ``user.name`` or ``tags.0``).

    A missing path and a JSON null both return ``None``. List indexes must be
    canonical decimal integers such as ``0`` or ``-1``; ``-1`` is the last item.
    """
    data = read_json(Path(input_path))

    keys = path.split(".")
    current = data

    for key in keys:
        if isinstance(current, dict):
            if key not in current:
                return None
            current = current[key]
        elif isinstance(current, list):
            index = _canonical_list_index(key)
            if index is None:
                return None
            try:
                current = current[index]
            except IndexError:
                return None
        else:
            return None

    return current
