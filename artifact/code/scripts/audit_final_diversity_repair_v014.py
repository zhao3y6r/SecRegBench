#!/usr/bin/env python3
"""Audit the materialized v0.14 corpus against the frozen graph-quality gates."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import sys
from collections import Counter
from pathlib import Path
from typing import Any


SCRIPT = Path(__file__).resolve()
sys.path.insert(0, str(SCRIPT.parent))
from analyze_component_diversity_v014 import canonical_hash, dialogue_text  # noqa: E402


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("corpus", type=Path)
    parser.add_argument("lexical_edges", type=Path)
    parser.add_argument("lexical_report", type=Path)
    parser.add_argument("component_mapping", type=Path)
    parser.add_argument("component_report", type=Path)
    parser.add_argument("bounded_clusters", type=Path)
    parser.add_argument("preregistration", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    corpus = read_jsonl(args.corpus)
    edges = read_jsonl(args.lexical_edges)
    lexical_report = json.loads(args.lexical_report.read_text(encoding="utf-8"))
    mapping = read_jsonl(args.component_mapping)
    component_report = json.loads(args.component_report.read_text(encoding="utf-8"))
    cluster_rows = read_jsonl(args.bounded_clusters)
    prereg = json.loads(args.preregistration.read_text(encoding="utf-8"))
    gates = prereg["graph_quality_gates"]

    by_id = {row["scenario_id"]: row for row in corpus}
    mapping_by_id = {row["scenario_id"]: row for row in mapping}
    if (
        len(corpus) != gates["scenarios"]
        or len(by_id) != len(corpus)
        or set(by_id) != set(mapping_by_id)
    ):
        raise ValueError("corpus/component scenario coverage mismatch")
    if lexical_report.get("records_sha256") != sha256(args.corpus):
        raise ValueError("lexical report does not bind corpus")
    if lexical_report.get("edges_sha256") != sha256(args.lexical_edges):
        raise ValueError("lexical report does not bind edge file")
    if component_report.get("records_sha256") != sha256(args.corpus):
        raise ValueError("component report does not bind corpus")
    if component_report.get("mapping_sha256") != sha256(args.component_mapping):
        raise ValueError("component report does not bind mapping")
    if component_report.get("derived_edges_sha256") != sha256(args.lexical_edges):
        raise ValueError("component report does not bind lexical edges")

    component_sizes = Counter(row["component_id"] for row in mapping)
    sizes = list(component_sizes.values())
    hhi = sum((size / len(corpus)) ** 2 for size in sizes)
    effective = 1.0 / hhi
    normalized_dialogues = {dialogue_text(row) for row in corpus}
    dialogue_state_pairs = {
        (dialogue_text(row), canonical_hash(row["state"])) for row in corpus
    }
    cluster_by_plan = {
        row["authoring_block_id"]: row["bounded_cluster_id"]
        for row in cluster_rows
    }
    if len(cluster_by_plan) != gates["authoring_blocks"] or any(
        row["component_id"] not in cluster_by_plan for row in corpus
    ):
        raise ValueError("bounded-cluster mapping does not cover all authoring blocks")
    cross_bounded_edges = [
        edge
        for edge in edges
        if cluster_by_plan[by_id[edge["left_id"]]["component_id"]]
        != cluster_by_plan[by_id[edge["right_id"]]["component_id"]]
    ]

    observed = {
        "scenarios": len(corpus),
        "families": len({row["family_id"] for row in corpus}),
        "authoring_blocks": len({row["component_id"] for row in corpus}),
        "realized_components": len(sizes),
        "minimum_component_rows": min(sizes),
        "median_component_rows": statistics.median(sizes),
        "maximum_component_rows": max(sizes),
        "maximum_component_share": max(sizes) / len(corpus),
        "hhi": hhi,
        "effective_components_inverse_hhi": effective,
        "normalized_dialogues": len(normalized_dialogues),
        "surface_unique_share": len(normalized_dialogues) / len(corpus),
        "unique_dialogue_state_pairs": len(dialogue_state_pairs),
        "unique_dialogue_state_pair_share": len(dialogue_state_pairs) / len(corpus),
        "lexical_edges": len(edges),
        "cross_bounded_cluster_lexical_edges": len(cross_bounded_edges),
        "cross_bounded_cluster_edge_examples": cross_bounded_edges[:20],
        "component_report_cross_split_components_before_resplit": len(
            component_report.get("cross_split_components") or []
        ),
    }
    checks = {
        "scenarios_exact": observed["scenarios"] == gates["scenarios"],
        "families_exact": observed["families"] == gates["families"],
        "authoring_blocks_exact": observed["authoring_blocks"]
        == gates["authoring_blocks"],
        "maximum_component_rows": observed["maximum_component_rows"]
        <= gates["maximum_component_rows"],
        "maximum_component_share": observed["maximum_component_share"]
        <= gates["maximum_component_share"],
        "minimum_effective_components": observed[
            "effective_components_inverse_hhi"
        ]
        >= gates["minimum_effective_components_inverse_hhi"],
        "minimum_realized_components": observed["realized_components"]
        >= gates["minimum_realized_components"],
        "minimum_unique_dialogue_state_pair_share": observed[
            "unique_dialogue_state_pair_share"
        ]
        >= gates["minimum_unique_dialogue_state_pair_share"],
        "zero_cross_bounded_cluster_lexical_edges": observed[
            "cross_bounded_cluster_lexical_edges"
        ]
        == 0,
    }
    report = {
        "schema_version": "0.14.0",
        "status": (
            "PASS_FROZEN_DIVERSITY_GRAPH_GATES_PENDING_COMPONENT_SAFE_RESPLIT"
            if all(checks.values())
            else "FAIL_FROZEN_DIVERSITY_GRAPH_GATES"
        ),
        "observed": observed,
        "frozen_gates": gates,
        "checks": checks,
        "all_checks_pass": all(checks.values()),
        "surface_unique_share_is_descriptive_not_a_hard_gate": True,
        "gold_or_model_evaluation_outputs_loaded": False,
        "input_hashes": {
            "corpus": sha256(args.corpus),
            "lexical_edges": sha256(args.lexical_edges),
            "lexical_report": sha256(args.lexical_report),
            "component_mapping": sha256(args.component_mapping),
            "component_report": sha256(args.component_report),
            "bounded_clusters": sha256(args.bounded_clusters),
            "preregistration": sha256(args.preregistration),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(
        (json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
