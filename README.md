# SecRegBench

SecRegBench is a synthetic Chinese benchmark for evaluating whether a
securities customer-service assistant should `ANSWER`, `CLARIFY`, `REFUSE`, or
`ESCALATE` under changing regulatory, institutional, customer, and dialogue
state.

This repository is the public research artifact accompanying:

> SecRegBench: Stateful Regulatory Action Evaluation for Securities
> Customer-Service Assistants

## What is included

- 10,000 synthetic scenarios in 5,750 families;
- a fixed 8,000/2,000 component-disjoint development/held-out split;
- public rule/source metadata and 48 attributed evidence excerpts from 13
  official sources;
- a fixed category-level audit of 1,833 official CSRC supervisory or
  punishment records, plus the existing 85-item official investor-question
  language proxy;
- three sanitized 8,000-event model ledgers and 24,000 scored rows;
- 700 deidentified practitioner judgments over 500 frozen items, with item
  aggregates, a statistical report, and a deterministic verifier;
- aggregate construction, privacy, overlap, diversity, and evaluation reports;
- the exact evaluation system instruction, deterministic request compiler,
  provider-neutral runner, full scorer, tests, documentation, and a verifier.

The exact frozen release is under [`artifact/`](artifact/). Its public corpus
SHA-256 is:

```text
dc6ec37506c8baa26d23cf55a78a7a23f67f5d04c284233389b00cc340c5d878
```

The release revision and every payload hash are recorded in
[`artifact/ARTIFACT_MANIFEST.json`](artifact/ARTIFACT_MANIFEST.json) and
[`artifact/SHA256SUMS.txt`](artifact/SHA256SUMS.txt).

## Verify

From the repository root:

```bash
python artifact/code/verify_public_artifact_v020.py artifact
python -m unittest discover -s artifact/code/tests -p "test_*.py" -v
```

The verifier checks hashes, row counts, field whitelists, split isolation,
three-model event/scored-row correspondence, selected metrics, the
deidentified practitioner study, and prohibited operational metadata. It does
not rerun model inference.

## Data origin

All scenario conversations are synthetic. Benchmark state and action targets
are constructed from a typed rule system informed by public mainland-China
securities laws, regulatory rules, self-regulatory guidance, and exchange
rules. The repository distributes source titles, issuers, dates, article
locators, and official URLs. It does **not** redistribute raw regulatory
snapshots, full source documents, or verbatim clause collections.

Five anonymous securities compliance practitioners reviewed 500 frozen items:
50 received five-way review and 450 one review each, yielding 700 judgments.
On the shared items, action agreement was 100% (Fleiss kappa 1.0). Across all
500 items, practitioner actions matched the rule-compiled target on 77.8%,
mean realism was 4.01/5, and 7 items (1.4%) were marked as materially
defective. The complete deidentified result is released; it does not make the
rule-compiled targets legal certification or production approval.

The external audit aligns 11 risk-bearing rule atoms, controlling 8,670
scenarios, with at least one official regulatory-record category. The remaining
1,330 general-education scenarios use only the 85-item official-page language
proxy. Category alignment does not make a synthetic scenario a real
enforcement case or an item-level gold record. See
[`artifact/audits/external_regulatory_cases/`](artifact/audits/external_regulatory_cases/).

See [SOURCES_AND_RIGHTS.md](SOURCES_AND_RIGHTS.md) and
[`artifact/data/source_registry.jsonl`](artifact/data/source_registry.jsonl).

## Privacy and publication boundary

The release contains no raw production customer conversation, customer
identifier, credential, private server address, API key, raw provider response,
model weight, or named practitioner record. It intentionally includes the
exact evaluation instruction, evidence inputs, and request-building/evaluation
code. Per-row generation-engine and internal workflow identifiers have been
removed.

Aggregate use of Qwen, DeepSeek V4, and OpenAI Codex is disclosed in
[`artifact/docs/GENERATION_AND_LABEL_DISCLOSURE.md`](artifact/docs/GENERATION_AND_LABEL_DISCLOSURE.md).
Model identities are retained only where necessary to interpret construction
or experimental results.

## Licenses and responsible use

- Code under `artifact/code/`: Apache License 2.0.
- Synthetic benchmark data and non-code artifact materials:
  CC BY-NC 4.0.
- Third-party laws, regulations, official documents, model software, and model
  weights are not relicensed or redistributed by this repository.

See [LICENSE.md](LICENSE.md), [NOTICE.md](NOTICE.md), and
[TAKEDOWN_POLICY.md](TAKEDOWN_POLICY.md).

This artifact is for diagnostic research. It is not legal advice, investment
advice, an automated eligibility decision, or evidence that a model or
institution is regulator-certified.

## Reporting problems

- Data, source, licensing, or rights concern:
  use the **Rights or data issue** template.
- Security concern: follow [SECURITY.md](SECURITY.md) and do not post secrets
  in a public issue.
- Corrections should identify the release version and affected scenario,
  family, source, or file.
