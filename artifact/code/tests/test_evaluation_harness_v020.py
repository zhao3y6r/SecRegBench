import importlib.util
import json
import unittest
from pathlib import Path


ARTIFACT = Path(__file__).resolve().parents[2]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


COMPILER = load_module(
    "compile_evaluation_requests_v020",
    ARTIFACT / "code/scripts/compile_evaluation_requests_v020.py",
)
RUNNER = load_module(
    "run_openai_compatible_evaluation_v020",
    ARTIFACT / "code/scripts/run_openai_compatible_evaluation_v020.py",
)


class EvaluationHarnessV020Tests(unittest.TestCase):
    def test_exact_prompt_and_evidence_are_present(self):
        prompt = (
            ARTIFACT / "evaluation/system_prompt_zh_v020.txt"
        ).read_text(encoding="utf-8")
        self.assertTrue(prompt.startswith("你是证券客户服务流程的合规动作分类器"))
        self.assertIn('{"action":"ANSWER|CLARIFY|REFUSE|ESCALATE"}', prompt)
        evidence = [
            json.loads(line)
            for line in (
                ARTIFACT / "evaluation/evidence_inputs_v020.jsonl"
            ).read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        self.assertEqual(len(evidence), 48)
        self.assertEqual(len({row["clause_id"] for row in evidence}), 48)

    def test_view_construction_is_label_free(self):
        with (ARTIFACT / "data/secregbench_public_v014.jsonl").open(
            encoding="utf-8"
        ) as stream:
            corpus_row = json.loads(stream.readline())
        view = COMPILER.evaluation_view(corpus_row, "state_only", [])
        serialized = COMPILER.canonical_json(view)
        self.assertIn("typed_state", view)
        self.assertNotIn("label", view)
        self.assertNotIn(corpus_row["label"]["primary_action"], serialized)

    def test_runner_parser_accepts_only_one_action_field(self):
        self.assertEqual(
            RUNNER.parse_action('{"action":"CLARIFY"}'), ("CLARIFY", [])
        )
        action, errors = RUNNER.parse_action('{"action":"ANSWER","why":"x"}')
        self.assertEqual(action, "ANSWER")
        self.assertIn("keys_must_equal_action", errors)
        self.assertIsNone(RUNNER.parse_action("not json")[0])


if __name__ == "__main__":
    unittest.main()
