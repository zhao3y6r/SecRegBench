#!/usr/bin/env python3
"""Build v0.14 held-out paper assets from a frozen machine-stage report."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


SCRIPT = Path(__file__).resolve()
sys.path.insert(0, str(SCRIPT.parent))
import build_paper_assets_v012 as base  # noqa: E402


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate(report: dict[str, Any]) -> None:
    if report.get("status") != base.EXPECTED_STATUS:
        raise ValueError("evaluation report status is not the accepted machine-stage status")
    if report.get("scenarios") != 10000:
        raise ValueError("v0.14 report must bind the full 10,000-row corpus")
    if report.get("first_generation_jobs") != 8000:
        raise ValueError("v0.14 report must contain 2,000 held-out rows times four methods")
    if report.get("bootstrap_replicates") != 10000:
        raise ValueError("paper assets require 10,000 bootstrap replicates")
    if tuple(report.get("methods", [])) != base.METHODS:
        raise ValueError("method order/coverage mismatch")
    for method in base.METHODS:
        metrics = report.get("results", {}).get(method, {}).get("heldout")
        if not isinstance(metrics, dict) or metrics.get("n") != 2000:
            raise ValueError(f"{method}: expected exactly 2,000 held-out predictions")
        if not isinstance(metrics.get("component_bootstrap_ci95"), dict):
            raise ValueError(f"{method}: missing component-bootstrap intervals")
    if any(name not in report.get("heldout_baselines", {}) for name in base.BASELINE_LABELS):
        raise ValueError("required held-out baselines are missing")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("evaluation_report", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--physical-checkpoint", required=True)
    args = parser.parse_args()
    report = base.load(args.evaluation_report)
    validate(report)
    output = args.output_dir
    if output.exists() and any(output.iterdir()):
        raise ValueError(f"refusing to overwrite non-empty output: {output}")
    output.mkdir(parents=True, exist_ok=True)
    base.plt.rcParams.update({"font.size": 8, "pdf.fonttype": 42, "ps.fonttype": 42})

    main_path = output / "heldout_main_metrics.tex"
    comparison_path = output / "heldout_information_ablation.tex"
    main_path.write_text(base.main_table(report), encoding="utf-8", newline="\n")
    comparison_path.write_text(base.comparison_table(report), encoding="utf-8", newline="\n")
    metric_png = output / "heldout_information_budgets.png"
    metric_pdf = output / "heldout_information_budgets.pdf"
    confusion_png = output / "heldout_confusion_matrices.png"
    confusion_pdf = output / "heldout_confusion_matrices.pdf"
    base.save_metric_figure(report, metric_png)
    base.save_metric_figure(report, metric_pdf)
    base.save_confusion_figure(report, confusion_png)
    base.save_confusion_figure(report, confusion_pdf)

    fact_sheet = {
        "schema_version": "0.14.0",
        "status": base.EXPECTED_STATUS,
        "physical_checkpoint": args.physical_checkpoint,
        "corpus_scenarios": report["scenarios"],
        "heldout_scenarios": 2000,
        "first_generation_jobs": report["first_generation_jobs"],
        "heldout_only_model_request_scope": True,
        "bootstrap_replicates": report["bootstrap_replicates"],
        "heldout": {
            method: report["results"][method]["heldout"] for method in base.METHODS
        },
        "comparisons": report["heldout_primary_comparisons"],
        "heldout_baselines": report["heldout_baselines"],
        "heldout_family_diagnostics": report["heldout_family_diagnostics"],
        "claim_boundary": (
            "Machine-stage predictions and statistics only. Any practitioner "
            "validation is documented separately and is not inferred here."
        ),
    }
    facts_path = output / "MACHINE_RESULT_FACT_SHEET_V014.json"
    facts_path.write_text(
        json.dumps(fact_sheet, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    generated = [
        main_path,
        comparison_path,
        metric_png,
        metric_pdf,
        confusion_png,
        confusion_pdf,
        facts_path,
    ]
    manifest = {
        "schema_version": "0.14.0",
        "status": "PASS_V014_PAPER_ASSETS_FROM_HELDOUT_MACHINE_STAGE_REPORT",
        "physical_checkpoint": args.physical_checkpoint,
        "input": {
            "path": str(args.evaluation_report.as_posix()),
            "sha256": sha256(args.evaluation_report),
        },
        "outputs": [
            {"path": path.name, "bytes": path.stat().st_size, "sha256": sha256(path)}
            for path in generated
        ],
    }
    manifest_path = output / "ASSET_MANIFEST_V014.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(
        json.dumps(
            {
                "status": manifest["status"],
                "outputs": len(generated),
                "manifest_sha256": sha256(manifest_path),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
