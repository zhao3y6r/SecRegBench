import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "audit_synthetic_privacy_v014.py"
SPEC = importlib.util.spec_from_file_location("audit_synthetic_privacy_v014", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class SyntheticPrivacyAuditPublicTest(unittest.TestCase):
    def test_detects_mainland_mobile_number(self):
        pattern = MODULE.PATTERNS["mainland_mobile_number"]
        self.assertIsNotNone(pattern.search("contact 13800138000 for this test"))

    def test_generic_dialogue_has_no_identifier_match(self):
        text = "Please explain the general product risk without personal data."
        matched = [name for name, pattern in MODULE.PATTERNS.items() if pattern.search(text)]
        self.assertEqual(matched, [])


if __name__ == "__main__":
    unittest.main()
