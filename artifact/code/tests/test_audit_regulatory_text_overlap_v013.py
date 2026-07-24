import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "audit_regulatory_text_overlap_v013.py"
SPEC = importlib.util.spec_from_file_location("audit_regulatory_text_overlap_v013", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class RegulatoryTextOverlapAuditTest(unittest.TestCase):
    def test_compact_removes_punctuation_and_normalizes_width(self):
        self.assertEqual(MODULE.compact("Ａ， B。证券"), "ab证券")

    def test_ngrams(self):
        self.assertEqual(MODULE.ngrams("abcd", 3), {"abc", "bcd"})
        self.assertEqual(MODULE.ngrams("ab", 3), set())


if __name__ == "__main__":
    unittest.main()
