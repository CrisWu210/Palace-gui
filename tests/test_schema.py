import json
from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = REPO_ROOT / "schema" / "palace.examples.schema.json"
EXAMPLE_DIRS = [
    REPO_ROOT / "palace" / "examples" / "antenna",
    REPO_ROOT / "palace" / "examples" / "coaxial",
    REPO_ROOT / "palace" / "examples" / "cpw",
]


def value_type(value):
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return "array"
    return "unknown"


def validate(schema, value, path="$"):
    schema_types = schema.get("type")
    if schema_types:
        allowed = {schema_types} if isinstance(schema_types, str) else set(schema_types)
        actual = value_type(value)
        assert actual in allowed, f"{path}: {actual} not in {sorted(allowed)}"

    if "enum" in schema:
        assert value in schema["enum"], f"{path}: {value} not in {schema['enum']}"

    if isinstance(value, dict):
        required = schema.get("required", [])
        for key in required:
            assert key in value, f"{path}: missing required key '{key}'"
        properties = schema.get("properties", {})
        for key, child in value.items():
            if key in properties:
                validate(properties[key], child, f"{path}.{key}")

    if isinstance(value, list):
        items_schema = schema.get("items")
        if items_schema:
            for index, item in enumerate(value):
                validate(items_schema, item, f"{path}[{index}]")


class TestSchemaExamples(unittest.TestCase):
    def setUp(self):
        self.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    def test_examples_validate(self):
        example_files = []
        for directory in EXAMPLE_DIRS:
            example_files.extend(directory.rglob("*.json"))
        self.assertGreater(len(example_files), 0, "No example JSON files found")
        for example_file in example_files:
            with self.subTest(example=str(example_file)):
                data = json.loads(example_file.read_text(encoding="utf-8"))
                validate(self.schema, data)


if __name__ == "__main__":
    unittest.main()
