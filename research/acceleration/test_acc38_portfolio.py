"""ACC38 preserves the original 36 acceleration proposals; no native model admission."""
from __future__ import annotations
import ast
import importlib.util
import pathlib
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[2]
PROTO=ROOT/"docs/research/ACC-38-U02-GO-SCALAR-SPECULATION-PREREG.md"
GO=ROOT/"research/acceleration/acc38_go_spec/main.go"
TEST=ROOT/"research/acceleration/acc38_go_spec/main_test.go"
LEDGER=ROOT/"research/acceleration/acc34_scoreboard.py"

class ACC38PortfolioContract(unittest.TestCase):
    def test_all_36_original_registered_unchanged(self):
        spec=importlib.util.spec_from_file_location("acc38_original_acc34",LEDGER)
        mod=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        r=mod.scoreboard(run_full_screening=False)
        self.assertEqual(r["total_registered_candidates"],36)
        self.assertEqual({v["claim_id"] for v in r["rows"]},
              {f"U{i:02d}" for i in range(1,31)}|
              {f"AC-D{i}" for i in range(1,7)})
        self.assertEqual(r["hardware_substitutes_not_physical_results"],["U03","U06"])
        self.assertEqual(r["stage2_qualified_native_model_speedups"],0)
        self.assertFalse(r["scientific_first_use"])
        self.assertFalse(r["scientific_admission"])

    def test_original_ac08_source_identity_and_order(self):
        text=(ROOT/"research/ac07_sourcefree/ac08_portfolio.py").read_text()
        self.assertIn('NATIVE_PILOT_ORDER=(',text)
        self.assertIn('"AC-D1"',text)
        self.assertIn('"AC-D5"',text)
        self.assertIn('"AC-D3"',text)
        ast.parse(text)

    def test_frozen_u02_scalar_source_and_no_synthetic_source_substitutes(self):
        s=GO.read_text()
        p=PROTO.read_text()
        self.assertIn("Original U02",p)
        self.assertIn("128 charged exact-target FIT calls",p)
        self.assertIn("192-round",p)
        self.assertIn('return (7*s+3)&31',s)
        self.assertIn('return (5*s+1)&31',s)
        self.assertIn("targetStep(state,shift,&r)",s)
        self.assertIn("r.VerificationCalls++",s)
        self.assertIn("child_user_system_cpu_ns",s)
        self.assertIn("GO_SYS",s.upper())
        self.assertNotIn("env.unwrapped",s)
        self.assertNotIn("original_external_source",s)
        self.assertTrue(TEST.read_text().count("func Test")>=8)

    def test_precise_negative_and_no_promotion_labels(self):
        s=GO.read_text()
        self.assertIn("ACC38_U02_NO_VERIFIED_SCALAR_CPU_GAIN",s)
        self.assertIn("ACC38_PROTOCOL_OR_METER_BLOCKED",s)
        self.assertIn("ACC38_U02_SCALAR_VERIFIED_GO_CPU_WIN_ENGINEERING_ONLY",s)
        self.assertIn("NativeModelImprovementProven:false",s)
        self.assertIn("UnsafeWrongTrials",s)
        self.assertIn("VerifiedMismatches",s)

if __name__=="__main__":unittest.main()
