# SecRegBench v0.21 public research artifact

Status: `PUBLIC_RELEASE_V3_READY`

SecRegBench is a synthetic Chinese benchmark for deciding whether a
securities customer-service assistant should `ANSWER`, `CLARIFY`, `REFUSE`, or
`ESCALATE` under typed regulatory and conversational state.

This public package contains:

- a 10,000-row UTF-8 JSONL benchmark with dialogue, state, rule-derived action
  labels, family/suite membership, realized components, and the fixed
  8,000/2,000 split;
- source/rule metadata and 48 attributed evidence excerpts without full
  regulatory snapshots;
- a category-level audit of 1,833 public CSRC supervisory or punishment
  records, with titles, official URLs, dates, hashes, and category evidence;
- graph and split mappings;
- three sanitized 8,000-event model ledgers and scored predictions;
- deidentified practitioner-validation evidence: 700 judgments over 500
  frozen items, item aggregates, statistical report, and verifier;
- a deidentified 100-item expert-adjudication overlay with aggregate votes,
  91 high-confidence references, 10 label revisions, 9 unresolved items, and
  saved-prediction rescoring without new inference;
- aggregate construction, repair, scoring, privacy, overlap, and diversity
  reports;
- the exact evaluation instruction, deterministic request compiler,
  provider-neutral runner, full scorer, tests, documentation, and verifier.

The public JSONL is a projection of the frozen author-side corpus. Only
operational fields such as internal candidate/task identifiers, per-row model
generation markers, historical private provenance, and pre-release status were
removed. Scenario IDs, dialogue text, typed state, rule-derived labels,
families, suites, component IDs, and split assignments are unchanged.

It does **not** contain credentials, API endpoints, server addresses, absolute
server paths, raw provider responses, model weights, private candidate/failure
ledgers, full regulatory snapshots, practitioner identities, or production
customer data.

## Verify

From the extracted package root:

```bash
python code/verify_public_artifact_v020.py .
python code/verify_expert_adjudication_v021.py
```

Expected status:

```text
PASS_PUBLIC_ARTIFACT_V021
```

The verifier checks manifest hashes, public-field policy, row cardinalities,
UTF-8 decoding, split/component isolation, action counts, exact
event/scored-ledger correspondence, selected metrics, the deidentified
practitioner study, and prohibited operational markers. It also reconstructs
all 8,000 held-out requests and confirms their job identifiers. It does not
rerun model inference.

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
- `validation/`: deidentified practitioner judgments, item aggregates, and
  statistical report, plus the aggregate-only expert-adjudication overlay
- `evaluation/`: exact prompt, evidence inputs, and reconstruction guide
- `audits/`: quality, privacy, overlap, projection-equivalence, and statistics
- `provenance/`: aggregate generation and repair counts only
- `code/`: compiler, runner, parser, scorer, analyses, tests, and verifier
- `docs/`: data card, governance, practitioner scope, licenses, and disclosure

## Licenses

- project code: Apache License 2.0
- synthetic benchmark data and accompanying non-code artifact material:
  Creative Commons Attribution-NonCommercial 4.0 International
  (`CC BY-NC 4.0`)

See `LICENSE` for the scope and official license links.
