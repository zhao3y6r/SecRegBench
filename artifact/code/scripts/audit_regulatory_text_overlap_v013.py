#!/usr/bin/env python3
"""Detect long exact normalized overlap between synthetic dialogue and clauses."""

from __future__ import annotations

import argparse
import hashlib
import json
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if line.strip():
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{number}: expected object")
            rows.append(value)
    return rows


def compact(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text).lower()
    return "".join(character for character in normalized if character.isalnum())


def ngrams(text: str, width: int) -> set[str]:
    return {text[index : index + width] for index in range(max(0, len(text) - width + 1))}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("corpus", type=Path)
    parser.add_argument("clauses", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--minimum-characters", type=int, default=24)
    args = parser.parse_args()
    if args.minimum_characters < 16:
        raise ValueError("minimum overlap must be at least 16 normalized characters")
    corpus, clauses = read_jsonl(args.corpus), read_jsonl(args.clauses)
    index: dict[str, set[str]] = defaultdict(set)
    for clause in clauses:
        excerpt = clause.get("excerpt")
        if not isinstance(excerpt, str):
            raise ValueError("clause excerpt missing")
        for gram in ngrams(compact(excerpt), args.minimum_characters):
            index[gram].add(str(clause["clause_id"]))

    findings = []
    for row in corpus:
        for turn_index, turn in enumerate(row["dialogue"]):
            text = compact(turn["text"])
            matches: dict[str, set[str]] = {}
            for gram in ngrams(text, args.minimum_characters):
                clause_ids = index.get(gram)
                if clause_ids:
                    matches[hashlib.sha256(gram.encode("utf-8")).hexdigest()] = clause_ids
            for gram_hash, clause_ids in sorted(matches.items()):
                findings.append(
                    {
                        "scenario_id": row["scenario_id"],
                        "turn_index": turn_index,
                        "normalized_overlap_characters": args.minimum_characters,
                        "matched_ngram_sha256": gram_hash,
                        "clause_ids": sorted(clause_ids),
                    }
                )

    args.output_dir.mkdir(parents=True, exist_ok=False)
    findings_path = args.output_dir / "regulatory_text_overlap_findings_private.jsonl"
    findings_path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n" for row in findings),
        encoding="utf-8",
        newline="\n",
    )
    report = {
        "schema_version": "0.1.0",
        "status": "PASS_NO_LONG_EXACT_NORMALIZED_CLAUSE_OVERLAP" if not findings else "FLAGGED_FOR_SOURCE_TERMS_REVIEW",
        "normalization": "Unicode NFKC, lowercase, retain alphanumeric characters only",
        "minimum_overlap_characters": args.minimum_characters,
        "corpus_rows": len(corpus),
        "clause_rows": len(clauses),
        "finding_events": len(findings),
        "scenarios_flagged": len({row["scenario_id"] for row in findings}),
        "human_source_terms_reviews": 0,
        "limitations": [
            "The scan detects exact normalized substrings only and does not detect paraphrase.",
            "Shorter conventional regulatory phrases are below the fixed threshold.",
            "A passing scan is not a source-redistribution or legal approval.",
        ],
        "hashes": {
            "corpus": sha256(args.corpus),
            "clauses": sha256(args.clauses),
            "findings": sha256(findings_path),
        },
    }
    (args.output_dir / "regulatory_text_overlap_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not findings else 2


if __name__ == "__main__":
    raise SystemExit(main())
