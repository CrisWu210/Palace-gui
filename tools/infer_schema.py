#!/usr/bin/env python3
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set


EXAMPLE_DIRS = [
    Path("palace/examples/antenna"),
    Path("palace/examples/coaxial"),
    Path("palace/examples/cpw"),
]


def value_type(value: Any) -> str:
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


def merge_schema(schema: Dict[str, Any], value: Any) -> None:
    schema.setdefault("_types", set()).add(value_type(value))
    if isinstance(value, dict):
        properties = schema.setdefault("properties", {})
        for key, child in value.items():
            child_schema = properties.setdefault(key, {})
            merge_schema(child_schema, child)
    elif isinstance(value, list):
        items_schema = schema.setdefault("items", {})
        for item in value:
            merge_schema(items_schema, item)


def record_paths(
    path: str,
    value: Any,
    file_path: Path,
    path_types: Dict[str, Set[str]],
    path_files: Dict[str, Set[str]],
) -> None:
    path_types[path].add(value_type(value))
    path_files[path].add(file_path.as_posix())
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else key
            record_paths(child_path, child, file_path, path_types, path_files)
    elif isinstance(value, list):
        item_path = f"{path}[]" if path else "[]"
        for item in value:
            record_paths(item_path, item, file_path, path_types, path_files)


def schema_to_json(schema: Dict[str, Any]) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    types = sorted(schema.get("_types", []))
    if types:
        result["type"] = types[0] if len(types) == 1 else types
    if "properties" in schema:
        result["properties"] = {
            key: schema_to_json(child) for key, child in schema["properties"].items()
        }
    if "items" in schema:
        result["items"] = schema_to_json(schema["items"])
    if "required" in schema:
        result["required"] = sorted(schema["required"])
    if "enum" in schema:
        result["enum"] = sorted(schema["enum"])
    if "minItems" in schema:
        result["minItems"] = schema["minItems"]
    return result


def ensure_object(schema: Dict[str, Any]) -> None:
    schema.setdefault("_types", set()).add("object")


def ensure_path(schema: Dict[str, Any], path: Iterable[str]) -> Dict[str, Any]:
    current = schema
    for key in path:
        ensure_object(current)
        properties = current.setdefault("properties", {})
        current = properties.setdefault(key, {})
    return current


def ensure_enum(schema: Dict[str, Any], values: Iterable[str]) -> None:
    schema.setdefault("_types", set()).add("string")
    schema.setdefault("enum", set()).update(values)


def ensure_array(schema: Dict[str, Any]) -> None:
    schema.setdefault("_types", set()).add("array")


def apply_manual_rules(schema: Dict[str, Any]) -> None:
    schema.setdefault("required", set()).update(
        ["Problem", "Model", "Domains", "Boundaries", "Solver"]
    )

    problem_type = ensure_path(schema, ["Problem", "Type"])
    ensure_enum(problem_type, ["Driven", "Transient"])

    sweep_type = ensure_path(schema, ["Solver", "Sweep", "Type"])
    ensure_enum(sweep_type, ["Uniform", "Adaptive"])

    excitations = ensure_path(schema, ["Solver", "Excitations"])
    ensure_array(excitations)

    post_processing = ensure_path(schema, ["Boundaries", "PostProcessing"])
    post_processing.setdefault("required", set()).add("NSample")
    nsample = ensure_path(schema, ["Boundaries", "PostProcessing", "NSample"])
    nsample.setdefault("_types", set()).add("number")


def load_examples(example_dirs: List[Path]) -> Dict[Path, Any]:
    examples = {}
    for example_dir in example_dirs:
        if not example_dir.exists():
            continue
        for json_file in example_dir.rglob("*.json"):
            examples[json_file] = json.loads(json_file.read_text(encoding="utf-8"))
    return examples


def write_report(
    report_path: Path,
    path_types: Dict[str, Set[str]],
    path_files: Dict[str, Set[str]],
) -> None:
    lines = ["# Schema Report", "", "## Key Paths", ""]
    for path in sorted(path_types.keys()):
        types = sorted(path_types[path])
        files = sorted(path_files[path])
        conflict = " (type conflict)" if len(types) > 1 else ""
        lines.append(f"- `{path}`{conflict}")
        lines.append(f"  - Types: {', '.join(types)}")
        lines.append("  - Files:")
        for file_path in files:
            lines.append(f"    - {file_path}")
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    example_dirs = [repo_root / path for path in EXAMPLE_DIRS]
    examples = load_examples(example_dirs)
    if not examples:
        raise SystemExit("No example JSON files found.")

    schema: Dict[str, Any] = {}
    path_types: Dict[str, Set[str]] = defaultdict(set)
    path_files: Dict[str, Set[str]] = defaultdict(set)

    for file_path, data in examples.items():
        merge_schema(schema, data)
        record_paths("", data, file_path.relative_to(repo_root), path_types, path_files)

    apply_manual_rules(schema)

    schema_json = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Palace Examples Schema",
        **schema_to_json(schema),
    }

    schema_dir = repo_root / "schema"
    schema_dir.mkdir(exist_ok=True)

    schema_path = schema_dir / "palace.examples.schema.json"
    schema_path.write_text(
        json.dumps(schema_json, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    report_path = schema_dir / "report.md"
    write_report(report_path, path_types, path_files)


if __name__ == "__main__":
    main()
