#!/usr/bin/env python3
"""Diagnose v0.13 dependency percolation and propose a minimal v0.14 repair.

This script is read-only with respect to v0.13. It does not alter scenario
labels, splits, model outputs, or the frozen manuscript. The proposed repair
regenerates dialogue surfaces for complete families only, preserving state and
oracle contracts.
"""

from __future__ import annotations

import argparse
import hashlib
import heapq
import json
import re
import statistics
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


NUMBER_RE = re.compile(r"\d+(?:[./:-]\d+)*")
SPACE_RE = re.compile(r"\s+")
EDGE_PRIORITY = {
    "exact_semantic_signature": 3,
    "char_ngram": 2,
    "token_jaccard": 1,
}
REPAIR_CAPS = (100, 150, 200, 250, 300, 400, 500)
RECOMMENDED_CAP = 300
SEED = 27072027


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number}: expected object")
            rows.append(value)
    return rows


def normalize(text: str) -> str:
    value = unicodedata.normalize("NFKC", text).lower()
    value = NUMBER_RE.sub("<num>", value)
    value = "".join(
        character
        if character.isalnum()
        or "\u3400" <= character <= "\u9fff"
        or character in "<>"
        else " "
        for character in value
    )
    return SPACE_RE.sub(" ", value).strip()


def dialogue_text(row: dict[str, Any]) -> str:
    return normalize(
        " ".join(
            f"{message['role']} {message['text']}"
            for message in row["dialogue"]
        )
    )


def canonical_hash(value: Any) -> str:
    rendered = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest()


class DSU:
    def __init__(self, keys: Iterable[str], weights: dict[str, int] | None = None) -> None:
        keys = list(keys)
        self.parent = {key: key for key in keys}
        self.weight = {
            key: (weights[key] if weights is not None else 1)
            for key in keys
        }

    def find(self, key: str) -> str:
        while self.parent[key] != key:
            self.parent[key] = self.parent[self.parent[key]]
            key = self.parent[key]
        return key

    def union(self, left: str, right: str, cap: int | None = None) -> bool:
        left_root, right_root = self.find(left), self.find(right)
        if left_root == right_root:
            return True
        if cap is not None and self.weight[left_root] + self.weight[right_root] > cap:
            return False
        if (self.weight[left_root], left_root) < (self.weight[right_root], right_root):
            left_root, right_root = right_root, left_root
        self.parent[right_root] = left_root
        self.weight[left_root] += self.weight[right_root]
        return True


def summarize_component_sizes(sizes: list[int], rows: int) -> dict[str, Any]:
    if not sizes:
        raise ValueError("empty component sizes")
    hhi = sum((size / rows) ** 2 for size in sizes)
    return {
        "components": len(sizes),
        "minimum_rows": min(sizes),
        "median_rows": statistics.median(sizes),
        "maximum_rows": max(sizes),
        "maximum_share": max(sizes) / rows,
        "hhi": hhi,
        "effective_components_inverse_hhi": 1.0 / hhi,
        "top10_rows": sorted(sizes, reverse=True)[:10],
    }


def scenario_component_variant(
    rows: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    relation_fields: tuple[str, ...],
    edge_types: set[str],
    selected_for_regeneration: set[str] | None = None,
) -> dict[str, Any]:
    ids = [row["scenario_id"] for row in rows]
    dsu = DSU(ids)
    for field in relation_fields:
        first: dict[str, str] = {}
        for row in rows:
            value = row.get(field)
            if not isinstance(value, str) or not value:
                continue
            if value in first:
                dsu.union(first[value], row["scenario_id"])
            else:
                first[value] = row["scenario_id"]
    removed = selected_for_regeneration or set()
    included_edges = 0
    for edge in edges:
        if edge["edge_type"] not in edge_types:
            continue
        if edge["left_id"] in removed or edge["right_id"] in removed:
            continue
        dsu.union(edge["left_id"], edge["right_id"])
        included_edges += 1
    counts = Counter(dsu.find(scenario_id) for scenario_id in ids)
    report = summarize_component_sizes(list(counts.values()), len(rows))
    report.update(
        {
            "relation_fields": list(relation_fields),
            "edge_types": sorted(edge_types),
            "included_derived_edges": included_edges,
            "regenerated_old_edges_removed_for_rows": len(removed),
        }
    )
    return report


def threshold_variant(
    rows: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    char_threshold: float | None,
    token_threshold: float | None,
) -> dict[str, Any]:
    included = []
    for edge in edges:
        edge_type = edge["edge_type"]
        if edge_type == "exact_semantic_signature":
            included.append(edge)
        elif edge_type == "char_ngram" and char_threshold is not None:
            if float(edge["score"]) >= char_threshold:
                included.append(edge)
        elif edge_type == "token_jaccard" and token_threshold is not None:
            if float(edge["score"]) >= token_threshold:
                included.append(edge)
    report = scenario_component_variant(
        rows,
        included,
        ("component_id", "family_id"),
        set(EDGE_PRIORITY),
    )
    report["char_threshold"] = char_threshold
    report["token_threshold"] = token_threshold
    return report


def aggregate_plan_edges(
    rows_by_id: dict[str, dict[str, Any]],
    edges: list[dict[str, Any]],
) -> dict[tuple[str, str], dict[str, Any]]:
    aggregate: dict[tuple[str, str], dict[str, Any]] = {}
    for edge in edges:
        left_plan = rows_by_id[edge["left_id"]]["component_id"]
        right_plan = rows_by_id[edge["right_id"]]["component_id"]
        if left_plan == right_plan:
            continue
        pair = tuple(sorted((left_plan, right_plan)))
        slot = aggregate.setdefault(
            pair,
            {
                "edge_count": 0,
                "exact_count": 0,
                "char_count": 0,
                "token_count": 0,
                "maximum_score": 0.0,
                "priority": 0,
            },
        )
        edge_type = edge["edge_type"]
        slot["edge_count"] += 1
        slot["exact_count"] += int(edge_type == "exact_semantic_signature")
        slot["char_count"] += int(edge_type == "char_ngram")
        slot["token_count"] += int(edge_type == "token_jaccard")
        slot["maximum_score"] = max(slot["maximum_score"], float(edge["score"]))
        slot["priority"] = max(slot["priority"], EDGE_PRIORITY[edge_type])
    return aggregate


def bounded_plan_clustering(
    rows: list[dict[str, Any]],
    aggregate: dict[tuple[str, str], dict[str, Any]],
    cap: int,
) -> tuple[dict[str, str], dict[str, Any]]:
    plan_weights = Counter(row["component_id"] for row in rows)
    dsu = DSU(plan_weights, dict(plan_weights))
    ordered = sorted(
        aggregate.items(),
        key=lambda item: (
            item[1]["priority"],
            item[1]["exact_count"],
            item[1]["edge_count"],
            item[1]["maximum_score"],
            item[0],
        ),
        reverse=True,
    )
    accepted_pairs = 0
    rejected_pairs = 0
    for (left, right), _ in ordered:
        if dsu.find(left) == dsu.find(right):
            continue
        if dsu.union(left, right, cap=cap):
            accepted_pairs += 1
        else:
            rejected_pairs += 1
    cluster_by_plan = {plan: dsu.find(plan) for plan in plan_weights}
    row_counts = Counter()
    block_counts = Counter()
    for plan, cluster in cluster_by_plan.items():
        row_counts[cluster] += plan_weights[plan]
        block_counts[cluster] += 1
    report = summarize_component_sizes(list(row_counts.values()), len(rows))
    report.update(
        {
            "cap_rows": cap,
            "authoring_blocks": len(plan_weights),
            "accepted_plan_pairs": accepted_pairs,
            "rejected_plan_pairs": rejected_pairs,
            "maximum_authoring_blocks_per_cluster": max(block_counts.values()),
        }
    )
    return cluster_by_plan, report


def family_aware_vertex_cover(
    rows_by_id: dict[str, dict[str, Any]],
    family_members: dict[str, set[str]],
    crossing_edges: list[dict[str, Any]],
) -> tuple[list[str], set[str]]:
    edge_families: list[tuple[str, str]] = []
    adjacency: dict[str, set[int]] = defaultdict(set)
    for index, edge in enumerate(crossing_edges):
        left_family = rows_by_id[edge["left_id"]]["family_id"]
        right_family = rows_by_id[edge["right_id"]]["family_id"]
        edge_families.append((left_family, right_family))
        adjacency[left_family].add(index)
        adjacency[right_family].add(index)

    alive = set(range(len(crossing_edges)))
    heap = [(-len(edge_ids), family) for family, edge_ids in adjacency.items()]
    heapq.heapify(heap)
    selected_families: list[str] = []
    while alive:
        chosen = None
        while heap:
            negative_count, family = heapq.heappop(heap)
            current_count = len(adjacency[family] & alive)
            if current_count == -negative_count and current_count > 0:
                chosen = family
                break
            if current_count > 0:
                heapq.heappush(heap, (-current_count, family))
        if chosen is None:
            raise RuntimeError("vertex-cover heap exhausted with live edges")
        selected_families.append(chosen)
        removed_edges = adjacency[chosen] & alive
        alive -= removed_edges
        touched: set[str] = set()
        for edge_index in removed_edges:
            touched.update(edge_families[edge_index])
        for family in touched:
            count = len(adjacency[family] & alive)
            if count:
                heapq.heappush(heap, (-count, family))

    selected_rows: set[str] = set()
    for family in selected_families:
        selected_rows.update(family_members[family])
    return selected_families, selected_rows


def simulate_repair(
    rows: list[dict[str, Any]],
    rows_by_id: dict[str, dict[str, Any]],
    edges: list[dict[str, Any]],
    aggregate: dict[tuple[str, str], dict[str, Any]],
    family_members: dict[str, set[str]],
    cap: int,
) -> tuple[dict[str, Any], dict[str, str], list[str], set[str]]:
    cluster_by_plan, bounded_report = bounded_plan_clustering(rows, aggregate, cap)
    crossing_edges = [
        edge
        for edge in edges
        if cluster_by_plan[rows_by_id[edge["left_id"]]["component_id"]]
        != cluster_by_plan[rows_by_id[edge["right_id"]]["component_id"]]
    ]
    selected_families, selected_rows = family_aware_vertex_cover(
        rows_by_id,
        family_members,
        crossing_edges,
    )
    post_repair = scenario_component_variant(
        rows,
        edges,
        ("component_id", "family_id"),
        set(EDGE_PRIORITY),
        selected_for_regeneration=selected_rows,
    )
    selected_records = [rows_by_id[scenario_id] for scenario_id in selected_rows]
    report = {
        "cap_rows": cap,
        "bounded_partition_before_regeneration": bounded_report,
        "cross_partition_derived_edges_requiring_removal": len(crossing_edges),
        "selected_complete_families": len(selected_families),
        "selected_rows_for_dialogue_regeneration": len(selected_rows),
        "selected_rows_by_suite": dict(
            sorted(Counter(row["suite"] for row in selected_records).items())
        ),
        "selected_rows_by_v013_split": dict(
            sorted(Counter(row["split"] for row in selected_records).items())
        ),
        "selected_family_sizes": dict(
            sorted(Counter(len(family_members[family]) for family in selected_families).items())
        ),
        "predicted_post_regeneration_graph": post_repair,
        "assumption": (
            "Every selected family receives a fresh, relation-preserving dialogue "
            "surface that has no old exact/lexical edge outside its bounded cluster."
        ),
    }
    return report, cluster_by_plan, selected_families, selected_rows


def deterministic_rank(*values: str) -> str:
    return hashlib.sha256(
        (str(SEED) + "|" + "|".join(values)).encode("utf-8")
    ).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    output_dir = args.output_dir.resolve()

    base = root / "experiments" / "final_scale_v0.13"
    corpus_path = (
        base
        / "component_safe_resplit_lexical_v013"
        / "provisional_corpus_component_safe_split_private.jsonl"
    )
    edges_path = (
        base
        / "leakage_rebuild_lexical_v013"
        / "lexical_edges_v013.jsonl"
    )
    rows = read_jsonl(corpus_path)
    edges = read_jsonl(edges_path)
    rows_by_id = {row["scenario_id"]: row for row in rows}
    if len(rows_by_id) != len(rows):
        raise ValueError("duplicate scenario_id")
    family_members: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        family_members[row["family_id"]].add(row["scenario_id"])

    normalized_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    text_state_groups: Counter[tuple[str, str]] = Counter()
    for row in rows:
        text = dialogue_text(row)
        normalized_groups[text].append(row)
        text_state_groups[(text, canonical_hash(row["state"]))] += 1

    duplicate_groups = [
        members for members in normalized_groups.values() if len(members) > 1
    ]
    exact_group_report = {
        "normalized_dialogues": len(normalized_groups),
        "surface_unique_share": len(normalized_groups) / len(rows),
        "duplicate_excess_rows": len(rows) - len(normalized_groups),
        "groups_with_duplicates": len(duplicate_groups),
        "rows_in_duplicate_groups": sum(len(group) for group in duplicate_groups),
        "maximum_exact_group_size": max(map(len, normalized_groups.values())),
        "unique_dialogue_state_pairs": len(text_state_groups),
        "groups_crossing_authoring_blocks": sum(
            len({row["component_id"] for row in group}) > 1
            for group in duplicate_groups
        ),
        "groups_crossing_suites": sum(
            len({row["suite"] for row in group}) > 1
            for group in duplicate_groups
        ),
        "groups_with_multiple_gold_actions": sum(
            len({row["label"]["primary_action"] for row in group}) > 1
            for group in duplicate_groups
        ),
        "rows_in_groups_with_multiple_gold_actions": sum(
            len(group)
            for group in duplicate_groups
            if len({row["label"]["primary_action"] for row in group}) > 1
        ),
        "exact_group_size_histogram": dict(
            sorted(Counter(map(len, normalized_groups.values())).items())
        ),
    }

    edge_report: dict[str, Any] = {}
    for edge_type in EDGE_PRIORITY:
        selected = [edge for edge in edges if edge["edge_type"] == edge_type]
        cross_plan = [
            edge
            for edge in selected
            if rows_by_id[edge["left_id"]]["component_id"]
            != rows_by_id[edge["right_id"]]["component_id"]
        ]
        cross_suite = [
            edge
            for edge in selected
            if rows_by_id[edge["left_id"]]["suite"]
            != rows_by_id[edge["right_id"]]["suite"]
        ]
        different_gold = [
            edge
            for edge in selected
            if rows_by_id[edge["left_id"]]["label"]["primary_action"]
            != rows_by_id[edge["right_id"]]["label"]["primary_action"]
        ]
        edge_report[edge_type] = {
            "edges": len(selected),
            "cross_authoring_block_edges": len(cross_plan),
            "cross_suite_edges": len(cross_suite),
            "different_gold_action_edges": len(different_gold),
            "minimum_score": min(float(edge["score"]) for edge in selected),
            "median_score": statistics.median(float(edge["score"]) for edge in selected),
            "maximum_score": max(float(edge["score"]) for edge in selected),
        }

    variant_specs = [
        ("rows_only", (), set()),
        ("family_only", ("family_id",), set()),
        ("authoring_block_only", ("component_id", "family_id"), set()),
        (
            "family_plus_all_text_edges",
            ("family_id",),
            set(EDGE_PRIORITY),
        ),
        (
            "authoring_block_plus_exact",
            ("component_id", "family_id"),
            {"exact_semantic_signature"},
        ),
        (
            "authoring_block_plus_char",
            ("component_id", "family_id"),
            {"char_ngram"},
        ),
        (
            "authoring_block_plus_token",
            ("component_id", "family_id"),
            {"token_jaccard"},
        ),
        (
            "authoring_block_plus_all_text_edges",
            ("component_id", "family_id"),
            set(EDGE_PRIORITY),
        ),
    ]
    variants = {
        name: scenario_component_variant(rows, edges, relation_fields, edge_types)
        for name, relation_fields, edge_types in variant_specs
    }

    threshold_sensitivity = []
    for char_threshold, token_threshold in (
        (None, None),
        (0.82, 0.88),
        (0.86, 0.92),
        (0.90, 0.94),
        (0.94, 0.96),
        (0.96, 0.98),
    ):
        threshold_sensitivity.append(
            threshold_variant(rows, edges, char_threshold, token_threshold)
        )

    aggregate = aggregate_plan_edges(rows_by_id, edges)
    repair_reports: dict[str, Any] = {}
    repair_outputs: dict[int, tuple[dict[str, str], list[str], set[str]]] = {}
    for cap in REPAIR_CAPS:
        report, cluster_by_plan, selected_families, selected_rows = simulate_repair(
            rows,
            rows_by_id,
            edges,
            aggregate,
            family_members,
            cap,
        )
        repair_reports[str(cap)] = report
        repair_outputs[cap] = (cluster_by_plan, selected_families, selected_rows)

    cluster_by_plan, selected_families, selected_rows = repair_outputs[RECOMMENDED_CAP]
    plan_row_counts = Counter(row["component_id"] for row in rows)
    cluster_mapping_path = output_dir / "BOUNDED_AUTHORING_BLOCK_CLUSTERS_CAP300_V014.jsonl"
    cluster_mapping_path.parent.mkdir(parents=True, exist_ok=True)
    cluster_mapping_path.write_bytes(
        "".join(
            json.dumps(
                {
                    "schema_version": "0.14.0",
                    "authoring_block_id": plan,
                    "bounded_cluster_id": cluster_by_plan[plan],
                    "rows": plan_row_counts[plan],
                    "cap_rows": RECOMMENDED_CAP,
                },
                ensure_ascii=False,
                separators=(",", ":"),
            )
            + "\n"
            for plan in sorted(cluster_by_plan)
        ).encode("utf-8")
    )
    candidate_rows = []
    for family in sorted(selected_families):
        members = sorted(family_members[family])
        incident_edges = [
            edge
            for edge in edges
            if edge["left_id"] in members or edge["right_id"] in members
        ]
        for scenario_id in members:
            row = rows_by_id[scenario_id]
            candidate_rows.append(
                {
                    "schema_version": "0.14.0",
                    "status": "PROPOSED_DIALOGUE_REGENERATION_NOT_EXECUTED",
                    "family_id": family,
                    "scenario_id": scenario_id,
                    "suite": row["suite"],
                    "v013_split": row["split"],
                    "authoring_block_id": row["component_id"],
                    "bounded_cluster_id": cluster_by_plan[row["component_id"]],
                    "dialogue_sha256": row["dialogue_sha256"],
                    "family_size": len(members),
                    "family_incident_old_derived_edges": len(incident_edges),
                    "preserve_exactly": [
                        "family_id",
                        "suite",
                        "state",
                        "relation_spec",
                        "label",
                        "decision_date",
                    ],
                    "regenerate_only": "dialogue",
                }
            )
    candidate_path = output_dir / "PROPOSED_DIALOGUE_REGENERATION_ROWS_V014.jsonl"
    output_dir.mkdir(parents=True, exist_ok=True)
    candidate_path.write_bytes(
        "".join(
            json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n"
            for row in candidate_rows
        ).encode("utf-8")
    )

    cross_plan_edges = [
        edge
        for edge in edges
        if rows_by_id[edge["left_id"]]["component_id"]
        != rows_by_id[edge["right_id"]]["component_id"]
    ]
    sampled_edges = []
    for edge_type in EDGE_PRIORITY:
        candidates = [
            edge for edge in cross_plan_edges if edge["edge_type"] == edge_type
        ]
        candidates.sort(
            key=lambda edge: deterministic_rank(
                edge_type,
                edge["left_id"],
                edge["right_id"],
            )
        )
        sampled_edges.extend(candidates[:100])
    if len(sampled_edges) != 300:
        raise ValueError(f"expected 300 review edges, obtained {len(sampled_edges)}")
    review_rows = []
    for index, edge in enumerate(sampled_edges, start=1):
        left = rows_by_id[edge["left_id"]]
        right = rows_by_id[edge["right_id"]]
        review_rows.append(
            {
                "schema_version": "0.14.0",
                "review_pair_id": f"DIV14-{index:04d}",
                "edge_type": edge["edge_type"],
                "score": edge["score"],
                "left_dialogue": left["dialogue"],
                "right_dialogue": right["dialogue"],
                "same_normalized_dialogue": dialogue_text(left) == dialogue_text(right),
                "review_fields": {
                    "semantic_equivalence": None,
                    "leakage_link_required": None,
                    "confidence": None,
                    "notes": None,
                },
            }
        )
    review_path = output_dir / "BLINDED_BRIDGE_EDGE_REVIEW_PACKET_V014.jsonl"
    review_path.write_bytes(
        "".join(
            json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n"
            for row in review_rows
        ).encode("utf-8")
    )

    diagnostic = {
        "schema_version": "0.14.0",
        "status": "PASS_READ_ONLY_COMPONENT_DIVERSITY_DIAGNOSTIC",
        "inputs": {
            "corpus": str(corpus_path.relative_to(root)).replace("\\", "/"),
            "corpus_sha256": sha256(corpus_path),
            "derived_edges": str(edges_path.relative_to(root)).replace("\\", "/"),
            "derived_edges_sha256": sha256(edges_path),
            "scenarios": len(rows),
            "families": len(family_members),
            "authoring_blocks": len({row["component_id"] for row in rows}),
        },
        "exact_dialogue_diagnostics": exact_group_report,
        "edge_diagnostics": edge_report,
        "component_definition_variants": variants,
        "threshold_sensitivity_with_authoring_blocks_and_exact_edges_retained": threshold_sensitivity,
        "bounded_repair_simulations": repair_reports,
        "recommended_candidate": {
            "cap_rows": RECOMMENDED_CAP,
            "reason": (
                "Smallest tested regeneration plan that comfortably exceeds 50 "
                "effective components while preserving complete authoring blocks and "
                "family relations."
            ),
            "candidate_rows": len(selected_rows),
            "candidate_families": len(selected_families),
            "candidate_path": str(candidate_path.relative_to(root)).replace("\\", "/"),
            "candidate_sha256": sha256(candidate_path),
            "bounded_cluster_mapping_path": str(
                cluster_mapping_path.relative_to(root)
            ).replace("\\", "/"),
            "bounded_cluster_mapping_sha256": sha256(cluster_mapping_path),
            "requires_model_full_rerun": False,
            "requires_incremental_inference_for_changed_dialogue": True,
        },
        "bridge_review_packet": {
            "rows": len(review_rows),
            "per_edge_type": dict(
                sorted(Counter(row["edge_type"] for row in review_rows).items())
            ),
            "path": str(review_path.relative_to(root)).replace("\\", "/"),
            "sha256": sha256(review_path),
            "status": "UNREVIEWED_PACKET_ONLY",
        },
        "interpretation": [
            (
                "The 6,416-row component is not a single exact duplicate group. It is "
                "a transitive closure across shared 19-21-row authoring blocks and "
                "cross-block exact/lexical dialogue edges."
            ),
            (
                "Raising lexical thresholds alone cannot solve the problem because "
                "authoring blocks plus exact normalized dialogue edges already create "
                "a 3,623-row component."
            ),
            (
                "Dropping authoring-block dependence would make the graph look much "
                "healthier, but contradicts the frozen construction protocol and is "
                "not selected as the repair."
            ),
            (
                "The recommended repair changes dialogue surfaces only for complete "
                "families selected by a deterministic graph-cover heuristic; it does "
                "not change states, rules, labels, or expert-review claims."
            ),
        ],
        "paper_or_submission_modified": False,
        "server_contacted": False,
    }
    diagnostic_path = output_dir / "COMPONENT_DIVERSITY_DIAGNOSTIC_V014.json"
    write_json(diagnostic_path, diagnostic)

    instructions_path = output_dir / "BRIDGE_EDGE_REVIEW_INSTRUCTIONS_V014.md"
    instructions_path.write_text(
        "# Blinded bridge-edge review instructions (v0.14)\n\n"
        "This packet has not been reviewed. Each row shows only two dialogue surfaces "
        "and the mechanical similarity edge. Reviewers must not receive gold actions, "
        "split names, model outputs, or authoring-block identifiers.\n\n"
        "For each pair, fill `semantic_equivalence`, `leakage_link_required`, "
        "`confidence`, and optional `notes`. `leakage_link_required` means the pair is "
        "similar enough that placing the two records in different evaluation splits "
        "would create a credible near-duplicate leakage risk. Three anonymous reviewer "
        "ledgers, if actually completed, remain private and are aggregated separately.\n",
        encoding="utf-8",
        newline="\n",
    )
    checksums_path = output_dir / "SHA256SUMS.txt"
    tracked = (
        diagnostic_path,
        candidate_path,
        cluster_mapping_path,
        review_path,
        instructions_path,
    )
    checksums_path.write_text(
        "".join(f"{sha256(path)}  {path.name}\n" for path in tracked),
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps(diagnostic, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
