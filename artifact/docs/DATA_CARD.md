# SecRegBench v0.21 public data card

## Summary

SecRegBench is a synthetic Chinese benchmark for selecting one operational
action—`ANSWER`, `CLARIFY`, `REFUSE`, or `ESCALATE`—in securities
customer-service scenarios. It is a diagnostic benchmark, not legal advice,
investment recommendation, automated approval, or production certification.

## Composition

- 10,000 scenarios and 5,750 controlled families
- six suites: benign hard negatives, compositional OOD, counterfactual,
  institution role, multi-turn, and temporal
- 6,965 normalized dialogue surfaces
- 9,250 unique dialogue-state pairs
- 6,337 lexical edges and 214 realized components
- largest component: 300 rows; inverse-HHI effective count: 67.75
- 8,000 development and 2,000 held-out rows
- 59 held-out components and zero frozen-component crossing
- held-out suite counts: 457 / 283 / 420 / 320 / 200 / 320
- held-out actions: 877 `ANSWER`, 229 `CLARIFY`, 646 `REFUSE`,
  248 `ESCALATE`

## Public record fields

Each JSONL row contains:

- scenario, family, suite, split, and component identifiers;
- decision date and dialogue turns;
- typed jurisdiction, institution, assistant, customer, suitability, product,
  interaction, data, and market-integrity state;
- rule-derived target action, acceptable actions, severity, and rule IDs;
- controlled-family relation metadata; and
- dialogue and split-protocol hashes/versions.

The public projection excludes internal candidate/review/task IDs, per-row
generator identifiers, request/response provenance, historical private
selection metadata, and pre-release status. These exclusions do not alter any
dialogue, state, label, split, family, suite, or component assignment.

## Construction and labels

Thirteen official-source registry entries feed 48 attributed evidence excerpts
and 12 executable rule atoms. The release includes the exact short excerpts
used in oracle-evidence prompts, their locators and official URLs, but not full
regulatory snapshots or documents. Action labels are produced by the
executable rule layer; surface models do not judge the labels.

Each of 5,750 families received three label-blind Qwen surface candidates.
DeepSeek V4 later produced 102 label-blind diversity-repair candidates for 34
families; 34 candidates covering 72 rows were selected by frozen structural
and lexical criteria. The public artifact records these facts in aggregate,
without per-row engine or internal request identifiers.

Five anonymous securities compliance practitioners reviewed 500 frozen items.
Fifty common items received five judgments each and 450 additional items
received one judgment each, for 700 judgments. Shared-item action pairwise
agreement was 100% (Fleiss kappa 1.0). Across all 500 items, practitioner
actions matched the rule-compiled primary action on 77.8%, mean realism was
4.01/5, and 7 items were marked as materially defective (1.4%; Wilson 95% CI
0.7--2.9%). The benchmark targets remain rule-compiled operational-policy
outputs, not legal certification or production approval.

A separate five-practitioner study reviewed the same 100 items in an
independent first round: 50 stratified random items and 50 challenge items.
Action Fleiss kappa was 0.852 across all 100, and modal actions matched
rule-derived labels on 90% of the stratified random half. Thirty-four disputed
or flagged items entered a Delphi round that disclosed the current rule action
and public evidence. It confirmed 15 labels, revised 10, and retained 9 as
unresolved, yielding 91 high-confidence reference items. This adjudication
overlay is distributed separately and does not silently rewrite the original
10,000 rule-derived labels.

## Evaluation evidence

The package includes parsed first-generation events and scored rows for:

- Qwen3.5-35B-A3B-GPTQ-Int4: 8,000 predictions;
- Qwen2.5-7B-Instruct: 8,000 predictions;
- the served `deepseek-v4-flash` identifier: 8,000 predictions;
- four information views over the same 2,000 held-out scenarios;
- a development-only keyword log-odds baseline; and
- 10,000-draw component-bootstrap reports over 59 held-out components.

The package also includes 700 deidentified practitioner judgments, 500
item-level aggregates, the frozen statistical report, and a verifier. No
practitioner name, employer, or contact information is distributed.

For the 100-item adjudication layer, only aggregate vote counts and final
statuses are distributed. Raw cards, reviewer-level answers, reviewer slots,
free-text reasons, names, employers, contacts, signatures, and participation
documents are excluded. Existing model predictions are rescored under the nine
high-confidence held-out label revisions; no model is rerun.

Event rows contain parsed actions, usage totals, and non-sensitive run
metadata. The exact evaluation instruction, evidence inputs, deterministic
request compiler, provider-neutral runner, parser, scorer, and tests are
included. Raw provider responses, endpoints, credentials, and model-serving
logs are excluded.

## Public projection integrity

- author-side complete corpus SHA-256: `a459ea29ab434679e6c59a65704318376e2a1ca548cf0d43e89d4df791cd5bdc`
- public JSONL SHA-256: `dc6ec37506c8baa26d23cf55a78a7a23f67f5d04c284233389b00cc340c5d878`
- public scientific-projection SHA-256:
  `7250d41e5a460d7e8d7ba800d4dd38957153205dcb70731f0d91b1be529fc614`

`audits/PUBLIC_PROJECTION_EQUIVALENCE_V016.json` verifies that all 10,000
scenario IDs and every distributed scientific field are identical to the
projection of the frozen author-side corpus.

## Privacy and source-text checks

Automatic scans cover all 10,000 scenarios and 16,000 dialogue turns for
configured high-risk identifier and credential patterns. A separate audit
checks exact normalized overlap at a 24-character threshold against the
author-side 48-clause registry. Neither scan proves absence of all personal
information, paraphrase, legal risk, or redistribution constraints.

No production customer conversation, raw regulatory snapshot, practitioner
identity, credential, or private infrastructure record is included.

## Known limitations

- The corpus is synthetic and does not estimate customer-traffic frequencies.
- The 457 benign held-out rows occupy five components and 23 authoring blocks.
- The rules cover a designed slice of public mainland-China securities
  materials rather than comprehensive law.
- Evaluation covers three checkpoint identities from two model families
  (Qwen and DeepSeek); the primary Qwen checkpoint generated much of the
  surface text.
- Five-way action agreement is estimated only on 50 shared items; 450 items
  have a single practitioner judgment.
- Seven validation items are materially flagged and remain distributed; three
  are in held-out.
- The expert-adjudication layer contains 91 high-confidence items and 9
  unresolved items. Its 50 challenge items are not a random population sample.
- Round-two rule acceptance is not an independent validation estimate because
  reviewers saw the current rule action and public evidence.
- State and evidence are supplied as oracle inputs.
- Public held-out labels permit transparent reproduction but are unsuitable as
  a permanently secret leaderboard.

## Licensing

Code is released under Apache-2.0. Synthetic data and accompanying non-code
artifact material are released under CC BY-NC 4.0. Model weights, raw source
snapshots, and third-party full text are excluded.
