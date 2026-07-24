# Reproduce the four-view evaluation

This directory contains the exact frozen system instruction and the 48 short
official-clause excerpts used as oracle evidence inputs. The compiler combines
them with the public held-out scenarios and rule atoms to reconstruct 8,000
label-free requests (2,000 scenarios × four information views).

From `artifact/`:

```bash
python code/scripts/compile_evaluation_requests_v020.py \
  data/secregbench_public_v014.jsonl \
  data/rule_atoms.jsonl \
  evaluation/evidence_inputs_v020.jsonl \
  evaluation/system_prompt_zh_v020.txt \
  run_outputs/compiled \
  --model YOUR_MODEL_ID
```

Safe local validation without network access:

```bash
python code/scripts/run_openai_compatible_evaluation_v020.py \
  run_outputs/compiled/evaluation_jobs.jsonl \
  run_outputs/compiled/evaluation_requests.jsonl \
  run_outputs/model_run \
  --mode dry-run \
  --model YOUR_MODEL_ID
```

Actual inference requires an OpenAI-compatible chat-completions URL supplied
with `--endpoint` and a key in `SECREGBENCH_API_KEY`. Start with `--mode
canary`; use `--mode batch` only after checking the canary. Set
`--profile deepseek-json` only for a service that accepts the corresponding
thinking-control field.

Score a completed run:

```bash
python code/scripts/score_provisional_evaluation_v012.py \
  data/secregbench_public_v014.jsonl \
  run_outputs/compiled/evaluation_jobs.jsonl \
  run_outputs/model_run/events_private.jsonl \
  run_outputs/scored
```

To include the frozen development-only keyword baseline in the same report,
append:

```bash
  --keyword-baseline-report scores/keyword_baseline/report.json \
  --keyword-baseline-predictions scores/keyword_baseline/predictions.jsonl
```

The keyword report records both the frozen author-side corpus hash and the
verified public-projection corpus hash. The scorer accepts either binding and
always verifies the supplied prediction file by SHA-256.

The versioned scorer is the complete scorer used for the released results. It
computes accuracy, macro-F1, unsafe fulfilment, service denial, non-answer
rates, component-bootstrap intervals, pair comparisons, and trajectory
diagnostics.

Request reconstruction is exact at the scientific-input level: scenario,
dialogue, typed state, evidence, method, and model-facing request content.
The reconstructed job-ledger byte hash can differ from the older private run
ledger because the public compiler uses a versioned public schema and excludes
private operational metadata. Scoring equivalence is checked through job
identifiers, model-input hashes, predictions, and reported metrics rather than
requiring those two ledger files to be byte-identical.

## Publication boundary

Safe to publish here:

- the exact system instruction;
- the exact short evidence excerpts and their official URLs;
- the deterministic request compiler;
- the provider-neutral runner, parser, scorer, metrics, and verification tests.

Not included:

- API keys, private endpoints, server addresses, or absolute server paths;
- raw provider responses, response headers, or internal serving metadata;
- model weights or third-party full documents.

The project licenses do not relicense third-party laws, regulations, official
documents, model software, or model weights. Evidence excerpts are included
for research traceability with attribution to their official sources.
