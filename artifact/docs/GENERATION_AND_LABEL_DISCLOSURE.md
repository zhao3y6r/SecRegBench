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
parsed evaluation events, and hashes. It excludes per-row engine markers,
internal task/review identifiers, request payloads, raw responses, endpoints,
serving logs, and private candidate/failure ledgers.

Five anonymous securities compliance practitioners completed the released
500-item validation study. Its high realism result, zero marked material
scenario defects, and low action agreement are reported together. The study
does not convert rule-compiled targets into expert gold, legal certification,
or production approval.
