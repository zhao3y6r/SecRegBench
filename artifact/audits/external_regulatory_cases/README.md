# External public regulatory-record audit

This directory contains a reproducible category-level relevance audit for
SecRegBench. It does not turn synthetic scenarios into real cases.

The fixed retrieval searches two official CSRC public channels:

- Hunan Regulatory Bureau administrative supervisory measures;
- central CSRC administrative punishment decisions.

After official-record deduplication and deterministic keyword-category
tagging, the registry contains 1,833 records. It stores only official titles,
URLs, dates, content hashes, fixed query terms, and category evidence terms.
It does not redistribute the decision text.

The audit aligns the benchmark's 11 risk-bearing rule atoms with at least one
official record category. Those atoms control 8,670 benchmark scenarios. The
remaining 1,330 general-education scenarios are associated only with the
separate 85-item official investor-question language proxy.

Permitted interpretation: the designed regulatory trigger categories have
documented public precedents.

Not permitted:

- treating the 10,000 synthetic scenarios as 10,000 real punishment cases;
- treating official decisions as customer-service conversation logs;
- treating category alignment as item-level gold annotation;
- claiming production-traffic representativeness.

Files:

- `official_regulatory_records_v017.jsonl`: URL-level registry and category
  evidence;
- `official_regulatory_case_audit_report_v017.json`: counts, hashes,
  rule-category coverage, and claim boundary.
- `external_style_proxy_report_v013.json`: the fixed aggregate report used
  only to supply the separately audited 85-item official-question proxy count
  and its surface-distance statistics.

Rebuild code:

```bash
node artifact/code/scripts/build_public_regulatory_case_registry_v017.mjs
```

Run the command from the repository root. It refreshes the two
`official_regulatory_*_v017` files in this directory from the fixed official
CSRC searches; it does not download or redistribute the official decision
texts.
