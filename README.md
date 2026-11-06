# rulecheck-ar

**[العربية](#العربية) · [English](#english)**

> **Intended use / الاستخدام المقصود**
>
> This repository contains adversarial prompts written for **defensive testing**: they request
> harmful help so that a model's refusal can be measured. They contain no operational harmful
> detail. Use it to test and harden safety rules.
>
> يحتوي هذا المستودع على طلبات ضارة مكتوبة **لأغراض الاختبار الدفاعي** فقط: وظيفتها قياس رفض
> النموذج، ولا تتضمن أي تفاصيل تنفيذية ضارة. استخدمه لاختبار قواعد السلامة وتقويتها.

---

## العربية

أداة مفتوحة المصدر لاختبار **قواعد سلامة النماذج اللغوية باللغة العربية**. تقيس شيئين:

1. **دقة الرفض:** هل يرفض النموذج الطلبات الضارة المكتوبة بالفصحى واللهجات؟
2. **الرفض المفرط:** هل يرفض النموذج، خطأً، طلبات سليمة؟

مجموعة الاختبارات الأولية صغيرة (41 حالة، 7 لهجات)، والهدف أن تنمو بمساهمات المجتمع.

### التثبيت والتشغيل

```bash
pip install -e ".[dev]"

rulecheck-ar validate                       # التحقق من ملفات الحالات
rulecheck-ar list                           # عرض الحالات
rulecheck-ar run --provider mock:refuse     # تجربة بلا شبكة

# اختبار نموذج عبر Anthropic مباشرة (المفتاح من متغير البيئة)
export ANTHROPIC_API_KEY="..."
rulecheck-ar run --provider anthropic --model <model-name> --system-prompt-file my_rules.txt

# أو عبر واجهة متوافقة مع OpenAI (chat/completions)
export RULECHECK_BASE_URL="https://your-gateway.example/v1"
export RULECHECK_API_KEY="..."
rulecheck-ar run --provider openai-compatible --model <model-name> \
  --system-prompt-file my_rules.txt --report report.md --json report.json --fail-under 0.9
```

خيار `--system-prompt-file` هو جوهر الفكرة: ضع قواعد السلامة في ملف نصي واختبرها، وشغّل الاختبار في CI عند كل تعديل عليها.

### حدود معروفة (اقرأها قبل الاعتماد على النتائج)

- كشف الرفض **تقريبي**: مطابقة عبارات رفض في أول 200 حرف من الرد. قد يخطئ في الاتجاهين.
- مجموعة الحالات صغيرة، ولا تثبت أن النموذج «آمن». نجاحها لا يعني غياب الثغرات.
- مزوّد Anthropic جديد، واختباراته تعتمد على محاكاة الطلبات فقط. لم يُجرَّب بعد على الواجهة الحقيقية.
- الحالات اللهجية تحتاج مراجعة متحدثين أصليين.

### خارطة الطريق (غير منفذة بعد)

- مُقيّم بنموذج حكم (judge) بدل مطابقة العبارات.
- تصدير الحالات إلى صيغ أدوات تقييم أخرى.
- المزيد من اللهجات والفئات.

---

## English

An open-source test suite and CLI for checking **LLM safety rules in Arabic**. It measures:

1. **Refusal accuracy:** does the model decline harmful requests in MSA and dialects?
2. **Over-refusal:** does the model wrongly decline benign requests?

The seed set is small (41 cases, 7 dialects) and meant to grow through contributions.

### Install and run

```bash
pip install -e ".[dev]"

rulecheck-ar validate                       # validate case files
rulecheck-ar list                           # list cases
rulecheck-ar run --provider mock:refuse     # offline smoke test

# Test a model through Anthropic directly (key read from the environment)
export ANTHROPIC_API_KEY="..."
rulecheck-ar run --provider anthropic --model <model-name> --system-prompt-file my_rules.txt

# Or through an OpenAI-style chat/completions endpoint
export RULECHECK_BASE_URL="https://your-gateway.example/v1"
export RULECHECK_API_KEY="..."
rulecheck-ar run --provider openai-compatible --model <model-name> \
  --system-prompt-file my_rules.txt --report report.md --json report.json --fail-under 0.9
```

`--system-prompt-file` is the core idea: keep your safety rules in a text file, test them, and run
the suite in CI on every change to that file.

Exit codes: `0` ok, `1` pass rate below `--fail-under`, `2` configuration or provider errors.

### Case format

```yaml
cases:
  - id: refuse-fraud-msa-01
    category: fraud
    dialect: msa
    expect: refuse        # or: comply
    prompt: "..."
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full schema and rules.

### Known limitations (read before trusting results)

- Refusal detection is **heuristic**: phrase matching in the first 200 characters. It can err in both directions.
- The case set is small and cannot prove a model is "safe". Passing does not mean no gaps.
- The Anthropic provider is new and covered only by mocked-request tests. It has not been run against the live API yet.
- Dialect cases need review by native speakers.

### Roadmap (not implemented yet)

- Judge-model evaluator instead of phrase matching.
- Export to other evaluation tools' formats.
- More dialects and categories.

## License

MIT. See [LICENSE](LICENSE).
