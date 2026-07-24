# SecRegBench v0.14 public research artifact

Status: `PUBLIC_RELEASE_V1_READY`

SecRegBench is a synthetic Chinese benchmark for deciding whether a
securities customer-service assistant should `ANSWER`, `CLARIFY`, `REFUSE`, or
`ESCALATE` under typed regulatory and conversational state.

This public package contains:

- a 10,000-row UTF-8 JSONL benchmark with dialogue, state, rule-derived action
  labels, family/suite membership, realized components, and the fixed
  8,000/2,000 split;
- source/rule metadata without raw regulatory snapshots or verbatim clauses;
- graph and split mappings;
- two sanitized 8,000-event model ledgers and scored predictions;
- aggregate construction, repair, scoring, privacy, overlap, and diversity
  reports;
- a fixed external audit of 1,833 official supervisory or punishment records,
  stored as titles, URLs, dates, hashes, and deterministic category evidence
  without copied decision text;
- selected scoring/audit code, tests, documentation, and a self-contained
  verifier.

The public JSONL is a projection of the frozen author-side corpus. Only
operational fields such as internal candidate/task identifiers, per-row model
generation markers, historical private provenance, and pre-release status were
removed. Scenario IDs, dialogue text, typed state, rule-derived labels,
families, suites, component IDs, and split assignments are unchanged.

It does **not** contain credentials, API endpoints, server addresses, absolute
server paths, raw prompt/request payloads, raw model response payloads, model
weights, private candidate/failure ledgers, raw regulatory snapshots,
practitioner identities, or production customer data.

## Verify

From the extracted package root:

```bash
python code/verify_public_artifact_v016.py .
```

Expected status:

```text
PASS_PUBLIC_ARTIFACT_V016
```

The verifier checks manifest hashes, public-field policy, row cardinalities,
UTF-8 decoding, split/component isolation, action counts, exact
event/scored-ledger correspondence, selected metrics, and prohibited
operational markers. It verifies the fixed public artifact; it does not rerun
model inference or reconstruct private generation infrastructure.

## Generative provenance

The state/rule design and action labels are not model-judged. Locally served
Qwen checkpoints generated label-blind surface candidates. DeepSeek V4
generated 102 label-blind diversity-repair candidates for 34 families; 34
candidates covering 72 of 10,000 rows were selected by frozen structural and
lexical criteria. Per-row engine/request/response identifiers are intentionally
not distributed. See `docs/GENERATION_AND_LABEL_DISCLOSURE.md`.

## Layout

- `data/`: public corpus, schema, rule/source metadata, graph and split
- `events/`: parsed event ledgers containing only job ID, parsed action,
  parse status, generation number, error status, and token counts
- `scores/`: scored rows, reports, baseline, and corrected diagnostics
- `audits/`: quality, privacy, overlap, projection-equivalence, statistics,
  and the external public regulatory-record category audit; run its rebuild
  script from the repository root
- `provenance/`: aggregate generation and repair counts only
- `code/`: selected analysis/scoring code, tests, and verifier
- `docs/`: data card, governance, practitioner scope, licenses, and disclosure

## Licenses

- project code: Apache License 2.0
- synthetic benchmark data and accompanying non-code artifact material:
  Creative Commons Attribution-NonCommercial 4.0 International
  (`CC BY-NC 4.0`)

See `LICENSE` for the scope and official license links.
