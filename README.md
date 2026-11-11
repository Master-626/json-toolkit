# JSON Toolkit

## 简介

json-toolkit 是一个轻量的 JSON 工具：可在命令行或 Python 中格式化、压缩、校验，并按点号路径取值。输出只会写到还不存在的路径；如果目标已经是文件、目录或链接，命令会失败而不会覆盖。支持 Python 3.8 及以上。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![Tests](https://github.com/Master-626/json-toolkit/actions/workflows/tests.yml/badge.svg)](https://github.com/Master-626/json-toolkit/actions/workflows/tests.yml)

Format, minify, validate, and query JSON from the command line or from Python. Parsing uses the standard library. Click is the only runtime dependency.

## Features

- **Format** — pretty-print JSON with a configurable indent, and optionally sort object keys
- **Minify** — remove insignificant whitespace and report the UTF-8 size
- **Validate** — check syntax, and optionally reject repeated object keys
- **Query** — read a value at a dot-separated path such as `user.address.city` or `tags.0`
- **Python API** — call the same operations from `json_toolkit`

## Installation

Python 3.8 or newer is required.

```bash
git clone https://github.com/Master-626/json-toolkit.git
cd json-toolkit
pip install .
```

The install adds two equivalent commands, `json-toolkit` and `jtk`.

```bash
json-toolkit --help
json-toolkit --version
```

Install the test and lint extras while developing:

```bash
pip install -e ".[dev]"
```

## Usage

### Format

```bash
# Pretty-print with the default 2-space indent
json-toolkit format -i raw.json -o pretty.json

# 4-space indent and alphabetical keys at every object
json-toolkit format -i raw.json -o sorted.json --indent 4 --sort
```

| Option | Description |
| --- | --- |
| `-i`, `--input` | Input JSON file (required) |
| `-o`, `--output` | Output path (required, and it must not already exist) |
| `--indent` | Number of indentation spaces (default `2`) |
| `--sort` | Sort keys alphabetically in every object |

`format` exits 0 after the new file is written. A syntax or I/O error exits 1 and does not leave an output file behind.

### Minify

```bash
json-toolkit minify -i pretty.json -o minified.json
```

| Option | Description |
| --- | --- |
| `-i`, `--input` | Input JSON file (required) |
| `-o`, `--output` | Output path (required, and it must not already exist) |

The success message includes the UTF-8 byte size of the new file. Spaces inside strings stay; only insignificant JSON whitespace is removed. Key order is preserved.

### Validate

```bash
json-toolkit validate -i data.json
json-toolkit validate -i data.json --reject-duplicates
```

| Option | Description |
| --- | --- |
| `-i`, `--input` | Input JSON file (required) |
| `--reject-duplicates` | Fail when one object repeats a key |

The exit status is 0 when the file is valid and 1 when it is not, including when the path is missing or unreadable. A repeated key is valid by default, and formatting or minifying that file keeps the last value. `--reject-duplicates` names the repeated key and exits 1.

A leading UTF-8 BOM is accepted. Python's parser also accepts `NaN` and `Infinity`; this tool reports those files as valid even though those tokens are not strict JSON.

### Query

```bash
json-toolkit query -i data.json -p "user.address.city"
json-toolkit query -i data.json -p "tags.-1"
```

| Option | Description |
| --- | --- |
| `-i`, `--input` | Input JSON file (required) |
| `-p`, `--path` | Dot-separated path (required) |

Each segment is an object key. When the current value is an array, the segment must be a canonical decimal index such as `0`, `12`, or `-1` (the last item). `01`, `+1`, `1_0`, and indexes that contain spaces do not match. A missing path prints `null` and exits 0, the same result as a stored JSON `null`. Syntax and I/O errors exit 1. The printed value is JSON, with non-ASCII characters left unescaped.

## Output safety

`format`, `minify`, and the Python `write_json` helper require a **new output
path**. They raise an error instead of replacing an existing file, directory,
symbolic link (including a broken link), or hard link. Input and output cannot
be the same file. Choose a different output filename to keep the original safe.
This deliberately changes the previous behavior, which silently overwrote files.

Output is serialized and written to a sibling temporary file before being
published with an exclusive hard link. Write failures do not expose a partial
output, and a destination created by another process is not overwritten.
The destination filesystem must support hard links; otherwise the command fails
without replacing anything. This is not a power-loss durability guarantee or
protection against an attacker changing parent directories. A process killed
before cleanup may leave a `.json-toolkit-*.tmp` file beside the destination.
If temporary-file cleanup fails, a warning identifies the file to remove and
whether output was saved. On POSIX systems, new output files have private `0600`
permissions; adjust them explicitly if another account needs access.

## Python API

```python
from json_toolkit import format_json, minify_json, validate_json, query_path

# Each write returns the UTF-8 byte count of the new file.
format_json("input.json", "output.json", indent=2)
format_json("input.json", "sorted.json", sort_keys=True)

size = minify_json("input.json", "minified.json")

valid, error = validate_json("input.json")
valid, error = validate_json("input.json", reject_duplicate_keys=True)

value = query_path("input.json", "user.name")
last = query_path("input.json", "tags.-1")
```

`format_json` and `minify_json` raise `FileExistsError` when the output path already exists. They raise `json.JSONDecodeError`, `UnicodeError`, or `OSError` when the input cannot be read. `validate_json` returns `(False, message)` for those problems instead of raising. `query_path` returns `None` when a segment does not match, including when the stored value is JSON `null`.

## Testing

```bash
pip install -e ".[dev]"
python -m ruff check .
python -m pytest
```

GitHub Actions runs those two commands on Python 3.8 through 3.13.

## License

MIT License
