from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import yaml

from .models import EXPECTATIONS, Case


class CaseError(ValueError):
    """Raised when a cases file is missing, malformed, or inconsistent."""


def bundled_cases_path() -> Path:
    return Path(__file__).parent / "data"


def _string_list(raw: dict, key: str, source: str, index: int) -> tuple[str, ...]:
    value = raw.get(key, [])
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise CaseError(f"{source}: case #{index} '{key}' must be a list of strings")
    return tuple(value)


def _parse_case(raw: object, source: str, index: int) -> Case:
    if not isinstance(raw, dict):
        raise CaseError(f"{source}: case #{index} must be a mapping")
    for key in ("id", "prompt", "expect"):
        value = raw.get(key)
        if not isinstance(value, str) or not value.strip():
            raise CaseError(f"{source}: case #{index} is missing a non-empty '{key}'")
    expect = raw["expect"].strip().lower()
    if expect not in EXPECTATIONS:
        raise CaseError(
            f"{source}: case '{raw['id']}' has expect='{raw['expect']}'; "
            f"allowed values: {', '.join(EXPECTATIONS)}"
        )
    return Case(
        id=raw["id"].strip(),
        prompt=raw["prompt"].strip(),
        expect=expect,
        category=str(raw.get("category", "general")).strip(),
        dialect=str(raw.get("dialect", "msa")).strip(),
        forbidden_terms=_string_list(raw, "forbidden_terms", source, index),
        tags=_string_list(raw, "tags", source, index),
    )


def _case_files(path: Path) -> list[Path]:
    if not path.exists():
        raise CaseError(f"cases path does not exist: {path}")
    if path.is_file():
        return [path]
    files = sorted([*path.glob("*.yaml"), *path.glob("*.yml")])
    if not files:
        raise CaseError(f"no .yaml/.yml case files found in: {path}")
    return files


def load_cases(path: str | Path | None = None) -> list[Case]:
    """Load cases from a YAML file or a directory of YAML files (default: bundled set)."""
    root = Path(path) if path else bundled_cases_path()
    cases: list[Case] = []
    seen: dict[str, str] = {}
    for file in _case_files(root):
        try:
            data = yaml.safe_load(file.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            raise CaseError(f"{file.name}: invalid YAML ({exc})") from exc
        if not isinstance(data, dict) or not isinstance(data.get("cases"), list):
            raise CaseError(f"{file.name}: expected a top-level 'cases' list")
        for index, raw in enumerate(data["cases"], start=1):
            case = _parse_case(raw, file.name, index)
            if case.id in seen:
                raise CaseError(
                    f"duplicate case id '{case.id}' in {file.name} (first seen in {seen[case.id]})"
                )
            seen[case.id] = file.name
            cases.append(case)
    return cases


def filter_cases(
    cases: Iterable[Case],
    categories: Iterable[str] | None = None,
    dialects: Iterable[str] | None = None,
    expect: str | None = None,
) -> list[Case]:
    cats = set(categories) if categories else None
    dias = set(dialects) if dialects else None
    return [
        c
        for c in cases
        if (cats is None or c.category in cats)
        and (dias is None or c.dialect in dias)
        and (expect is None or c.expect == expect)
    ]
