import importlib.util
import hashlib
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "score_provisional_evaluation_v012.py"
SPEC = importlib.util.spec_from_file_location("score_provisional_evaluation_v012", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class ScoringPublicTest(unittest.TestCase):
    def test_keyword_binding_accepts_verified_public_projection(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            corpus = Path(temp_dir) / "corpus.jsonl"
            corpus.write_text('{"scenario_id":"S1"}\n', encoding="utf-8")
            digest = hashlib.sha256(corpus.read_bytes()).hexdigest()
            report = {
                "hashes": {
                    "corpus": "0" * 64,
                    "public_corpus_projection": digest,
                }
            }
            MODULE.validate_keyword_corpus_binding(report, corpus)

    def test_keyword_binding_rejects_unknown_projection(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            corpus = Path(temp_dir) / "corpus.jsonl"
            corpus.write_text('{"scenario_id":"S1"}\n', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "not bound to corpus"):
                MODULE.validate_keyword_corpus_binding(
                    {"hashes": {"corpus": "0" * 64}}, corpus
                )

    def test_first_generation_is_selected(self):
        events = [
            {"job_id": "J1", "run_generation": 2},
            {"job_id": "J1", "run_generation": 1},
            {"job_id": "J2", "run_generation": 1},
        ]
        selected = MODULE.first_generation(events)
        self.assertEqual(set(selected), {"J1", "J2"})
        self.assertEqual(selected["J1"]["run_generation"], 1)

    def test_perfect_confusion_scores_one(self):
        confusion = MODULE.empty_confusion()
        for action in MODULE.ACTIONS:
            confusion[action][action] = 1
        metrics = MODULE.metrics_from_confusion(confusion)
        self.assertEqual(metrics["n"], 4)
        self.assertEqual(metrics["accuracy"], 1.0)
        self.assertEqual(metrics["macro_f1"], 1.0)
        self.assertEqual(metrics["invalid_rate"], 0.0)


if __name__ == "__main__":
    unittest.main()
