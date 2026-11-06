from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .evaluator import run_cases
from .loader import CaseError, filter_cases, load_cases
from .providers import ProviderError, get_provider
from .report import _pct, summarize, to_json, to_markdown

EXIT_OK = 0
EXIT_BELOW_THRESHOLD = 1
EXIT_ERROR = 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="rulecheck-ar",
        description="Check LLM safety rules with Arabic test cases (refusals and over-refusals).",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="run cases against a model")
    run.add_argument("--cases", help="YAML file or directory (default: bundled cases)")
    run.add_argument(
        "--provider",
        default="mock:refuse",
        help="mock:refuse | mock:comply | openai-compatible | anthropic (default: mock:refuse)",
    )
    run.add_argument("--model", help="model name (required for openai-compatible and anthropic)")
    run.add_argument(
        "--base-url",
        help="API base URL (openai-compatible: or RULECHECK_BASE_URL; anthropic: optional gateway)",
    )
    run.add_argument("--system-prompt-file", help="text file sent as the system prompt")
    run.add_argument("--category", action="append", help="only run this category (repeatable)")
    run.add_argument("--dialect", action="append", help="only run this dialect (repeatable)")
    run.add_argument("--report", help="write a Markdown report to this path")
    run.add_argument("--json", dest="json_path", help="write a JSON report to this path")
    run.add_argument(
        "--fail-under",
        type=float,
        default=0.0,
        help="exit 1 if the overall pass rate (0-1) is below this value (default: 0)",
    )

    validate = sub.add_parser("validate", help="validate case files")
    validate.add_argument("--cases", help="YAML file or directory (default: bundled cases)")

    lst = sub.add_parser("list", help="list cases")
    lst.add_argument("--cases", help="YAML file or directory (default: bundled cases)")
    return parser


def _cmd_validate(args: argparse.Namespace) -> int:
    cases = load_cases(args.cases)
    print(f"OK: {len(cases)} cases valid")
    return EXIT_OK


def _cmd_list(args: argparse.Namespace) -> int:
    for case in load_cases(args.cases):
        print(f"{case.id}\t{case.expect}\t{case.category}\t{case.dialect}")
    return EXIT_OK


def _cmd_run(args: argparse.Namespace) -> int:
    cases = filter_cases(load_cases(args.cases), args.category, args.dialect)
    if not cases:
        raise CaseError("no cases match the given filters")
    system_prompt = None
    if args.system_prompt_file:
        system_prompt = Path(args.system_prompt_file).read_text(encoding="utf-8")
    provider = get_provider(
        args.provider, model=args.model, base_url=args.base_url, system_prompt=system_prompt
    )
    results = run_cases(cases, provider)
    summary = summarize(results)
    label = args.provider + (f" / {args.model}" if args.model else "")

    if args.report:
        Path(args.report).write_text(to_markdown(summary, results, label), encoding="utf-8")
    if args.json_path:
        Path(args.json_path).write_text(
            json.dumps(to_json(summary, results), ensure_ascii=False, indent=2), encoding="utf-8"
        )

    print(
        f"{summary['passed']}/{summary['scored']} passed ({_pct(summary['pass_rate'])}) | "
        f"refusal accuracy {_pct(summary['refusal_accuracy'])} | "
        f"over-refusal {_pct(summary['over_refusal_rate'])} | errors {summary['errors']}"
    )
    if summary["errors"] or summary["pass_rate"] is None:
        return EXIT_ERROR
    if summary["pass_rate"] < args.fail_under:
        return EXIT_BELOW_THRESHOLD
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    handlers = {"run": _cmd_run, "validate": _cmd_validate, "list": _cmd_list}
    try:
        return handlers[args.command](args)
    except (CaseError, ProviderError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_ERROR


if __name__ == "__main__":
    raise SystemExit(main())
