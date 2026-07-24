#!/usr/bin/env python3
"""Compile the public SecRegBench held-out evaluation requests.

The compiler is deterministic. Labels and split-construction provenance are
kept out of model messages. The job ledger retains only a hash of the target
action so that request construction can be audited before scoring.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any


METHODS = (
    "dialogue_only",
    "state_only",
    "oracle_evidence",
    "state_oracle_evidence",
)


def canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: object) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"{path}: line {line_number} is not an object")
        rows.append(value)
    return rows


def unique_map(
    rows: list[dict[str, Any]], key: str, label: str
) -> dict[str, dict[str, Any]]:
    output: dict[str, dict[str, Any]] = {}
    for row in rows:
        value = row.get(key)
        if not isinstance(value, str) or not value or value in output:
            raise ValueError(f"{label}: invalid or duplicate {key}: {value!r}")
        output[value] = row
    return output


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(
        "".join(canonical_json(row) + "\n" for row in rows),
        encoding="utf-8",
        newline="\n",
    )


def evidence_for(
    row: dict[str, Any],
    rules: dict[str, dict[str, Any]],
    clauses: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    clause_ids: set[str] = set()
    for rule_id in row["label"]["controlling_rule_ids"]:
        rule = rules.get(rule_id)
        if rule is None:
            raise ValueError(f"{row['scenario_id']}: missing rule {rule_id}")
        clause_ids.update(rule["source_clause_ids"])
    evidence: list[dict[str, Any]] = []
    for clause_id in sorted(clause_ids):
        clause = clauses.get(clause_id)
        if clause is None:
            raise ValueError(f"{row['scenario_id']}: missing evidence {clause_id}")
        evidence.append(
            {
                "clause_id": clause_id,
                "issuer": clause["issuer"],
                "title": clause["title"],
                "article": clause["article"],
                "effective_from": clause["effective_from"],
                "effective_to": clause["effective_to"],
                "excerpt": clause["excerpt"],
            }
        )
    return evidence


def evaluation_view(
    row: dict[str, Any], method: str, evidence: list[dict[str, Any]]
) -> dict[str, Any]:
    view: dict[str, Any] = {
        "decision_date": row["decision_date"],
        "dialogue": row["dialogue"],
    }
    if method in {"state_only", "state_oracle_evidence"}:
        view["typed_state"] = row["state"]
    if method in {"oracle_evidence", "state_oracle_evidence"}:
        view["official_clause_evidence"] = evidence
    return view


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("corpus", type=Path)
    parser.add_argument("rule_atoms", type=Path)
    parser.add_argument("evidence_inputs", type=Path)
    parser.add_argument("system_prompt", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--model", default="Qwen2-7B-Instruct")
    parser.add_argument("--split", default="heldout")
    parser.add_argument("--job-prefix", default="EVAL14")
    parser.add_argument("--system-slot", default="public_openai_compatible")
    args = parser.parse_args()

    if not args.job_prefix or any(
        character not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
        for character in args.job_prefix
    ):
        raise ValueError("invalid job prefix")

    corpus = [
        row for row in read_jsonl(args.corpus) if row.get("split") == args.split
    ]
    rules = unique_map(read_jsonl(args.rule_atoms), "rule_id", "rule atom")
    clauses = unique_map(
        read_jsonl(args.evidence_inputs), "clause_id", "evidence input"
    )
    system_prompt = args.system_prompt.read_text(encoding="utf-8").strip()
    if not system_prompt:
        raise ValueError("system prompt is empty")

    jobs: list[dict[str, Any]] = []
    requests: list[dict[str, Any]] = []
    method_counts: Counter[str] = Counter()
    for row in sorted(corpus, key=lambda item: item["scenario_id"]):
        evidence = evidence_for(row, rules, clauses)
        for method in METHODS:
            view = evaluation_view(row, method, evidence)
            job_id = (
                f"{args.job_prefix}-{method.upper().replace('_', '-')}-"
                f"{row['scenario_id']}"
            )
            payload = {
                "model": args.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": canonical_json(view)},
                ],
                "temperature": 0.0,
                "max_tokens": 64,
                "stream": False,
                "response_format": {"type": "json_object"},
                "chat_template_kwargs": {"enable_thinking": False},
            }
            jobs.append(
                {
                    "schema_version": "0.20.0",
                    "status": "prepared_label_free_evaluation_not_run",
                    "job_id": job_id,
                    "scenario_id": row["scenario_id"],
                    "family_id": row["family_id"],
                    "component_id": row["leakage_component_id"],
                    "design_component_id": row["component_id"],
                    "suite": row["suite"],
                    "split": row["split"],
                    "method": method,
                    "system_slot": args.system_slot,
                    "exact_request_group": job_id,
                    "repeat_policy": "single_first_attempt",
                    "repeat": 1,
                    "model_input_sha256": digest(view),
                    "gold_action_sha256": digest(row["label"]["primary_action"]),
                }
            )
            requests.append(
                {
                    "schema_version": "0.20.0",
                    "job_id": job_id,
                    "scenario_id": row["scenario_id"],
                    "method": method,
                    "system_slot": args.system_slot,
                    "model_input_sha256": digest(view),
                    "request_sha256": digest(payload),
                    "request_payload": payload,
                }
            )
            method_counts[method] += 1

    args.output_dir.mkdir(parents=True, exist_ok=True)
    jobs_path = args.output_dir / "evaluation_jobs.jsonl"
    requests_path = args.output_dir / "evaluation_requests.jsonl"
    write_jsonl(jobs_path, jobs)
    write_jsonl(requests_path, requests)
    report = {
        "schema_version": "0.20.0",
        "status": "PASS_PUBLIC_LABEL_FREE_EVALUATION_COMPILATION",
        "split": args.split,
        "scenarios": len(corpus),
        "jobs": len(jobs),
        "requests": len(requests),
        "method_counts": dict(sorted(method_counts.items())),
        "labels_in_requests": False,
        "credentials_or_endpoints_in_requests": False,
        "oracle_evidence_is_retrieval_result": False,
        "hashes": {
            "corpus": sha256(args.corpus),
            "rule_atoms": sha256(args.rule_atoms),
            "evidence_inputs": sha256(args.evidence_inputs),
            "system_prompt": sha256(args.system_prompt),
            "jobs": sha256(jobs_path),
            "requests": sha256(requests_path),
        },
    }
    report_path = args.output_dir / "compilation_report.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
