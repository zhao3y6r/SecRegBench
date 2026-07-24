#!/usr/bin/env python3
"""Recompute review-identified diagnostics without any model rerun."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
from collections import defaultdict
from pathlib import Path
from typing import Any

from score_provisional_evaluation_v012 import component_stats, paired_bootstrap, percentile


METHODS = ("dialogue_only", "state_only", "oracle_evidence", "state_oracle_evidence")
METHOD_LABELS = {
    "dialogue_only": "Dialogue",
    "state_only": "State",
    "oracle_evidence": "Evidence",
    "state_oracle_evidence": "State+evidence",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def clustered_rates(
    records: list[dict[str, Any]],
    fields: tuple[str, ...],
    replicates: int,
    seed: int,
) -> dict[str, Any]:
    by_component: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        by_component[record["component_id"]].append(record)
    components = sorted(by_component)
    if not components:
        raise ValueError("diagnostic has no component support")

    def rates(selection: list[str] | None = None) -> dict[str, float]:
        selected = components if selection is None else selection
        numerators = {field: 0 for field in fields}
        denominator = 0
        for component in selected:
            for record in by_component[component]:
                denominator += 1
                for field in fields:
                    numerators[field] += int(record[field])
        return {field: numerators[field] / denominator for field in fields}

    observed = rates()
    samples = {field: [] for field in fields}
    rng = random.Random(seed)
    for _ in range(replicates):
        selection = [rng.choice(components) for _ in components]
        draw = rates(selection)
        for field in fields:
            samples[field].append(draw[field])
    return {
        "n": len(records),
        "components": len(components),
        "rates": {
            field: {
                "point": observed[field],
                "ci95_low": percentile(samples[field], 0.025),
                "ci95_high": percentile(samples[field], 0.975),
            }
            for field in fields
        },
    }


def build_pair_records(rows: list[dict[str, Any]]) -> dict[str, dict[str, list[dict[str, Any]]]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(row["method"], row["family_id"])].append(row)
    output: dict[str, dict[str, list[dict[str, Any]]]] = {
        method: defaultdict(list) for method in METHODS
    }
    for (method, _), members in grouped.items():
        suite = members[0]["suite"]
        if suite not in {"counterfactual", "institution_role", "temporal"} or len(members) != 2:
            continue
        if members[0]["gold"] == members[1]["gold"]:
            continue
        components = {member["component_id"] for member in members}
        if len(components) != 1:
            raise ValueError("a controlled pair spans realized components")
        output[method][suite].append(
            {
                "component_id": next(iter(components)),
                "predicted_change": members[0]["prediction"] != members[1]["prediction"],
                "exact_pair": all(member["prediction"] == member["gold"] for member in members),
            }
        )
    return output


def build_multiturn_records(rows: list[dict[str, Any]]) -> dict[str, dict[str, list[dict[str, Any]]]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if row["suite"] == "multi_turn":
            grouped[(row["method"], row["family_id"])].append(row)
    output = {
        method: {"trajectory": [], "change_event": []}
        for method in METHODS
    }
    for (method, _), members in grouped.items():
        ordered = sorted(members, key=lambda item: len(item["dialogue"]))
        components = {member["component_id"] for member in ordered}
        if len(components) != 1:
            raise ValueError("a multi-turn trajectory spans realized components")
        component = next(iter(components))
        output[method]["trajectory"].append(
            {
                "component_id": component,
                "complete_trajectory": all(
                    member["prediction"] == member["gold"] for member in ordered
                ),
            }
        )
        for index in range(1, len(ordered)):
            if ordered[index]["gold"] == ordered[index - 1]["gold"]:
                continue
            output[method]["change_event"].append(
                {
                    "component_id": component,
                    "correct_after_change": ordered[index]["prediction"] == ordered[index]["gold"],
                    "stale_previous_action": ordered[index]["prediction"] == ordered[index - 1]["gold"],
                }
            )
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("primary_scored", type=Path)
    parser.add_argument("keyword_predictions", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--replicates", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=27072027)
    args = parser.parse_args()

    rows = read_jsonl(args.primary_scored)
    if len(rows) != 8000:
        raise ValueError(f"expected 8,000 primary rows, found {len(rows)}")
    pair_records = build_pair_records(rows)
    multiturn_records = build_multiturn_records(rows)

    controlled = {}
    for method in METHODS:
        controlled[method] = {}
        for offset, suite in enumerate(("counterfactual", "institution_role", "temporal")):
            controlled[method][suite] = clustered_rates(
                pair_records[method][suite],
                ("predicted_change", "exact_pair"),
                args.replicates,
                args.seed + offset,
            )
        controlled[method]["correct_after_change"] = clustered_rates(
            multiturn_records[method]["change_event"],
            ("correct_after_change", "stale_previous_action"),
            args.replicates,
            args.seed + 10,
        )
        controlled[method]["complete_trajectory"] = clustered_rates(
            multiturn_records[method]["trajectory"],
            ("complete_trajectory",),
            args.replicates,
            args.seed + 11,
        )

    keyword = {row["scenario_id"]: row["prediction"] for row in read_jsonl(args.keyword_predictions)}
    combined_rows = [row for row in rows if row["method"] == "state_oracle_evidence"]
    if len(combined_rows) != 2000:
        raise ValueError("primary combined view does not contain 2,000 held-out rows")
    if any(row["scenario_id"] not in keyword for row in combined_rows):
        raise ValueError("keyword baseline lacks a held-out scenario")
    keyword_rows = [
        {**row, "prediction": keyword[row["scenario_id"]]}
        for row in combined_rows
    ]
    baseline_comparison = paired_bootstrap(
        component_stats(keyword_rows),
        component_stats(combined_rows),
        args.replicates,
        args.seed + 20,
    )

    report = {
        "schema_version": "0.14.0",
        "status": "PASS_REVIEW_CORRECTION_DIAGNOSTICS_WITHOUT_MODEL_RERUN",
        "definitions": {
            "predicted_change": "The two predictions differ on a pair whose two gold actions differ.",
            "exact_pair": "Both endpoint predictions equal their respective gold actions.",
            "clustered_interval": "Percentile bootstrap over realized held-out components; all families/events in a sampled component move together.",
            "keyword_comparison": "Primary state+oracle-evidence minus the frozen development-only keyword baseline on identical held-out scenarios and identical component draws.",
        },
        "bootstrap": {
            "replicates": args.replicates,
            "seed_base": args.seed,
        },
        "controlled_family_diagnostics": controlled,
        "keyword_baseline_paired_comparison": baseline_comparison,
        "input_hashes": {
            str(args.primary_scored): sha256(args.primary_scored),
            str(args.keyword_predictions): sha256(args.keyword_predictions),
        },
        "model_rerun_performed": False,
        "submission_or_upload_performed": False,
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    report_path = args.output_dir / "REVIEW_CORRECTION_DIAGNOSTICS_V014.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    suite_labels = {
        "counterfactual": "Counterfactual",
        "institution_role": "Institution-role",
        "temporal": "Temporal",
    }
    table_lines = [
        r"\begin{table*}[t]",
        r"\caption{Held-out controlled-family diagnostics (percent). For required-flip pairs, each cell reports predicted-change rate / exact endpoint-pair accuracy. Intervals and component support are reported in the artifact.}",
        r"\label{tab:family-diagnostics}",
        r"\centering",
        r"\small",
        r"\setlength{\tabcolsep}{5pt}",
        r"\begin{tabular}{@{}lrrrr@{}}",
        r"\toprule",
        r"Diagnostic (families/events) & Dialogue & State & Evidence & State+evidence \\",
        r"\midrule",
    ]
    for suite in ("counterfactual", "institution_role", "temporal"):
        n = controlled["dialogue_only"][suite]["n"]
        cells = []
        for method in METHODS:
            item = controlled[method][suite]["rates"]
            cells.append(
                f"{item['predicted_change']['point'] * 100:.1f} / "
                f"{item['exact_pair']['point'] * 100:.1f}"
            )
        table_lines.append(f"{suite_labels[suite]} flip ({n}) & " + " & ".join(cells) + r" \\")
    cells = [
        f"{controlled[method]['correct_after_change']['rates']['correct_after_change']['point'] * 100:.1f}"
        for method in METHODS
    ]
    table_lines.append(
        f"Correct after change ({controlled['dialogue_only']['correct_after_change']['n']}) & "
        + " & ".join(cells)
        + r" \\"
    )
    cells = [
        f"{controlled[method]['complete_trajectory']['rates']['complete_trajectory']['point'] * 100:.1f}"
        for method in METHODS
    ]
    table_lines.append(
        f"Complete trajectory ({controlled['dialogue_only']['complete_trajectory']['n']}) & "
        + " & ".join(cells)
        + r" \\"
    )
    table_lines.extend((r"\bottomrule", r"\end{tabular}", r"\end{table*}"))
    table_path = args.output_dir / "family_diagnostics_corrected.tex"
    table_path.write_text("\n".join(table_lines) + "\n", encoding="utf-8")

    summary_path = args.output_dir / "REVIEW_CORRECTION_SUMMARY_V014.md"
    combined_exact = controlled["state_oracle_evidence"]
    macro = baseline_comparison["metrics"]["macro_f1"]
    summary_path.write_text(
        "\n".join(
            (
                "# Review-correction diagnostic summary v0.14",
                "",
                "No model was retrained or rerun. Existing first-generation predictions were rescored.",
                "",
                f"- Counterfactual combined predicted-change / exact-pair: "
                f"{combined_exact['counterfactual']['rates']['predicted_change']['point'] * 100:.1f}% / "
                f"{combined_exact['counterfactual']['rates']['exact_pair']['point'] * 100:.1f}%.",
                f"- Institution-role combined predicted-change / exact-pair: "
                f"{combined_exact['institution_role']['rates']['predicted_change']['point'] * 100:.1f}% / "
                f"{combined_exact['institution_role']['rates']['exact_pair']['point'] * 100:.1f}%.",
                f"- Temporal combined predicted-change / exact-pair: "
                f"{combined_exact['temporal']['rates']['predicted_change']['point'] * 100:.1f}% / "
                f"{combined_exact['temporal']['rates']['exact_pair']['point'] * 100:.1f}%.",
                f"- Combined minus keyword macro-F1: {macro['difference'] * 100:+.1f} points "
                f"(95% component-bootstrap CI {macro['ci95_low'] * 100:+.1f}, "
                f"{macro['ci95_high'] * 100:+.1f}).",
            )
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": report["status"],
                "report": str(report_path),
                "table": str(table_path),
                "summary": str(summary_path),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
