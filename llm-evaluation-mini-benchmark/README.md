# LLM Evaluation Mini-Benchmark

A reproducible mini-benchmark for comparing language-model responses on structured tasks. Includes 20 prompts, explicit rubrics, deterministic scoring, coding tests, failure analysis, A/B comparison, CSV/JSON exports, a Markdown report, and optional OpenAI-compatible API evaluation.

## Quick start

Requires Python 3.10+. Core benchmark uses only the Python standard library.

```bash
python -m unittest discover -s tests -v
python run_benchmark.py --demo
```

**Important:** `--demo` uses authored illustrative responses to verify the pipeline. Its score is not a real model result and must not be presented as one.

## Evaluate real responses from JSONL

Create a JSONL file with one record per benchmark ID, for example:

```json
{"id":"IF-01","response":"{\"status\":\"ok\",\"count\":3}"}
{"id":"FACT-01","response":"Tokyo"}
```

Run one model:

```bash
python run_benchmark.py --responses model_a.jsonl --model-name "Model A"
```

Compare two models:

```bash
python run_benchmark.py --compare model_a.jsonl model_b.jsonl --names "Model A" "Model B"
```

## Optional live API evaluation

Set environment variables for an OpenAI-compatible chat-completions endpoint. Provider compatibility, cost, rate limits, and data handling vary. Do not send sensitive data.

PowerShell:
```powershell
$env:LLM_BASE_URL="https://your-provider.example/v1"
$env:LLM_API_KEY="your-key"
$env:LLM_MODEL="your-model"
python run_benchmark.py --api --model-name "Your Model"
```

macOS/Linux:
```bash
export LLM_BASE_URL="https://your-provider.example/v1"
export LLM_API_KEY="your-key"
export LLM_MODEL="your-model"
python run_benchmark.py --api --model-name "Your Model"
```

The API mode has not been validated against a live provider in this package.

## What's included

- 20 prompts across instruction following, factuality, reasoning, coding, safety, uncertainty, and summarization.
- Per-item rubrics and machine-readable checks.
- Deterministic scoring and category aggregation.
- Four Python coding tasks tested on edge cases with a timeout.
- JSONL import and optional API runner.
- Detailed CSV/JSON output, Markdown report, and two-model comparison.
- Unit tests, documentation, and limitations.

## Scoring and limitations

Scores are rule-based proxies: exact checks, keyword checks, and deterministic coding tests. Keyword matches can be fooled and cannot establish nuanced factuality or safety. The dataset is small and not statistically representative. Review failures manually, keep prompts/settings identical across models, and record model/provider/version, date, parameters, latency, and cost.

**Security note:** coding submissions execute in a subprocess with a timeout, not a secure sandbox. Only run code you trust. For public or multi-user use, isolate execution in a container or VM with resource limits.

## Suggested improvements

1. Expand to 100+ balanced items per capability.
2. Add independent human ratings and inter-rater agreement.
3. Repeat stochastic runs and report variance/confidence intervals.
4. Record latency and cost.
5. Add domain-specific metrics and robust human review.

## License
MIT; see `LICENSE`.
