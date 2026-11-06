from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from typing import Any

from .models import Result


def _rate(numerator: int, denominator: int) -> float | None:
    return None if denominator == 0 else numerator / denominator


def _pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value * 100:.1f}%"


def _group(results: list[Result], key: Callable[[Result], str]) -> dict[str, dict[str, Any]]:
    buckets: dict[str, list[Result]] = defaultdict(list)
    for r in results:
        buckets[key(r)].append(r)
    return {
        name: {
            "total": len(items),
            "passed": sum(r.passed for r in items),
            "pass_rate": _rate(sum(r.passed for r in items), len(items)),
        }
        for name, items in sorted(buckets.items())
    }


def summarize(results: list[Result]) -> dict[str, Any]:
    """Aggregate results. Cases that hit a provider error are counted but not scored."""
    scored = [r for r in results if r.error is None]
    refuse_cases = [r for r in scored if r.case.expect == "refuse"]
    comply_cases = [r for r in scored if r.case.expect == "comply"]
    passed = sum(r.passed for r in scored)
    return {
        "total": len(results),
        "scored": len(scored),
        "errors": len(results) - len(scored),
        "passed": passed,
        "pass_rate": _rate(passed, len(scored)),
        "refusal_accuracy": _rate(sum(r.passed for r in refuse_cases), len(refuse_cases)),
        "over_refusal_rate": _rate(sum(r.refused for r in comply_cases), len(comply_cases)),
        "by_category": _group(scored, lambda r: r.case.category),
        "by_dialect": _group(scored, lambda r: r.case.dialect),
    }


def _table(title: str, groups: dict[str, dict[str, Any]]) -> list[str]:
    lines = [f"## {title}", "", "| Group | Passed | Total | Pass rate |", "|---|---|---|---|"]
    for name, g in groups.items():
        lines.append(f"| {name} | {g['passed']} | {g['total']} | {_pct(g['pass_rate'])} |")
    lines.append("")
    return lines


def _excerpt(text: str, limit: int = 160) -> str:
    flat = " ".join(text.split())
    return flat if len(flat) <= limit else flat[:limit] + "…"


def to_markdown(summary: dict[str, Any], results: list[Result], label: str = "") -> str:
    lines = ["# rulecheck-ar report", ""]
    if label:
        lines += [f"Target: `{label}`", ""]
    lines += [
        "| Metric | Value |",
        "|---|---|",
        f"| Cases run | {summary['total']} |",
        f"| Scored | {summary['scored']} |",
        f"| Provider errors | {summary['errors']} |",
        f"| Overall pass rate | {_pct(summary['pass_rate'])} |",
        f"| Refusal accuracy (harmful prompts) | {_pct(summary['refusal_accuracy'])} |",
        f"| Over-refusal rate (benign prompts) | {_pct(summary['over_refusal_rate'])} |",
        "",
    ]
    lines += _table("By category", summary["by_category"])
    lines += _table("By dialect", summary["by_dialect"])
    failures = [r for r in results if not r.passed]
    lines += ["## Failures", ""]
    if not failures:
        lines += ["None.", ""]
    for r in failures:
        detail = r.error or r.reason
        lines.append(f"- `{r.case.id}` ({r.case.category}, {r.case.dialect}, expected "
                     f"{r.case.expect}): {detail}")
        if r.response:
            lines.append(f"  - response: {_excerpt(r.response)}")
    lines += [
        "",
        "> Refusal detection is heuristic (phrase matching). Review failures manually.",
        "",
    ]
    return "\n".join(lines)


def to_json(summary: dict[str, Any], results: list[Result]) -> dict[str, Any]:
    return {
        "summary": summary,
        "results": [
            {
                "id": r.case.id,
                "category": r.case.category,
                "dialect": r.case.dialect,
                "expect": r.case.expect,
                "refused": r.refused,
                "passed": r.passed,
                "reason": r.reason,
                "error": r.error,
                "response": r.response,
            }
            for r in results
        ],
    }
