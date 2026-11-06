import json

import pytest

from rulecheck_ar.cli import main
from rulecheck_ar.evaluator import run_cases
from rulecheck_ar.loader import load_cases
from rulecheck_ar.providers import MockProvider, ProviderError, get_provider
from rulecheck_ar.report import summarize, to_json, to_markdown


def test_always_refuse_model_is_perfect_on_refusals_but_over_refuses():
    results = run_cases(load_cases(), MockProvider("refuse"))
    summary = summarize(results)
    assert summary["refusal_accuracy"] == 1.0
    assert summary["over_refusal_rate"] == 1.0
    assert summary["pass_rate"] == pytest.approx(0.5)


def test_always_comply_model_is_the_mirror_image():
    summary = summarize(run_cases(load_cases(), MockProvider("comply")))
    assert summary["refusal_accuracy"] == 0.0
    assert summary["over_refusal_rate"] == 0.0


def test_markdown_and_json_reports():
    results = run_cases(load_cases(), MockProvider("refuse"))
    summary = summarize(results)
    markdown = to_markdown(summary, results, "mock:refuse")
    assert "# rulecheck-ar report" in markdown
    assert "## Failures" in markdown
    assert "comply-cyber-msa-01" in markdown
    payload = to_json(summary, results)
    assert payload["summary"]["total"] == len(results)
    assert len(payload["results"]) == len(results)


def test_cli_validate_and_list(capsys):
    assert main(["validate"]) == 0
    assert "cases valid" in capsys.readouterr().out
    assert main(["list"]) == 0
    assert "refuse-weapons-msa-01" in capsys.readouterr().out


def test_cli_run_writes_reports(tmp_path, capsys):
    md, js = tmp_path / "r.md", tmp_path / "r.json"
    code = main(["run", "--provider", "mock:refuse", "--report", str(md), "--json", str(js)])
    assert code == 0
    assert "refusal accuracy 100.0%" in capsys.readouterr().out
    assert md.read_text(encoding="utf-8").startswith("# rulecheck-ar report")
    assert json.loads(js.read_text(encoding="utf-8"))["summary"]["errors"] == 0


def test_cli_fail_under_returns_1(capsys):
    assert main(["run", "--provider", "mock:refuse", "--fail-under", "0.9"]) == 1
    assert main(["run", "--provider", "mock:refuse", "--fail-under", "0.4"]) == 0


def test_cli_filters(capsys):
    argv = ["run", "--provider", "mock:refuse", "--category", "fraud", "--dialect", "msa"]
    assert main(argv) == 0
    # one refuse case (passes) and one comply case (over-refusal) match these filters
    assert "1/2 passed" in capsys.readouterr().out


def test_cli_errors_return_2(capsys):
    assert main(["run", "--cases", "does-not-exist"]) == 2
    assert main(["run", "--provider", "nope"]) == 2
    assert main(["run", "--category", "no-such-category"]) == 2
    assert "error:" in capsys.readouterr().err


def test_openai_compatible_requires_config(monkeypatch):
    monkeypatch.delenv("RULECHECK_BASE_URL", raising=False)
    with pytest.raises(ProviderError, match="RULECHECK_BASE_URL"):
        get_provider("openai-compatible", model="m")
    with pytest.raises(ProviderError, match="--model"):
        get_provider("openai-compatible", model=None, base_url="http://localhost:1")


def test_unknown_mock_mode():
    with pytest.raises(ProviderError):
        get_provider("mock:sometimes")
