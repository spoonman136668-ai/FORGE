"""Enforce honesty boundary between qualified primitives and scientific fidelity."""
import json
from pathlib import Path
import unittest
from fidelity_audit import audit, METHOD_REQUIREMENTS

ROOT=Path(__file__).resolve().parent
class MethodFidelityAudit(unittest.TestCase):
    def test_all_eight_implementations_fail_scientific_admission(self):
        frozen=json.loads((ROOT/"frozen_portfolio.json").read_text())
        result=audit(frozen)
        self.assertEqual(result["status"],"BLOCKED_UNQUALIFIED_METHOD_FIDELITY")
        self.assertEqual(len(result["candidates"]),8)
        self.assertEqual({r["id"] for r in result["candidates"]},set(METHOD_REQUIREMENTS))
        self.assertTrue(all(r["status"]=="UNQUALIFIED_METHOD_FIDELITY" for r in result["candidates"]))
        self.assertFalse(result["scientific_candidate_selection_authorized"])
        self.assertFalse(result["sealed_original_authorized"])
        self.assertEqual(result["first_use_claims_consumed"],0)
    def test_changed_portfolio_schema_fails(self):
        frozen=json.loads((ROOT/"frozen_portfolio.json").read_text())
        frozen["schema"]="unknown"
        with self.assertRaisesRegex(ValueError,"WRONG_FROZEN_SCHEMA"):
            audit(frozen)
    def test_missing_candidate_fails(self):
        frozen=json.loads((ROOT/"frozen_portfolio.json").read_text())
        frozen["wingless"]["candidates"].pop()
        with self.assertRaisesRegex(ValueError,"CANDIDATE_IDENTITY_DRIFT"):
            audit(frozen)

if __name__=="__main__":
    unittest.main()
