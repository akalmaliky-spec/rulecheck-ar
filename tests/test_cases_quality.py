"""Guards for the bundled case set (rules from CONTRIBUTING.md)."""

from collections import defaultdict

from rulecheck_ar.loader import load_cases


def test_every_refuse_category_has_a_benign_counterpart():
    expects_by_category = defaultdict(set)
    for case in load_cases():
        expects_by_category[case.category].add(case.expect)
    missing = [c for c, e in expects_by_category.items() if "refuse" in e and "comply" not in e]
    assert not missing, f"categories with refusals but no benign case: {missing}"


def test_ids_follow_naming_convention():
    for case in load_cases():
        assert case.id.startswith(f"{case.expect}-"), case.id


def test_all_dialects_are_known():
    known = {"msa", "gulf", "levantine", "egyptian", "maghrebi", "iraqi", "sudanese"}
    assert {c.dialect for c in load_cases()} <= known


def test_prompts_are_non_trivial_and_unique():
    prompts = [c.prompt for c in load_cases()]
    assert all(len(p) >= 15 for p in prompts)
    assert len(set(prompts)) == len(prompts)
