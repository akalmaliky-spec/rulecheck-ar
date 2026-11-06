import pytest

from rulecheck_ar.loader import CaseError, filter_cases, load_cases


def _write(tmp_path, text, name="cases.yaml"):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def test_bundled_cases_load_and_are_balanced():
    cases = load_cases()
    assert len(cases) >= 20
    expects = {c.expect for c in cases}
    assert expects == {"refuse", "comply"}
    assert len({c.id for c in cases}) == len(cases)
    assert {"msa", "gulf", "levantine", "egyptian", "maghrebi"} <= {c.dialect for c in cases}


def test_defaults_applied(tmp_path):
    path = _write(tmp_path, "cases:\n  - {id: a, prompt: hi, expect: Comply}\n")
    (case,) = load_cases(path)
    assert case.expect == "comply"
    assert case.category == "general"
    assert case.dialect == "msa"


@pytest.mark.parametrize(
    "body, message",
    [
        ("cases:\n  - {id: a, expect: refuse}\n", "'prompt'"),
        ("cases:\n  - {id: a, prompt: x, expect: maybe}\n", "allowed values"),
        ("cases:\n  - {id: a, prompt: x, expect: refuse, tags: oops}\n", "'tags'"),
        ("not_cases: []\n", "top-level 'cases'"),
        ("cases:\n  - just a string\n", "mapping"),
    ],
)
def test_invalid_files_raise(tmp_path, body, message):
    with pytest.raises(CaseError, match=message):
        load_cases(_write(tmp_path, body))


def test_duplicate_ids_across_files(tmp_path):
    _write(tmp_path, "cases:\n  - {id: a, prompt: x, expect: refuse}\n", "one.yaml")
    _write(tmp_path, "cases:\n  - {id: a, prompt: y, expect: comply}\n", "two.yaml")
    with pytest.raises(CaseError, match="duplicate case id 'a'"):
        load_cases(tmp_path)


def test_missing_path_and_empty_dir(tmp_path):
    with pytest.raises(CaseError, match="does not exist"):
        load_cases(tmp_path / "nope")
    with pytest.raises(CaseError, match="no .yaml"):
        load_cases(tmp_path)


def test_filter_cases():
    cases = load_cases()
    gulf = filter_cases(cases, dialects=["gulf"])
    assert gulf and all(c.dialect == "gulf" for c in gulf)
    refuse_fraud = filter_cases(cases, categories=["fraud"], expect="refuse")
    assert refuse_fraud
    assert all(c.category == "fraud" and c.expect == "refuse" for c in refuse_fraud)
