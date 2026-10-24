"""K4O offline scientific source-custody and nearest-neighbor falsification."""
import json
import unittest
from k4o_mechanism_audit import FROZEN,model_pools,diagnostic,SCHEMA
from k4m_mechanism_audit import selected,choice

def fit_rows():
    rows=[]
    for fam in ("reaching","pushing"):
        for v in range(12):
            for a in range(4):
                rows.append({"family":fam,"variant":v,"arm":a,
                    "features":[float(v)/12]+[0.0]*127,
                    "reward":float((a+v)%5)})
    return rows

def original_like():
    return {"FIT_rows":fit_rows(),"FIT_only_selection_audit":{
         fam:{"selected_FIT_variants_by_arm":{str(a):[0,3,6,9] for a in range(4)}}
         for fam in ("reaching","pushing")}}

class K4OMechanismTests(unittest.TestCase):
    def test_frozen_pins_and_hindsight_only(self):
        p=json.loads(FROZEN.read_text())
        self.assertFalse(p["governance"]["scientific_first_use"])
        self.assertFalse(p["governance"]["scientific_accepted"])
        self.assertTrue(p["governance"]["no_physics_rerun"])
        self.assertEqual(p["diagnostics"]["case_ids"],[17,19])
        self.assertEqual(len(p["original_source"]["members_sha256"]),3)

    def test_pools_have_four_original_records_only(self):
        original=original_like()
        pools=model_pools(original,"reaching")
        for arm in range(4):
            self.assertEqual(len(pools[arm]["full_12"]),12)
            for m in ("coverage_4","uniform_4","outcome_aware_4","fit_fidelity_4"):
                self.assertEqual(len(pools[arm][m]),4)
                self.assertTrue(all(r in original["FIT_rows"] for r in pools[arm][m]))

    def test_reproduction_cannot_accept_missing_FIT(self):
        p=original_like();p["FIT_rows"]=[r for r in p["FIT_rows"]
            if not (r["family"]=="reaching" and r["arm"]==3 and r["variant"]==8)]
        with self.assertRaises(ValueError):model_pools(p,"reaching")

    def test_duplicate_capacity_not_permitted(self):
        p=original_like()
        p["FIT_only_selection_audit"]["reaching"]["selected_FIT_variants_by_arm"]["3"]=[0,3,3,9]
        with self.assertRaises(ValueError):model_pools(p,"reaching")

    def test_nearest_policy_reacts_to_record_removal_but_hindsight_is_not_claim(self):
        x=[0.0]*128
        records=lambda v,reward:[{"variant":v,"features":x,"reward":float(reward)}]
        arms={0:records(0,0),1:records(0,10),2:records(0,-1),
              3:records(1,50)+[{"variant":2,"features":[1.0]+[0.0]*127,"reward":2.0}]}
        self.assertEqual(choice(arms,x)["selected_arm"],3)
        arms[3]=[r for r in arms[3] if r["variant"]!=1]
        self.assertEqual(choice(arms,x)["selected_arm"],1)

    def test_original_selector_is_deterministic(self):
        rows=[{"variant":i,"features":[i/12.0]+[0.0]*127,"reward":float(i%3)}
              for i in range(12)]
        for method in ("full_12","coverage_4","outcome_aware_4","uniform_4"):
            self.assertEqual(selected(rows,method),selected(rows,method))

if __name__=="__main__":
    unittest.main()
