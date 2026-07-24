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
- public rule and source metadata with links to 13 official sources;
- a fixed category-level audit of 1,833 official CSRC supervisory or
  punishment records, plus the existing 85-item official investor-question
  language proxy;
- two sanitized 8,000-event model ledgers and 16,000 scored rows;
- aggregate construction, privacy, overlap, diversity, and evaluation reports;
- selected scoring and audit code, tests, documentation, and a verifier.

The exact frozen release is under [`artifact/`](artifact/). Its public corpus
SHA-256 is:

```text
dc6ec37506c8baa26d23cf55a78a7a23f67f5d04c284233389b00cc340c5d878
```

The original release ZIP has SHA-256:

```text
efb4a3f10de734632b727b5d76a136668a05c901f6b428e78bbce6763cd061b8
```

## Verify

From the repository root:

```bash
python artifact/code/verify_public_artifact_v016.py artifact
python -m unittest discover -s artifact/code/tests -p "test_*.py" -v
```

The verifier checks hashes, row counts, field whitelists, split isolation,
event/scored-row correspondence, selected metrics, and prohibited operational
metadata. It does not rerun model inference.

## Data origin

All scenario conversations are synthetic. Benchmark state and action targets
are constructed from a typed rule system informed by public mainland-China
securities laws, regulatory rules, self-regulatory guidance, and exchange
rules. The repository distributes source titles, issuers, dates, article
locators, and official URLs. It does **not** redistribute raw regulatory
snapshots, full source documents, or verbatim clause collections.

Three anonymous securities-industry reviewers familiar with production
customer-service records across multiple brokerages reviewed the design, rule
interpretations, label logic, and corpus examples. This establishes a
practitioner realism check, not that production conversations are included in
the public corpus.

The external audit aligns 11 risk-bearing rule atoms, controlling 8,670
scenarios, with at least one official regulatory-record category. The remaining
1,330 general-education scenarios use only the 85-item official-page language
proxy. Category alignment does not make a synthetic scenario a real
enforcement case or an item-level gold record. See
[`artifact/audits/external_regulatory_cases/`](artifact/audits/external_regulatory_cases/).

See [SOURCES_AND_RIGHTS.md](SOURCES_AND_RIGHTS.md) and
[`artifact/data/source_registry.jsonl`](artifact/data/source_registry.jsonl).

## Privacy and publication boundary

The release contains no raw production customer conversation, customer identifier,
credential, private server address, API key, raw prompt/request payload, raw
model response payload, model weight, or named practitioner record. Per-row
generation-engine and internal workflow identifiers have been removed.

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
