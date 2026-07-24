# Expert adjudication protocol

This release adds a separate, deidentified expert-adjudication layer over 100
SecRegBench scenarios. It does not silently replace the rule-derived labels in
the 10,000-row corpus.

## Participants and sampling

Five anonymous securities compliance practitioners independently reviewed the
same 100 scenarios. The frozen sample contained:

- 50 fresh items stratified across split and suite;
- 43 fresh held-out challenge items selected by deterministic model-error and
  prediction-disagreement criteria; and
- 7 items previously marked as potentially defective in the earlier
  500-item validation.

The challenge half is deliberately enriched for hard cases. Aggregate
agreement over all 100 items is useful for adjudication, but only the
stratified random half supports a descriptive rule-match estimate.

## Round one: independent validation

Reviewers saw the dialogue and typed state, but not the rule-derived target,
model prediction, sampling group, or another reviewer's answer. For every
item, each reviewer selected `ANSWER`, `CLARIFY`, `REFUSE`, or `ESCALATE`,
rated confidence from 1 to 5, and marked whether the item had a material
defect.

Across all 100 items, action Fleiss kappa was 0.852, 77% were unanimous, and
94% had at least four of five reviewers selecting the same action. The modal
action matched the rule-derived primary action on 90% of the stratified random
50 and 77% of all 100.

## Round two: Delphi adjudication

Thirty-four items entered round two if at least one of the following held:

1. first-round actions were not unanimous;
2. the modal action was outside the current rule-acceptable action set; or
3. at least one reviewer marked a material defect.

For these items, reviewers saw anonymized first-round vote counts, their own
first-round answer, the current rule action, and a short attributed public-rule
excerpt. They then selected a final action, accepted or rejected the current
rule action, and rated confidence. A rejection required a short reason.

The frozen decision rule was:

- high-confidence confirmation: at least four of five reviewers select the
  current rule action, at least four accept it, and median confidence is at
  least 4;
- high-confidence revision: at least four select a different action, at least
  four reject the current rule action, and median confidence is at least 4;
- unresolved: fewer than four select one action, or median confidence is below
  4.

Round two confirmed 15 labels, revised 10, and left 9 unresolved. Combined
with 66 round-one-stable items, the released reference layer contains 91
high-confidence items.

## Reporting boundary

Round one is independent practitioner-validation evidence. Round two is
Delphi adjudication after disclosure of the current rule action and evidence;
its rule-acceptance rate is therefore **not** an independent accuracy
estimate.

The public release includes scenario-level aggregate vote counts, final
statuses, and saved-prediction rescoring. It excludes raw answer cards,
reviewer-level judgments, reviewer slots, free-text reasons, names, employers,
contacts, signatures, and participation documents.
