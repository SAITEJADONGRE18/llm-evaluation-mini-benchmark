# Project Evaluation Summary

## Project
**LLM Evaluation Mini-Benchmark**

## Objective
Build a reproducible mini-benchmark to evaluate language-model responses using structured prompts, transparent rubrics, automated scoring, failure analysis, model comparisons, and a concise report.

## Implemented
- 20 prompts across instruction following, factuality, reasoning, coding, safety, uncertainty, and summarization.
- Per-item rubrics and machine-readable expected checks.
- Deterministic scoring functions and per-category aggregation.
- Four Python coding tasks tested against deterministic edge-case input/output sets with a timeout.
- JSONL import for actual model outputs.
- Optional OpenAI-compatible chat-completions API runner.
- CSV and JSON results, Markdown evaluation report, and two-model comparison outputs.
- Unit tests, setup instructions, limitations, and MIT license.

## Evidence boundary
The bundled demo uses authored illustrative responses only to verify the scoring pipeline. Its score is **not a real model evaluation**. A genuine model comparison requires running the same benchmark against actual model endpoints or importing their real outputs.

## Known limitations
- Only 20 prompts; results are not statistically representative.
- Several non-coding checks use keyword/format heuristics and can be fooled by superficial matches.
- Safety/factuality require human review; lexical scoring alone is insufficient.
- Coding tests cover selected cases only. The subprocess timeout is not a secure sandbox.
- API mode requires provider credentials and has not been validated against a live endpoint in this package.
- No confidence intervals or repeated sampling are included.

## Reproduction
```bash
python -m unittest discover -s tests -v
python run_benchmark.py --demo
```
