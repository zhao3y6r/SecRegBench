from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


class ExpertAdjudicationPublicTest(unittest.TestCase):
    def test_public_overlay_verifier(self) -> None:
        artifact = Path(__file__).resolve().parents[2]
        process = subprocess.run(
            [
                sys.executable,
                str(artifact / "code/verify_expert_adjudication_v021.py"),
            ],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        self.assertEqual(process.returncode, 0, process.stderr or process.stdout)
        report = json.loads(process.stdout)
        self.assertEqual(
            report["status"], "PASS_DEIDENTIFIED_EXPERT_ADJUDICATION_V021"
        )
        self.assertEqual(report["high_confidence_items"], 91)
        self.assertEqual(report["revised_labels"], 10)
        self.assertEqual(report["unresolved_items"], 9)
        self.assertFalse(report["identity_fields_distributed"])


if __name__ == "__main__":
    unittest.main()
