# Generation and label disclosure

## What models did

- Locally served Qwen checkpoints generated label-blind candidate dialogue
  surfaces and were later evaluated as benchmark subjects.
- DeepSeek V4 generated 102 label-blind diversity-repair candidates for 34
  families. Frozen structural and lexical criteria selected 34 candidates
  covering 72 of the 10,000 rows.
- OpenAI Codex assisted with code, audits, analysis, documentation, and
  manuscript preparation.

## What models did not do

- Models did not define the 12 executable rule atoms.
- Models did not receive or select the target action label during surface
  generation.
- Model-judged language quality or downstream accuracy did not select the
  published candidate.
- Models did not replace the disclosed practitioner review.

## Public provenance boundary

The package provides aggregate generation/repair counts, scientific content,
parsed evaluation events, hashes, the exact evaluation instruction, the
evidence inputs, and the complete request/compiler/runner/scorer harness. It
excludes per-row generation-engine markers, internal task/review identifiers,
raw provider responses, endpoints, serving logs, and private candidate/failure
ledgers.

Five anonymous securities compliance practitioners completed the released
500-item validation study. The released result includes 100% action agreement
on the 50 shared items, 77.8% target match across 500 items, 4.01/5 mean
realism, and all seven material-defect flags. The study does not convert
rule-compiled targets into legal certification or production approval.
