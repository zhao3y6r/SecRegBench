# SecRegBench public release notes v0.17-r1

Status: `PUBLIC_RELEASE_V1_READY`

This package is a public projection of the frozen author-side v0.14 artifact.
The v0.17-r1 update adds a public regulatory-record category audit and its
rebuild script. No scenario, split, label, model prediction, or score changed,
and no model was retrained or rerun.

## Integrity

- source complete corpus SHA-256: `a459ea29ab434679e6c59a65704318376e2a1ca548cf0d43e89d4df791cd5bdc`
- public corpus SHA-256: `dc6ec37506c8baa26d23cf55a78a7a23f67f5d04c284233389b00cc340c5d878`
- scientific projection SHA-256: `7250d41e5a460d7e8d7ba800d4dd38957153205dcb70731f0d91b1be529fc614`
- scenarios: 10,000
- development / held-out: 8,000 / 2,000
- realized components: 214

## Removed from the public projection

- internal candidate, task, and review identifiers;
- per-row generator/request/response provenance;
- internal source-artifact paths, source task IDs, and per-event request or
  response hashes;
- historical private selection metadata;
- pre-release status fields;
- raw prompt/request and response payloads;
- model-serving logs, endpoints, server paths, and infrastructure identifiers;
- the nested incremental-runtime archive;
- private candidate/failure ledgers and raw regulatory snapshots.

## Retained

- every scenario ID, dialogue, state, rule-derived label, family, suite,
  component assignment, and split;
- parsed first-generation events and scored predictions;
- graph/split mappings, aggregate reports, audits, code, tests, and licenses;
- 1,833 official supervisory or punishment record references with fixed
  retrieval/category evidence and no copied decision text;
- aggregate, honest disclosure of Qwen and DeepSeek participation.

The public artifact is intentionally suitable for result verification rather
than clean-room reconstruction of private model serving.
