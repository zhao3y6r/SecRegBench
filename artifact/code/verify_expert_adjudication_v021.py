#!/usr/bin/env python3
"""Verify the deidentified SecRegBench v0.21 expert-adjudication overlay."""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path


ACTIONS = {"ANSWER", "CLARIFY", "REFUSE", "ESCALATE"}
PROHIBITED_KEYS = {
    "review_item_id",
    "reviewer_slot",
    "reason",
    "anonymized_reasons",
    "name",
    "real_name",
    "employer",
    "email",
    "phone",
    "signature",
    "stamp",
    "consent",
}


def read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def close(left: float, right: float) -> bool:
    return math.isclose(left, right, rel_tol=0, abs_tol=1e-12)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    validation = root / "validation/expert_adjudication"
    reference_path = validation / "expert_adjudicated_reference_v021.jsonl"
    summary_path = validation / "EXPERT_ADJUDICATION_SUMMARY_V021.json"
    rescoring_path = validation / "HELDOUT_RESCORING_V021.json"
    rows = read_jsonl(reference_path)
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    rescoring = json.loads(rescoring_path.read_text(encoding="utf-8"))

    if len(rows) != 100 or len({row["scenario_id"] for row in rows}) != 100:
        raise ValueError("expert-adjudication cardinality/uniqueness mismatch")
    if any(set(row) & PROHIBITED_KEYS for row in rows):
        raise ValueError("expert-adjudication release contains a prohibited field")
    released_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in validation.iterdir()
        if path.is_file()
    )
    prohibited_tokens = (
        "F:\\",
        "C:\\Users\\",
        "/Users/",
        "/home/",
        "_private_do_not_send",
        "api_key=",
        "authorization: bearer",
        "/chat/completions",
    )
    if any(token.lower() in released_text.lower() for token in prohibited_tokens):
        raise ValueError("expert-adjudication release contains a local/private marker")
    if re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", released_text):
        raise ValueError("email-like string in expert-adjudication release")
    if re.search(r"\b1[3-9]\d{9}\b", released_text):
        raise ValueError("phone-like string in expert-adjudication release")

    groups = Counter(row["selection_group"] for row in rows)
    if groups != {
        "stratified_random": 50,
        "challenge_model_hard": 43,
        "challenge_prior_defect_flag": 7,
    }:
        raise ValueError(f"selection-group mismatch: {groups}")
    status = Counter(row["reference_status"] for row in rows)
    if status != {"HIGH_CONFIDENCE": 91, "UNRESOLVED": 9}:
        raise ValueError(f"reference-status mismatch: {status}")
    revised = [row for row in rows if row["label_changed"]]
    if len(revised) != 10 or Counter(row["split"] for row in revised) != {
        "heldout": 9,
        "development": 1,
    }:
        raise ValueError("revised-label count/split mismatch")
    high_confidence = [row for row in rows if row["reference_status"] == "HIGH_CONFIDENCE"]
    unresolved = [row for row in rows if row["reference_status"] == "UNRESOLVED"]
    if Counter(row["split"] for row in high_confidence) != {
        "heldout": 64,
        "development": 27,
    }:
        raise ValueError("high-confidence split mismatch")
    for row in high_confidence:
        if (
            row["final_primary_action"] not in ACTIONS
            or row["final_acceptable_actions"] != [row["final_primary_action"]]
            or row["supporting_votes"] < 4
            or row["confidence_median"] < 4
        ):
            raise ValueError(f"invalid high-confidence row: {row['scenario_id']}")
    for row in unresolved:
        if row["final_primary_action"] is not None:
            raise ValueError(f"unresolved row has a primary action: {row['scenario_id']}")
        if not row["final_acceptable_actions"] or not set(
            row["final_acceptable_actions"]
        ).issubset(ACTIONS):
            raise ValueError(f"invalid unresolved action set: {row['scenario_id']}")
    for row in rows:
        if sum(row["round1_action_counts"].values()) != 5:
            raise ValueError(f"round-one vote count mismatch: {row['scenario_id']}")
        if "round2_action_counts" in row and (
            sum(row["round2_action_counts"].values()) != 5
            or sum(row["round2_rule_acceptance_counts"].values()) != 5
        ):
            raise ValueError(f"round-two vote count mismatch: {row['scenario_id']}")

    if summary.get("status") != (
        "PASS_DEIDENTIFIED_EXPERT_ADJUDICATION_PUBLIC_RELEASE"
    ):
        raise ValueError("unexpected expert-adjudication summary status")
    if summary["final_reference"] != {
        "items": 100,
        "high_confidence_items": 91,
        "unresolved_items": 9,
        "label_changed_items": 10,
        "high_confidence_heldout_items": 64,
        "revised_heldout_items": 9,
    }:
        raise ValueError("expert-adjudication summary count mismatch")
    independent = summary["round1_independent_validation"]
    if (
        not close(independent["action_fleiss_kappa_all_100"], 0.851723)
        or not close(independent["rule_primary_match_stratified_random_50"], 0.9)
        or not close(independent["rule_primary_match_all_100"], 0.77)
    ):
        raise ValueError("round-one public aggregate mismatch")
    privacy = summary["privacy"]
    if (
        privacy["raw_answer_cards_distributed"]
        or privacy["reviewer_level_judgments_distributed"]
        or privacy["free_text_reasons_distributed"]
        or privacy["reviewer_slots_distributed"]
        or privacy["names_employers_contacts_signatures_distributed"]
        or not privacy["aggregate_vote_counts_distributed"]
    ):
        raise ValueError("expert-adjudication privacy declaration mismatch")

    if rescoring.get("status") != "PASS_SAVED_PREDICTION_RESCORE_NO_MODEL_RERUN":
        raise ValueError("unexpected rescoring status")
    scope = rescoring["scope"]
    if scope != {
        "heldout_scenarios": 2000,
        "expert_revised_heldout_labels": 9,
        "expert_high_confidence_heldout_subset": 64,
        "unresolved_heldout_items_excluded_from_expert_subset": 7,
        "model_inference_rerun": False,
    }:
        raise ValueError("rescoring scope mismatch")
    if len(rescoring["models"]) != 3:
        raise ValueError("rescoring model count mismatch")
    for model_name, model in rescoring["models"].items():
        if len(model["methods"]) != 4:
            raise ValueError(f"{model_name}: method count mismatch")
        for method, result in model["methods"].items():
            full = result["full_heldout_2000"]
            subset = result["expert_high_confidence_subset_64"]
            if (
                full["original_rule_labels"]["n"] != 2000
                or full["nine_expert_revisions_applied"]["n"] != 2000
                or subset["original_rule_labels"]["n"] != 64
                or subset["expert_adjudicated_labels"]["n"] != 64
            ):
                raise ValueError(f"{model_name}/{method}: rescoring n mismatch")
            for metric, delta in full["delta"].items():
                observed = (
                    full["nine_expert_revisions_applied"][metric]
                    - full["original_rule_labels"][metric]
                )
                if not close(observed, delta):
                    raise ValueError(f"{model_name}/{method}: full delta mismatch")

    print(
        json.dumps(
            {
                "status": "PASS_DEIDENTIFIED_EXPERT_ADJUDICATION_V021",
                "items": len(rows),
                "high_confidence_items": len(high_confidence),
                "revised_labels": len(revised),
                "unresolved_items": len(unresolved),
                "stratified_random_match": independent[
                    "rule_primary_match_stratified_random_50"
                ],
                "round1_action_fleiss_kappa": independent[
                    "action_fleiss_kappa_all_100"
                ],
                "heldout_predictions_rescored_without_inference": True,
                "identity_fields_distributed": False,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
