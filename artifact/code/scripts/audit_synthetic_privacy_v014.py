#!/usr/bin/env python3
"""Fail-explicit automatic privacy scan for the final v0.14 dialogue corpus."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


PATTERNS = {
    "mainland_mobile_number": re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)"),
    "mainland_identity_number": re.compile(r"(?<!\d)\d{17}[\dXx](?!\d)"),
    "long_account_like_number": re.compile(r"(?<!\d)\d{12,19}(?!\d)"),
    "email_address": re.compile(
        r"(?i)(?<![\w.])[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}(?![\w.])"
    ),
    "ipv4_address": re.compile(r"(?<!\d)(?:\d{1,3}\.){3}\d{1,3}(?!\d)"),
    "credential_assignment": re.compile(
        r"(?i)(?:password|passwd|api[_-]?key|access[_-]?token|secret[_-]?key)\s*[:=]"
    ),
    "explicit_chinese_identifier_disclosure": re.compile(
        r"(?:身份证(?:号|号码)?|手机(?:号|号码)?|银行卡号|账户号|账号)"
        r"\s*(?:是|为|[:：])"
    ),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{line_number}: expected object")
        rows.append(value)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("corpus", type=Path)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    if args.output_dir.exists():
        raise FileExistsError(args.output_dir)

    rows = read_jsonl(args.corpus)
    findings: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()
    turns = 0
    for row in rows:
        scenario_id = str(row.get("scenario_id", ""))
        dialogue = row.get("dialogue")
        if not scenario_id or not isinstance(dialogue, list):
            raise ValueError("corpus row lacks scenario_id/dialogue")
        for turn_index, turn in enumerate(dialogue):
            turns += 1
            text = turn.get("text") if isinstance(turn, dict) else None
            if not isinstance(text, str):
                raise ValueError(f"{scenario_id}: turn {turn_index} lacks text")
            for finding_kind, pattern in PATTERNS.items():
                if pattern.search(text):
                    counts[finding_kind] += 1
                    findings.append(
                        {
                            "scenario_id": scenario_id,
                            "turn_index": turn_index,
                            "finding_kind": finding_kind,
                        }
                    )

    args.output_dir.mkdir(parents=True)
    findings_path = args.output_dir / "privacy_pattern_findings_private.jsonl"
    findings_path.write_text(
        "".join(
            json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
            for item in findings
        ),
        encoding="utf-8",
        newline="\n",
    )
    status = (
        "PASS_NO_HIGH_RISK_IDENTIFIER_OR_CREDENTIAL_PATTERN"
        if not findings
        else "FLAGGED_FOR_AUTHOR_PRIVACY_ADJUDICATION"
    )
    report = {
        "schema_version": "0.14.0",
        "status": status,
        "scope": "automatic_regex_scan_of_every_dialogue_turn_in_the_final_v014_corpus",
        "corpus_rows": len(rows),
        "dialogue_turns": turns,
        "pattern_definitions": {
            name: pattern.pattern for name, pattern in PATTERNS.items()
        },
        "finding_events": len(findings),
        "scenarios_flagged": len({item["scenario_id"] for item in findings}),
        "counts_by_kind": dict(sorted(counts.items())),
        "automatic_only": True,
        "practitioner_review_is_separate": True,
        "limitations": [
            "Regex scanning cannot establish absence of all personal or sensitive information.",
            "It does not infer whether an ordinary name or organization refers to a real person.",
            "A pass is not legal, institutional, or human privacy approval.",
        ],
        "hashes": {
            "corpus": sha256(args.corpus),
            "findings": sha256(findings_path),
        },
    }
    report_path = args.output_dir / "SYNTHETIC_PRIVACY_SCAN_REPORT_V014.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": status, "rows": len(rows), "turns": turns, "findings": len(findings)}, indent=2))
    return 0 if not findings else 2


if __name__ == "__main__":
    raise SystemExit(main())
