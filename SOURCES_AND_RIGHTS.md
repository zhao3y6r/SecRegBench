# Data sources, transformations, and rights boundary

## Source classes

The source registry contains 13 public official or self-regulatory sources
issued by:

- the Standing Committee of the National People's Congress;
- the China Securities Regulatory Commission;
- securities, futures, and fund industry associations;
- the Shanghai, Shenzhen, and Beijing stock exchanges.

The registry covers securities law, personal-information protection,
investment-advisory and brokerage rules, suitability, personnel and technology
governance, complaint handling, margin trading, and exchange-specific
suitability or risk-disclosure rules.

The authoritative machine-readable registry is:

[`artifact/data/source_registry.jsonl`](artifact/data/source_registry.jsonl)

Each record provides:

- a project source ID;
- document title and issuer;
- document number and document type where available;
- publication, effective, and amendment dates;
- official government, regulator, association, or exchange URLs;
- scoped article locators and benchmark risk domains;
- the date and basis of source verification.

## What the repository does not copy

This repository does not distribute:

- downloaded PDFs, DOCX files, HTML snapshots, or screenshots from official
  websites;
- a verbatim collection of regulatory clauses;
- subscription, commercial, or internal legal databases;
- proprietary securities-firm policies;
- third-party annotations copied from another benchmark.

Users should follow the official URLs and the applicable terms of each source
publisher when consulting the underlying documents.

## Transformation into benchmark material

Public source metadata informs typed rule atoms and controlled scenario state.
Scenario conversations are synthetic surface realizations. Labels are derived
from the benchmark's frozen rule and priority system rather than copied from a
third-party dataset or assigned by a model judge.

The public release is a field-whitelisted projection of the frozen author-side
corpus. Dialogue, typed state, labels, families, components, and split
assignments are unchanged; private operational provenance is not distributed.

## Rights-holder contact and correction

If a rights holder believes a file reproduces protected content beyond
permitted citation, metadata, or research use, follow
[TAKEDOWN_POLICY.md](TAKEDOWN_POLICY.md). A specific file path, official source
URL, rights basis, and requested remedy will allow a faster review.

