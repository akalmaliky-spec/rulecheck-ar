# Contributing / المساهمة

## Adding test cases (the most valuable contribution)

Cases live in `src/rulecheck_ar/data/*.yaml`. Each case has:

| Field | Required | Notes |
|---|---|---|
| `id` | yes | Unique, e.g. `refuse-fraud-gulf-02` |
| `prompt` | yes | The user message |
| `expect` | yes | `refuse` or `comply` |
| `category` | no | e.g. `fraud`, `cyber_misuse`, `medical_info` |
| `dialect` | no | `msa`, `gulf`, `levantine`, `egyptian`, `maghrebi`, … |
| `forbidden_terms` | no | Words that must not appear in the response |
| `tags` | no | Free-form labels |

Rules for cases:

1. **Defensive only.** Prompts may *ask* for harmful help so we can check refusals, but must not
   contain operational harmful details (recipes, working exploit code, real targets).
2. **No real people, accounts, or personal data.**
3. **Every harmful (`refuse`) case needs a nearby benign (`comply`) case** in the same category,
   so over-refusal is measured too.
4. **Dialect cases should be reviewed by a native speaker** of that dialect. Say so in the PR.
5. Do not copy prompts from other benchmarks unless their license allows it; credit the source.

## Development

```bash
pip install -e ".[dev]"
ruff check .
rulecheck-ar validate
pytest
```

Refusal markers live in `src/rulecheck_ar/evaluator.py`. A new marker must come with a test in
`tests/test_evaluator.py` showing both a refusal it catches and a normal answer it must not flag.
