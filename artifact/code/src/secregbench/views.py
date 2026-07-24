"""Leakage-controlled projections of a SecRegBench scenario record."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping


MODEL_METHODS = {"direct", "evidence_rag", "state_aware"}
FORBIDDEN_MODEL_KEYS = {
    "state",
    "label",
    "adjudication",
    "primary_action",
    "acceptable_actions",
    "control_actions",
    "severity",
    "violation_tags",
    "controlling_rule_ids",
    "controlling_predicates",
    "oracle_version",
    "ambiguity",
    "suite",
    "split",
    "scenario_id",
    "family_id",
    "pair_id",
    "conversation_id",
    "turn_index",
    "transformation",
    "expected_relation",
    "minimality_status",
    "provenance",
    "audits",
    "annotation_ledger_refs",
    "status_as_of_decision",
    "accessed_at",
}


class ViewError(ValueError):
    """Raised when a safe projection cannot be constructed."""


def oracle_view(record: Mapping[str, Any]) -> dict[str, Any]:
    if "decision_date" not in record or "state" not in record:
        raise ViewError("oracle view requires decision_date and state")
    return {"decision_date": record["decision_date"], "state": deepcopy(record["state"])}


def realization_view(record: Mapping[str, Any]) -> dict[str, Any]:
    required = ("decision_date", "language", "state")
    if any(key not in record for key in required):
        raise ViewError("realization view requires decision_date, language, and state")
    return {
        "decision_date": record["decision_date"],
        "language": record["language"],
        "state": deepcopy(record["state"]),
    }


def _sanitized_evidence(record: Mapping[str, Any]) -> list[dict[str, Any]]:
    result = []
    for item in record.get("evidence", []):
        if item.get("role") not in {"controlling", "retrieval_candidate", "distractor"}:
            raise ViewError(f"invalid evidence role: {item.get('role')!r}")
        result.append(
            {
                "source_clause_id": item["source_clause_id"],
                "authority": item["authority"],
                "title": item["title"],
                "effective_from": item["effective_from"],
                "effective_to": item["effective_to"],
                "article": item["article"],
                "excerpt": item["excerpt"],
            }
        )
    return result


def _assert_dialogue_prefix(dialogue: Any) -> None:
    if not isinstance(dialogue, list) or not dialogue:
        raise ViewError("model view requires a non-empty dialogue prefix")
    if dialogue[-1].get("role") != "customer":
        raise ViewError("scored dialogue prefix must end with the pending customer turn")
    message_ids = [item.get("message_id") for item in dialogue]
    if any(not isinstance(item, str) or not item for item in message_ids):
        raise ViewError("each dialogue message requires a message_id")
    if len(message_ids) != len(set(message_ids)):
        raise ViewError("dialogue message_ids must be unique")


def build_model_input_view(record: Mapping[str, Any], method: str) -> dict[str, Any]:
    if method not in MODEL_METHODS:
        raise ViewError(f"unsupported model method: {method!r}")
    dialogue = deepcopy(record.get("dialogue"))
    _assert_dialogue_prefix(dialogue)
    result: dict[str, Any] = {
        "view_version": "0.2.0",
        "method": method,
        "decision_date": record.get("decision_date"),
        "dialogue": dialogue,
    }
    if method in {"evidence_rag", "state_aware"}:
        result["evidence"] = _sanitized_evidence(record)
    if method == "state_aware":
        if "state" not in record or not isinstance(record["state"], Mapping):
            raise ViewError("state-aware view requires structured observed state")
        result["observed_state"] = deepcopy(record["state"])
    assert_model_view_safe(result)
    return result


def scoring_view(record: Mapping[str, Any]) -> dict[str, Any]:
    required = (
        "scenario_id",
        "family_id",
        "suite",
        "split",
        "label",
    )
    if any(key not in record for key in required):
        raise ViewError("scoring view lacks required fields")
    return {
        "scenario_id": record["scenario_id"],
        "family_id": record["family_id"],
        "pair_id": record.get("pair_id"),
        "conversation_id": record.get("conversation_id"),
        "turn_index": record.get("turn_index"),
        "suite": record["suite"],
        "split": record["split"],
        "decision_date": record.get("decision_date"),
        "label": deepcopy(record["label"]),
        "transformation": deepcopy(record.get("transformation")),
        "evidence_ids": [item.get("source_clause_id") for item in record.get("evidence", [])],
    }


def assert_model_view_safe(value: Any, path: str = "$") -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if key in FORBIDDEN_MODEL_KEYS:
                raise ViewError(f"forbidden model-view field at {path}.{key}")
            assert_model_view_safe(nested, f"{path}.{key}")
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            assert_model_view_safe(nested, f"{path}[{index}]")
