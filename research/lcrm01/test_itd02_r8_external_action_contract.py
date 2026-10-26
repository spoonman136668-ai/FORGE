"""Tests for external-action admission. Native source remains unchanged."""
import unittest
from itd02_r8_external_action_contract import require_external_action_custody

class ExternalActionTest(unittest.TestCase):
    def test_valid_action_still_requires_native_custody(self):
        for action in (0,1,2):
            with self.subTest(action=action):
                with self.assertRaisesRegex(RuntimeError,"NOT_IMPLEMENTED"):
                    require_external_action_custody(object(),action,{"X":1})
    def test_invalid_action_rejected_first(self):
        for action in (True,-1,3,1.0):
            with self.subTest(action=action):
                with self.assertRaises(ValueError):
                    require_external_action_custody(object(),action,{"X":1})
    def test_missing_source_rejected(self):
        with self.assertRaises(ValueError):
            require_external_action_custody(None,0,{"X":1})

if __name__=="__main__":unittest.main()
