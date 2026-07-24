#!/usr/bin/env python3
"""Build a hash-bound v0.14 primary/secondary held-out comparison table."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


EXPECTED_REPORT_STATUS = "PASS_MACHINE_STAGE_SCORING_PROVISIONAL_NOT_HUMAN_VALIDATED_NOT_DATASET"
EXPECTED_MATERIALIZATION_STATUS = (
    "PASS_EXACT_REUSE_PLUS_INCREMENTAL_FIRST_GENERATION_MATERIALIZATION"
)
EXPECTED_CORPUS_SHA256 = "a459ea29ab434679e6c59a65704318376e2a1ca548cf0d43e89d4df791cd5bdc"
EXPECTED_JOBS_SHA256 = "3856bd94b831191b853c8542496afbb8d670ffbbad90759a9c3d82787fbccc79"
METHODS = (
    ("dialogue_only", "Dialogue"),
    ("state_only", "State"),
    ("oracle_evidence", "Evidence"),
    ("state_oracle_evidence", "State+evidence"),
)
METRICS = (
    "accuracy",
    "macro_f1",
    "unsafe_fulfilment_rate",
    "non_answer_rate_on_answer",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def extract_rows(report: dict, model_label: str) -> list[dict]:
    results = report.get("results")
    if not isinstance(results, dict):
        raise ValueError("evaluation report lacks results")
    rows: list[dict] = []
    for method, view_label in METHODS:
        method_result = results.get(method)
        if not isinstance(method_result, dict):
            raise ValueError(f"evaluation report lacks method: {method}")
        heldout = method_result.get("heldout")
        if not isinstance(heldout, dict):
            raise ValueError(f"evaluation report lacks heldout metrics: {method}")
        if heldout.get("n") != 2000:
            raise ValueError(f"{method}: expected 2,000 held-out rows, observed {heldout.get('n')}")
        values = {}
        for metric in METRICS:
            value = heldout.get(metric)
            if not isinstance(value, (int, float)) or not 0 <= float(value) <= 1:
                raise ValueError(f"{method}: invalid {metric}: {value!r}")
            values[metric] = float(value)
        rows.append({"model": model_label, "method": method, "view": view_label, **values})
    return rows


def validate_bindings(primary_path: Path, secondary_path: Path, materialization_path: Path) -> dict:
    primary = load(primary_path)
    secondary = load(secondary_path)
    materialization = load(materialization_path)
    if primary.get("status") != EXPECTED_REPORT_STATUS or secondary.get("status") != EXPECTED_REPORT_STATUS:
        raise ValueError("evaluation report status is not passing")
    if materialization.get("status") != EXPECTED_MATERIALIZATION_STATUS:
        raise ValueError("combined-event materialization status is not passing")
    for label, report in (("primary", primary), ("secondary", secondary)):
        if report.get("bootstrap_replicates") != 10000 or report.get("bootstrap_seed") != 27072027:
            raise ValueError(f"{label} report lacks the fixed final bootstrap")
        hashes = report.get("hashes") or {}
        if hashes.get("corpus") != EXPECTED_CORPUS_SHA256 or hashes.get("jobs") != EXPECTED_JOBS_SHA256:
            raise ValueError(f"{label} report corpus/jobs binding mismatch")
    expected_events = {
        "primary": materialization["hashes"][
            "primary_qwen35_combined_first_generation_v014.jsonl"
        ],
        "secondary": materialization["hashes"][
            "secondary_qwen25_combined_first_generation_v014.jsonl"
        ],
    }
    if primary["hashes"].get("event_attempts") != expected_events["primary"]:
        raise ValueError("primary report is not bound to the combined event ledger")
    if secondary["hashes"].get("event_attempts") != expected_events["secondary"]:
        raise ValueError("secondary report is not bound to the combined event ledger")
    return materialization


def pct(value: float) -> str:
    return f"{100 * value:.2f}"


def latex(rows: list[dict]) -> str:
    body = []
    for row in rows:
        body.append(
            f"{row['model']} & {row['view']} & {pct(row['accuracy'])} & "
            f"{pct(row['macro_f1'])} & {pct(row['unsafe_fulfilment_rate'])} & "
            f"{pct(row['non_answer_rate_on_answer'])} \\\\"
        )
    return "\n".join((
        r"\begin{table}[t]",
        r"\caption{Held-out transfer across information views. All values are percentages over the same 2,000 component-disjoint scenarios. Unsafe is computed on refuse/escalate targets; non-answer is computed on answer targets.}",
        r"\label{tab:secondary-transfer}",
        r"\centering",
        r"\small",
        r"\begin{tabular}{llrrrr}",
        r"\toprule",
        r"Model & View & Acc. & Macro-F1 & Unsafe & Non-answer \\",
        r"\midrule",
        *body[:4],
        r"\midrule",
        *body[4:],
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{table}",
        "",
    ))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("primary_report", type=Path)
    parser.add_argument("secondary_report", type=Path)
    parser.add_argument("materialization_report", type=Path)
    parser.add_argument("output_tex", type=Path)
    parser.add_argument("output_json", type=Path)
    args = parser.parse_args()
    if args.output_tex.exists() or args.output_json.exists():
        raise FileExistsError("refusing to overwrite secondary comparison asset")
    materialization = validate_bindings(
        args.primary_report, args.secondary_report, args.materialization_report
    )
    primary = load(args.primary_report)
    secondary = load(args.secondary_report)
    rows = extract_rows(primary, "Qwen3.5-35B") + extract_rows(secondary, "Qwen2.5-7B")
    args.output_tex.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_tex.write_text(latex(rows), encoding="utf-8")
    report = {
        "schema_version": "0.14.0",
        "status": "PASS_V014_HELDOUT_SECONDARY_COMPARISON_ASSET",
        "selection_on_accuracy": False,
        "heldout_scenarios_per_view": 2000,
        "rows": rows,
        "hashes": {
            "primary_report": sha256(args.primary_report),
            "secondary_report": sha256(args.secondary_report),
            "materialization_report": sha256(args.materialization_report),
            "latex_table": sha256(args.output_tex),
        },
        "materialization_status": materialization["status"],
        "bootstrap_replicates": primary["bootstrap_replicates"],
        "bootstrap_seed": primary["bootstrap_seed"],
    }
    args.output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "rows": len(rows), "output": str(args.output_tex)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
