# SecRegBench governance and maintenance plan v0.14

## Scope and prohibited uses

SecRegBench is for diagnostic research on regulatory action selection.
Prohibited uses include legal advice, automated investment recommendation,
customer eligibility decisions, production compliance approval, employee
monitoring, and claims that a model is regulator-certified.

## Versioning

Releases use semantic dataset versions. Any change to dialogue, typed state,
rule interpretation, target action, family relation, component mapping, split,
or model ledger creates a new manifest and invalidates prior result bindings.
Corrections never overwrite a published hash.

## Rule and source maintenance

The maintainer records issuer, official URL, retrieval time, content hash,
status, and represented effective interval. A scheduled release review checks
for amended or withdrawn sources. Institution-specific procedure is not inferred
from public rules; contested interpretations are recorded separately from raw
source metadata.

## Corrections and appeals

Reports should identify dataset version, scenario/family ID, disputed field,
supporting source, and proposed correction. Maintainers triage privacy/security
reports before semantic disagreements. Accepted corrections receive a public
change record, affected-hash list, and replacement release; rejected reports
receive a reason without exposing private reporters.

## Incident response and withdrawal

A credible personal-data, credential, redistribution, or harmful-label report
triggers temporary withdrawal of the affected archive where feasible, a scoped
investigation, and a replacement manifest. Old hashes remain documented as
withdrawn and must not be silently reused.

## Deprecation

A version is deprecated when sources materially change, an interpretation is
withdrawn, or a defect changes benchmark conclusions. Deprecation notices state
the successor version and whether old scores remain comparable. Production use
is unsupported in every version.

## Responsibility boundary

Automatic validators, simulated reviews, LLM judges, and anonymous practitioner
review do not replace qualified legal, privacy, institutional, or security
approval. Artifact publishing, license activation, and source/output
redistribution approval remain author responsibilities.
