# SecRegBench public release notes v0.21-r1

Status: `PUBLIC_RELEASE_V3_READY`

This revision adds a deidentified, aggregate-only expert-adjudication overlay
over 100 scenarios. The independent first round obtains action Fleiss kappa
0.852 and 90% modal-action match on a stratified random 50. A 34-item Delphi
round confirms 15 labels, revises 10, and leaves 9 unresolved, producing 91
high-confidence references.

Nine revised labels occur in held-out. All three model ledgers are rescored
from saved predictions under this overlay; no model inference, training, or
API call is repeated. The original 10,000 rule-derived labels remain intact,
and the expert overlay is versioned separately.

Raw answer cards, reviewer-level judgments, reviewer slots, free-text reasons,
identities, signatures, and participation documents are excluded.

This revision replaces the stale practitioner projection with the complete
latest five-practitioner result: 700 judgments over 500 frozen items, 100%
action agreement on the 50 shared items, 77.8% match to rule-compiled targets,
4.01/5 mean realism, and all seven material-defect flags. It also adds the
exact evaluation system instruction, 48 attributed evidence inputs, a
deterministic request compiler, a provider-neutral OpenAI-compatible runner,
the full scorer, and end-to-end verification.

The public keyword-baseline scoring path now binds the frozen baseline report
to both the author-side corpus and its verified public projection, and exposes
the public prediction filename used by the scorer. The evaluation guide also
distinguishes exact scientific-input reconstruction from byte-identical
reconstruction of an older private job ledger.

No model was retrained or rerun for this revision. A sensitivity analysis
uses existing predictions and shows that excluding the three flagged held-out
items changes any reported accuracy, macro-F1, or unsafe-fulfilment point
estimate by at most 0.074 percentage points.

## Integrity

- source complete corpus SHA-256: `a459ea29ab434679e6c59a65704318376e2a1ca548cf0d43e89d4df791cd5bdc`
- public corpus SHA-256: `dc6ec37506c8baa26d23cf55a78a7a23f67f5d04c284233389b00cc340c5d878`
- scientific projection SHA-256: `7250d41e5a460d7e8d7ba800d4dd38957153205dcb70731f0d91b1be529fc614`
- scenarios: 10,000
- development / held-out: 8,000 / 2,000
- realized components: 214

## Excluded from the public projection

- internal candidate, task, and review identifiers;
- per-row generator/request/response provenance;
- internal source-artifact paths, source task IDs, and per-event request or
  response hashes;
- historical private selection metadata;
- pre-release status fields;
- raw provider response payloads;
- model-serving logs, endpoints, server paths, and infrastructure identifiers;
- the nested incremental-runtime archive;
- private candidate/failure ledgers and raw regulatory snapshots.

## Retained

- every scenario ID, dialogue, state, rule-derived label, family, suite,
  component assignment, and split;
- parsed first-generation events and scored predictions;
- graph/split mappings, aggregate reports, audits, code, tests, and licenses;
- exact evaluation prompt/evidence inputs and the complete evaluation harness;
- aggregate, honest disclosure of Qwen and DeepSeek participation.

The artifact supports clean reconstruction of the label-free model inputs and
all scoring steps. It does not reconstruct private model-serving
infrastructure.
