#!/usr/bin/env python3
"""Build hash-bound v0.14 answer-risk diagnostics for two checkpoints."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]
METHODS = (
    ("dialogue_only", "Dialogue"),
    ("state_only", "State"),
    ("oracle_evidence", "Evidence"),
    ("state_oracle_evidence", "State+evidence"),
)
METHOD_IDS = {item[0] for item in METHODS}
ACTIONS = {"ANSWER", "CLARIFY", "REFUSE", "ESCALATE"}
EXPECTED_HELDOUT_PER_METHOD = 2000
EXPECTED_COMPONENTS = 59
EXPECTED_BOOTSTRAP_REPLICATES = 10000
EXPECTED_BOOTSTRAP_SEED = 27072027
EXPECTED_CORPUS_SHA256 = "a459ea29ab434679e6c59a65704318376e2a1ca548cf0d43e89d4df791cd5bdc"
EXPECTED_JOBS_SHA256 = "3856bd94b831191b853c8542496afbb8d670ffbbad90759a9c3d82787fbccc79"
EXPECTED_REPORT_STATUS = "PASS_MACHINE_STAGE_SCORING_PROVISIONAL_NOT_HUMAN_VALIDATED_NOT_DATASET"
EXPECTED_MATERIALIZATION_STATUS = (
    "PASS_EXACT_REUSE_PLUS_INCREMENTAL_FIRST_GENERATION_MATERIALIZATION"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def inside_project(path: Path) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(PROJECT.resolve())
    except ValueError as exc:
        raise ValueError(f"output must remain inside project: {path}") from exc
    return resolved


def load_heldout(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("split") != "heldout":
                continue
            method = row.get("method")
            scenario = row.get("scenario_id")
            component = row.get("component_id")
            gold = row.get("gold")
            prediction = row.get("prediction")
            if method not in METHOD_IDS:
                raise ValueError(f"unexpected method at {path}:{line_number}: {method!r}")
            if not isinstance(scenario, str) or not scenario:
                raise ValueError(f"missing scenario_id at {path}:{line_number}")
            if not isinstance(component, str) or not component:
                raise ValueError(f"missing component_id at {path}:{line_number}")
            if gold not in ACTIONS:
                raise ValueError(f"unexpected gold action at {path}:{line_number}: {gold!r}")
            if not isinstance(prediction, str) or not prediction:
                raise ValueError(f"missing prediction at {path}:{line_number}")
            rows.append(
                {
                    "method": method,
                    "scenario_id": scenario,
                    "component_id": component,
                    "gold": gold,
                    "prediction": prediction,
                }
            )

    counts = Counter(row["method"] for row in rows)
    expected = Counter({method: EXPECTED_HELDOUT_PER_METHOD for method, _ in METHODS})
    if counts != expected:
        raise ValueError(f"heldout method cardinality mismatch: {dict(counts)}")
    for method, _ in METHODS:
        scenarios = [row["scenario_id"] for row in rows if row["method"] == method]
        if len(set(scenarios)) != EXPECTED_HELDOUT_PER_METHOD:
            raise ValueError(f"duplicate/missing heldout scenario for {method}")
    return rows


def validate_report(path: Path, scored_path: Path) -> dict:
    report = read_json(path)
    if report.get("status") != EXPECTED_REPORT_STATUS:
        raise ValueError(f"evaluation report status is not passing: {path}")
    if report.get("bootstrap_replicates") != EXPECTED_BOOTSTRAP_REPLICATES:
        raise ValueError(f"evaluation report bootstrap count mismatch: {path}")
    if report.get("bootstrap_seed") != EXPECTED_BOOTSTRAP_SEED:
        raise ValueError(f"evaluation report bootstrap seed mismatch: {path}")
    hashes = report.get("hashes") or {}
    if hashes.get("corpus") != EXPECTED_CORPUS_SHA256:
        raise ValueError(f"unexpected corpus hash in {path}")
    if hashes.get("jobs") != EXPECTED_JOBS_SHA256:
        raise ValueError(f"unexpected jobs hash in {path}")
    if hashes.get("scored_rows") != sha256(scored_path):
        raise ValueError(f"scored-row hash mismatch for {path}")
    return report


def validate_materialization(
    materialization_path: Path, primary_report: dict, secondary_report: dict
) -> dict:
    materialization = read_json(materialization_path)
    if materialization.get("status") != EXPECTED_MATERIALIZATION_STATUS:
        raise ValueError("combined-event materialization status is not passing")
    expected = {
        "primary": materialization["hashes"][
            "primary_qwen35_combined_first_generation_v014.jsonl"
        ],
        "secondary": materialization["hashes"][
            "secondary_qwen25_combined_first_generation_v014.jsonl"
        ],
    }
    if (primary_report.get("hashes") or {}).get("event_attempts") != expected["primary"]:
        raise ValueError("primary report is not bound to materialized events")
    if (secondary_report.get("hashes") or {}).get("event_attempts") != expected["secondary"]:
        raise ValueError("secondary report is not bound to materialized events")
    return materialization


def validate_pair(primary: list[dict], secondary: list[dict]) -> list[str]:
    def index(rows: list[dict]) -> dict[tuple[str, str], dict]:
        value: dict[tuple[str, str], dict] = {}
        for row in rows:
            key = (row["method"], row["scenario_id"])
            if key in value:
                raise ValueError(f"duplicate method/scenario row: {key}")
            value[key] = row
        return value

    left = index(primary)
    right = index(secondary)
    if set(left) != set(right):
        raise ValueError("primary and secondary heldout method/scenario sets differ")
    for key in left:
        if left[key]["gold"] != right[key]["gold"]:
            raise ValueError(f"gold action differs across checkpoints: {key}")
        if left[key]["component_id"] != right[key]["component_id"]:
            raise ValueError(f"component differs across checkpoints: {key}")
    components = sorted({row["component_id"] for row in primary})
    if len(components) != EXPECTED_COMPONENTS:
        raise ValueError(f"expected {EXPECTED_COMPONENTS} heldout components, observed {len(components)}")
    return components


def row_counts(row: dict) -> tuple[int, int, int, int]:
    clarify_target = int(row["gold"] == "CLARIFY")
    premature_answer = int(row["gold"] == "CLARIFY" and row["prediction"] == "ANSWER")
    nonanswer_target = int(row["gold"] != "ANSWER")
    direct_answer = int(row["gold"] != "ANSWER" and row["prediction"] == "ANSWER")
    return clarify_target, premature_answer, nonanswer_target, direct_answer


def aggregate_by_system(rows_by_model: dict[str, list[dict]]) -> dict[tuple[str, str], dict[str, tuple[int, int, int, int]]]:
    systems: dict[tuple[str, str], dict[str, list[int]]] = defaultdict(lambda: defaultdict(lambda: [0, 0, 0, 0]))
    for model, rows in rows_by_model.items():
        for row in rows:
            values = row_counts(row)
            slot = systems[(model, row["method"])][row["component_id"]]
            for index, value in enumerate(values):
                slot[index] += value
    return {
        system: {component: tuple(values) for component, values in groups.items()}
        for system, groups in systems.items()
    }


def percentile(values: list[float], q: float) -> float:
    if not values:
        raise ValueError("cannot take percentile of empty list")
    ordered = sorted(values)
    position = (len(ordered) - 1) * q
    low = math.floor(position)
    high = math.ceil(position)
    if low == high:
        return ordered[low]
    weight = position - low
    return ordered[low] * (1 - weight) + ordered[high] * weight


def rate_tuple(values: tuple[int, int, int, int]) -> tuple[float | None, float | None]:
    clarify_den, premature_num, nonanswer_den, direct_num = values
    premature = premature_num / clarify_den if clarify_den > 0 else None
    direct = direct_num / nonanswer_den if nonanswer_den > 0 else None
    return premature, direct


def sum_groups(groups: dict[str, tuple[int, int, int, int]], draw: list[str]) -> tuple[int, int, int, int]:
    total = [0, 0, 0, 0]
    for component in draw:
        values = groups.get(component, (0, 0, 0, 0))
        for index, value in enumerate(values):
            total[index] += value
    return tuple(total)


def analyze(primary: list[dict], secondary: list[dict], components: list[str]) -> dict:
    grouped = aggregate_by_system({"Qwen3.5-35B": primary, "Qwen2.5-7B": secondary})
    systems = [(model, method) for model in ("Qwen3.5-35B", "Qwen2.5-7B") for method, _ in METHODS]
    observed: dict[tuple[str, str], tuple[int, int, int, int]] = {}
    for system in systems:
        observed[system] = sum_groups(grouped[system], components)

    bootstrap: dict[tuple[str, str], dict[str, list[float]]] = {
        system: {"premature": [], "direct_nonanswer": []} for system in systems
    }
    paired: dict[str, dict[str, list[float]]] = {
        method: {"premature": [], "direct_nonanswer": []} for method, _ in METHODS
    }
    rng = random.Random(EXPECTED_BOOTSTRAP_SEED)
    for _ in range(EXPECTED_BOOTSTRAP_REPLICATES):
        draw = [rng.choice(components) for _ in components]
        draw_rates: dict[tuple[str, str], tuple[float | None, float | None]] = {}
        for system in systems:
            rates = rate_tuple(sum_groups(grouped[system], draw))
            draw_rates[system] = rates
            if rates[0] is not None:
                bootstrap[system]["premature"].append(rates[0])
            if rates[1] is not None:
                bootstrap[system]["direct_nonanswer"].append(rates[1])
        for method, _ in METHODS:
            primary_rates = draw_rates[("Qwen3.5-35B", method)]
            secondary_rates = draw_rates[("Qwen2.5-7B", method)]
            if primary_rates[0] is not None and secondary_rates[0] is not None:
                paired[method]["premature"].append(secondary_rates[0] - primary_rates[0])
            if primary_rates[1] is not None and secondary_rates[1] is not None:
                paired[method]["direct_nonanswer"].append(secondary_rates[1] - primary_rates[1])

    rows: list[dict] = []
    for model, method in systems:
        clarify_den, premature_num, nonanswer_den, direct_num = observed[(model, method)]
        if clarify_den <= 0 or nonanswer_den <= 0:
            raise ValueError(f"observed diagnostic denominator is empty for {model}/{method}")
        premature = premature_num / clarify_den
        direct = direct_num / nonanswer_den
        rows.append(
            {
                "model": model,
                "method": method,
                "view": dict(METHODS)[method],
                "clarify_targets": clarify_den,
                "premature_answers": premature_num,
                "premature_answer_rate": premature,
                "premature_answer_ci95": {
                    "low": percentile(bootstrap[(model, method)]["premature"], 0.025),
                    "high": percentile(bootstrap[(model, method)]["premature"], 0.975),
                },
                "premature_answer_valid_bootstrap_replicates": len(bootstrap[(model, method)]["premature"]),
                "nonanswer_targets": nonanswer_den,
                "direct_answers_on_nonanswer": direct_num,
                "direct_answer_on_nonanswer_rate": direct,
                "direct_answer_on_nonanswer_ci95": {
                    "low": percentile(bootstrap[(model, method)]["direct_nonanswer"], 0.025),
                    "high": percentile(bootstrap[(model, method)]["direct_nonanswer"], 0.975),
                },
                "direct_answer_on_nonanswer_valid_bootstrap_replicates": len(bootstrap[(model, method)]["direct_nonanswer"]),
            }
        )

    differences: list[dict] = []
    for method, view in METHODS:
        values = paired[method]
        p = observed[("Qwen3.5-35B", method)]
        s = observed[("Qwen2.5-7B", method)]
        p_rates = rate_tuple(p)
        s_rates = rate_tuple(s)
        if None in p_rates or None in s_rates:
            raise ValueError(f"observed paired diagnostic denominator is empty for {method}")
        assert p_rates[0] is not None and p_rates[1] is not None
        assert s_rates[0] is not None and s_rates[1] is not None
        differences.append(
            {
                "method": method,
                "view": view,
                "secondary_minus_primary_premature_answer_rate": s_rates[0] - p_rates[0],
                "secondary_minus_primary_premature_answer_ci95": {
                    "low": percentile(values["premature"], 0.025),
                    "high": percentile(values["premature"], 0.975),
                },
                "premature_answer_valid_bootstrap_replicates": len(values["premature"]),
                "secondary_minus_primary_direct_answer_on_nonanswer_rate": s_rates[1] - p_rates[1],
                "secondary_minus_primary_direct_answer_on_nonanswer_ci95": {
                    "low": percentile(values["direct_nonanswer"], 0.025),
                    "high": percentile(values["direct_nonanswer"], 0.975),
                },
                "direct_answer_on_nonanswer_valid_bootstrap_replicates": len(values["direct_nonanswer"]),
            }
        )
    return {"rows": rows, "paired_secondary_minus_primary": differences}


def write_csv(path: Path, rows: list[dict]) -> None:
    fields = [
        "model", "method", "view", "clarify_targets", "premature_answers",
        "premature_answer_rate", "premature_answer_ci95_low", "premature_answer_ci95_high",
        "premature_answer_valid_bootstrap_replicates",
        "nonanswer_targets", "direct_answers_on_nonanswer", "direct_answer_on_nonanswer_rate",
        "direct_answer_on_nonanswer_ci95_low", "direct_answer_on_nonanswer_ci95_high",
        "direct_answer_on_nonanswer_valid_bootstrap_replicates",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            flat = dict(row)
            premature_ci = flat.pop("premature_answer_ci95")
            direct_ci = flat.pop("direct_answer_on_nonanswer_ci95")
            flat["premature_answer_ci95_low"] = premature_ci["low"]
            flat["premature_answer_ci95_high"] = premature_ci["high"]
            flat["direct_answer_on_nonanswer_ci95_low"] = direct_ci["low"]
            flat["direct_answer_on_nonanswer_ci95_high"] = direct_ci["high"]
            writer.writerow(flat)


def pct(value: float) -> str:
    return f"{100 * value:.1f}"


def latex(rows: list[dict]) -> str:
    lines = [
        r"\begin{tabular}{llrrll}",
        r"\toprule",
        r"Checkpoint & View & Clarify $n$ & Premature answer & Non-answer $n$ & Direct answer \\",
        r"\midrule",
    ]
    for row in rows:
        p_ci = row["premature_answer_ci95"]
        d_ci = row["direct_answer_on_nonanswer_ci95"]
        model = row["model"].replace("Qwen", "Qwen")
        lines.append(
            f"{model} & {row['view']} & {row['clarify_targets']} & "
            f"{pct(row['premature_answer_rate'])} [{pct(p_ci['low'])}, {pct(p_ci['high'])}] & "
            f"{row['nonanswer_targets']} & "
            f"{pct(row['direct_answer_on_nonanswer_rate'])} [{pct(d_ci['low'])}, {pct(d_ci['high'])}] \\\\"
        )
    lines.extend(
        [
            r"\bottomrule",
            r"\end{tabular}",
            "% Rates and 95% intervals are percentages from 10,000 held-out-component bootstrap draws.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("primary_report", type=Path)
    parser.add_argument("primary_scored", type=Path)
    parser.add_argument("secondary_report", type=Path)
    parser.add_argument("secondary_scored", type=Path)
    parser.add_argument("materialization_report", type=Path)
    parser.add_argument("output_json", type=Path)
    parser.add_argument("output_csv", type=Path)
    parser.add_argument("output_tex", type=Path)
    args = parser.parse_args()

    outputs = [inside_project(args.output_json), inside_project(args.output_csv), inside_project(args.output_tex)]
    if any(path.exists() for path in outputs):
        raise FileExistsError("refusing to overwrite action-risk diagnostic output")
    for path in (
        args.primary_report,
        args.primary_scored,
        args.secondary_report,
        args.secondary_scored,
        args.materialization_report,
    ):
        if not path.is_file():
            raise FileNotFoundError(path)

    primary_report = validate_report(args.primary_report, args.primary_scored)
    secondary_report = validate_report(args.secondary_report, args.secondary_scored)
    materialization = validate_materialization(
        args.materialization_report, primary_report, secondary_report
    )
    primary = load_heldout(args.primary_scored)
    secondary = load_heldout(args.secondary_scored)
    components = validate_pair(primary, secondary)
    analysis = analyze(primary, secondary, components)
    report = {
        "schema_version": "0.14.0",
        "status": "PASS_V014_ACTION_RISK_DIAGNOSTICS",
        "definitions": {
            "premature_answer_rate": "prediction ANSWER among gold CLARIFY targets",
            "direct_answer_on_nonanswer_rate": "prediction ANSWER among gold CLARIFY, REFUSE, or ESCALATE targets",
        },
        "heldout_scenarios_per_method": EXPECTED_HELDOUT_PER_METHOD,
        "heldout_components": EXPECTED_COMPONENTS,
        "bootstrap_replicates": EXPECTED_BOOTSTRAP_REPLICATES,
        "bootstrap_seed": EXPECTED_BOOTSTRAP_SEED,
        **analysis,
        "practitioner_validation": "documented_separately_from_machine_scoring",
        "materialization_status": materialization["status"],
        "hashes": {
            "primary_report": sha256(args.primary_report),
            "primary_scored_rows": sha256(args.primary_scored),
            "secondary_report": sha256(args.secondary_report),
            "secondary_scored_rows": sha256(args.secondary_scored),
            "materialization_report": sha256(args.materialization_report),
            "primary_report_corpus": (primary_report.get("hashes") or {}).get("corpus"),
            "secondary_report_corpus": (secondary_report.get("hashes") or {}).get("corpus"),
        },
    }
    for path in outputs:
        path.parent.mkdir(parents=True, exist_ok=True)
    outputs[0].write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_csv(outputs[1], report["rows"])
    outputs[2].write_text(latex(report["rows"]), encoding="utf-8")
    print(json.dumps({"status": report["status"], "rows": len(report["rows"]), "output": str(outputs[0])}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
