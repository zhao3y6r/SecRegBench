#!/usr/bin/env python3
"""Verify the deidentified SecRegBench practitioner-validation release."""

from __future__ import annotations

import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path


ACTIONS = ("ANSWER", "CLARIFY", "REFUSE", "ESCALATE")
SLOTS = ("R1", "R2", "R3", "R4", "R5")


def read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def mean(values: list[float]) -> float:
    return sum(values) / len(values)


def fleiss(rows: list[list[str]], categories: tuple[str, ...]) -> tuple[float, float]:
    raters = len(rows[0])
    totals = Counter()
    agreements = []
    for row in rows:
        counts = Counter(row)
        totals.update(counts)
        agreements.append(
            (sum(counts[category] ** 2 for category in categories) - raters)
            / (raters * (raters - 1))
        )
    observed = mean(agreements)
    expected = sum(
        (totals[category] / (len(rows) * raters)) ** 2 for category in categories
    )
    return observed, (observed - expected) / (1 - expected)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    validation = root / "validation/human_validation"
    judgments = read_jsonl(validation / "human_judgments_v016.jsonl")
    aggregates = read_jsonl(validation / "human_item_aggregates_v016.jsonl")
    report = json.loads(
        (validation / "HUMAN_VALIDATION_RESULTS_V016.json").read_text(
            encoding="utf-8"
        )
    )

    if len(judgments) != 700 or len(aggregates) != 500:
        raise ValueError("human-validation cardinality mismatch")
    if Counter(row["reviewer_slot"] for row in judgments) != Counter(
        {slot: 140 for slot in SLOTS}
    ):
        raise ValueError("reviewer-slot cardinality mismatch")
    if any(row["reviewer_action"] not in ACTIONS for row in judgments):
        raise ValueError("invalid action")
    if any(row["realism_score_1_to_5"] not in range(1, 6) for row in judgments):
        raise ValueError("invalid realism score")
    if any(row["material_defect"] not in {"Yes", "No"} for row in judgments):
        raise ValueError("invalid material-defect value")

    by_item: dict[str, list[dict]] = defaultdict(list)
    for row in judgments:
        by_item[row["review_item_id"]].append(row)
    counts = Counter(len(rows) for rows in by_item.values())
    if len(by_item) != 500 or counts != Counter({1: 450, 5: 50}):
        raise ValueError(f"shared/exclusive design mismatch: {counts}")

    shared = [
        sorted(rows, key=lambda row: row["reviewer_slot"])
        for rows in by_item.values()
        if len(rows) == 5
    ]
    action_matrix = [
        [row["reviewer_action"] for row in rows] for rows in shared
    ]
    pairwise, kappa = fleiss(action_matrix, ACTIONS)
    if not math.isclose(pairwise, 0.36, abs_tol=1e-12):
        raise ValueError(f"action pairwise agreement mismatch: {pairwise}")
    if not math.isclose(kappa, 0.06296851574212885, abs_tol=1e-12):
        raise ValueError(f"action kappa mismatch: {kappa}")

    target_match = mean(
        [1.0 if row["consensus_matches_oracle_primary"] else 0.0 for row in aggregates]
    )
    realism = mean([float(row["realism_mean"]) for row in aggregates])
    defects = sum(
        row["consensus_material_defect"] == "Yes" for row in aggregates
    )
    if not math.isclose(target_match, 0.36, abs_tol=1e-12):
        raise ValueError(f"target match mismatch: {target_match}")
    if not math.isclose(realism, 4.692, abs_tol=1e-12):
        raise ValueError(f"realism mean mismatch: {realism}")
    if defects != 0:
        raise ValueError(f"material-defect count mismatch: {defects}")

    if report.get("status") != (
        "PASS_COMPLETED_FIVE_ANONYMOUS_SECURITIES_COMPLIANCE_PRACTITIONERS"
    ):
        raise ValueError("unexpected human-validation report status")
    observed = report["item_level_500"]
    if (
        observed["oracle_primary_match"] != 0.36
        or observed["mean_realism"] != 4.692
        or observed["material_defect_count"] != 0
        or observed["material_defect_wilson_95ci"] != [0, 0.0076]
    ):
        raise ValueError("published aggregate mismatch")

    prohibited_keys = {
        "name",
        "real_name",
        "employer",
        "email",
        "phone",
        "signature",
        "stamp",
        "consent",
    }
    if any(set(row) & prohibited_keys for row in judgments + aggregates):
        raise ValueError("identity or personal-document field present")
    released_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in validation.iterdir()
        if path.is_file()
    )
    if re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", released_text):
        raise ValueError("email-like string in human-validation release")
    if re.search(r"\b1[3-9]\d{9}\b", released_text):
        raise ValueError("phone-like string in human-validation release")

    print(
        json.dumps(
            {
                "status": "PASS_DEIDENTIFIED_HUMAN_VALIDATION_V017",
                "judgments": len(judgments),
                "distinct_items": len(aggregates),
                "shared_five_way_items": counts[5],
                "single_review_items": counts[1],
                "action_pairwise_agreement": pairwise,
                "action_fleiss_kappa": kappa,
                "target_action_match": target_match,
                "mean_realism": realism,
                "material_defects": defects,
                "identity_fields_distributed": False,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
