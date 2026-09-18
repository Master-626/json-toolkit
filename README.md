# JSON Toolkit

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)

A powerful JSON processing toolkit. Format, minify, validate, and query JSON files from the command line.

## 🌟 Features

- 🎨 **Format** - Pretty print JSON with configurable indentation
- 📦 **Minify** - Compress JSON by removing whitespace
- ✅ **Validate** - Check JSON syntax validity
- 🔍 **Query** - Extract values by dot-separated path (e.g. `user.name`)
- 🐍 **Python API** - Use as a library in your code

## 📦 Installation

```bash
git clone https://github.com/Master-626/json-toolkit.git
cd json-toolkit
pip install .
```

## 🚀 Usage

### Format JSON
```bash
# Pretty print with 2-space indent
json-toolkit format -i raw.json -o pretty.json

# Sort keys alphabetically
json-toolkit format -i raw.json -o sorted.json --sort
```

### Minify JSON
```bash
json-toolkit minify -i pretty.json -o minified.json
```

### Validate JSON
```bash
json-toolkit validate -i data.json
```

### Query Path
```bash
# Get value at path user.address.city
json-toolkit query -i data.json -p "user.address.city"
```

## 🐍 Python API

```python
from json_toolkit import format_json, minify_json, validate_json, query_path

# Format
format_json("input.json", "output.json", indent=2)

# Minify
minify_json("input.json", "minified.json")

# Validate
valid, error = validate_json("input.json")

# Query
value = query_path("input.json", "user.name")
```

## 🧪 Testing

```bash
pip install -e ".[dev]"
pytest
```

## 📄 License

MIT License
