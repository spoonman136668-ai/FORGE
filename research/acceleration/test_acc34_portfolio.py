"""ACC-34 acceleration portfolio integrity and scientific no-go assertions."""
import json
import pathlib
import re
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[2]
INDEX=ROOT/"research/acceleration/acc34_portfolio_index.json"
SOURCE=ROOT/"research/ac07_sourcefree/ac08_portfolio.py"
DOC=ROOT/"docs/research/ACC-34-REALIGN-36-AND-ACD1-GO-PREREG.md"
class Acc34Portfolio(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=json.loads(INDEX.read_text(encoding="utf-8"))
        cls.source=SOURCE.read_text(encoding="utf-8")
        cls.prereg=DOC.read_text(encoding="utf-8")
    def test_all_original_thirty_and_six_distinct_additions(self):
        rows=self.data["rows"]; ids=[x["claim_id"] for x in rows]
        self.assertEqual(len(rows),36)
        self.assertEqual(len(set(ids)),36)
        self.assertEqual(set(ids),{"U%02d"%i for i in range(1,31)}|{"AC-D%d"%i for i in range(1,7)})
        self.assertEqual(self.data["original_claims"],30)
        self.assertEqual(self.data["additional_hypotheses"],6)
    def test_actual_early_source_registry_is_unchanged(self):
        s=self.source
        for key,expected in (("ORIGINAL_NAMES",30),("NATIVE_NAMES",6)):
            found=re.search(r"(?m)^"+key+r"=\(([\s\S]*?)\)\n",s)
            self.assertIsNotNone(found)
            titles=re.findall(r'"([^"]+)"',found.group(1))
            self.assertEqual(len(titles),expected)
            candidates=[r["title"] for r in self.data["rows"] if
                r["origin"]==("original_uploaded_portfolio" if key=="ORIGINAL_NAMES" else "six_additional_hypotheses")]
            if key=="ORIGINAL_NAMES":
                candidates=[r["title"] for r in self.data["rows"] if r["claim_id"].startswith("U")]
            self.assertEqual(candidates,titles)
        self.assertIn("U07 U08 U10 U18 U19 U20 U21 U22 U23 U24 U26 U27 U28 U29 U30",s)
    def test_original_physical_substitute_are_not_magic_hardware(self):
        rows={x["claim_id"]:x for x in self.data["rows"]}
        for x in ("U03","U06"):
            self.assertEqual(rows[x]["source_boundary"],"DIGITAL_ONLY_SUBSTITUTE_NOT_PHYSICAL_TEST")
        for x in rows.values():
            self.assertFalse(x["native_model_acceleration_proven"])
            self.assertFalse(x["scientifically_admitted"])
    def test_only_one_staged_go_pilot_not_model_science(self):
        rows={x["claim_id"]:x for x in self.data["rows"]}
        self.assertEqual(rows["AC-D1"]["stage2_status"],"STAGE2_GO_CPU_KERNEL_UNQUALIFIED")
        self.assertTrue(all(x["stage2_status"] in ("NOT_COMPLETE","STAGE1_ONLY") for k,x in rows.items() if k!="AC-D1"))
        self.assertFalse(self.data["scientific_first_use"])
        self.assertFalse(self.data["scientific_admission"])
        self.assertFalse(self.data["protected_main_or_controller_modified"])
    def test_preregistered_hidden_falsifier_and_total_cpu(self):
        for s in ("91101, 91103, 91107, 91109, 91111",
                  "HIDDEN_INTERACTION","UNVERIFIED","VERIFIED",
                  "0.90","1.10","32-node","24 public input bits"):
            self.assertIn(s,self.prereg)
if __name__=="__main__":unittest.main()
