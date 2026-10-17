import json
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
import f99_real_archive as f99

def synthetic_fixture(spec):
    wing=spec["lane"]=="Wingless"
    rows=[]
    seeds=range(51100,51124) if wing else range(51400,51448)
    families=range(4,8) if wing else range(40,44)
    for seed in seeds:
        for dimension in families:
            truth=[False,True] if wing else [True,False]
            coded=spec["coded_control"]
            learned=spec["learned_model"]
            models={
                "always_yes_shortcut":[True,True],
                coded:list(truth),
            }
            if wing:
                models.update({
                    learned:([False,False] if len(rows)<72 else [True,True]),
                    "old_F5_depth_blind":[True,True],
                })
                row=dict(seed=seed,path_depth=dimension,requested_depths=[dimension-1,dimension],
                         query=[17,19],edges=[[i,i+1] for i in range(12)],truth=truth,
                         models=models,frozen_probability=0.5)
            else:
                models.update({
                    learned:[True,True],
                    "untyped_coded_reachability":[True,True],
                })
                row=dict(seed=seed,family=dimension,question=[17,19],
                         edges=[[i,i+1] for i in range(12)],truth=truth,
                         predictions=models,requested_role_sequence=[0,1,2,3],
                         roles_positive=[0]*12,roles_swapped=[1]+[0]*11)
            rows.append(row)
    scores={}
    for key in rows[0]["models" if wing else "predictions"]:
        preds=[r["models" if wing else "predictions"][key] for r in rows]
        paired=sum(p==r["truth"] for p,r in zip(preds,rows))
        correct=sum(a==b for p,r in zip(preds,rows) for a,b in zip(p,r["truth"]))
        val=dict(accuracy=correct/(2*len(rows)),
                 paired_accuracy=paired/len(rows),paired_correct=paired)
        if wing:
            val.update(negative_correct=sum(not p[0] for p in preds),
                       positive_correct=sum(p[1] for p in preds))
        else:
            val.update(correct=correct,negative_false_positives=sum(p[1] for p in preds))
        scores[key]=val
    base=dict(schema=spec["payload_schema"],registered_verdict=spec["verdict"],
              stage="DEVELOPMENT_ONLY",model_retrained=False,
              source_birth_independent=False,sealed_first_use=False,
              external_llm_calls=0,rows=rows,scores=scores)
    if wing:
        base.update(query_depth_is_present_in_frozen_model_interface=False,
                    explicit_depth_is_only_control_input=True,accepted_ref_mutation=False,
                    graph_states=96,paired_questions=192,seeds=[51100,51124])
    else:
        base.update(candidate_state_contains_role_codes=False,
                    role_swaps_change_only_relation_types=True,
                    same_untyped_edges_and_query_per_counterfactual=True,
                    scientific_accepted=False,graph_pairs=192,question_count=384,
                    seeds=[51400,51448],families=[40,41,42,43])
    return base

class F99(unittest.TestCase):
    def test_authentic_pin_manifest_deny_science(self):
        f=f99.frozen()
        self.assertEqual([r["lane"] for r in f["cohorts"]],["Wingless","Yggdrasil"])
        self.assertFalse(f["assumptions"]["genenv_training_activated"])
        for spec in f["cohorts"]:
            self.assertEqual(len(spec["zip_sha256"]),64)
            self.assertEqual(len(spec["payload_sha256"]),64)
            self.assertTrue(spec["training_only"])
            self.assertEqual(spec["observed_train_only_vector"],
                             [spec["pair_count"],spec["pair_count"],spec["pair_count"]])
    def test_synthetic_fixture_exercises_full_reaggregation_not_real_science(self):
        for s in f99.frozen()["cohorts"]:
            r=f99.semantic(s,synthetic_fixture(s))
            self.assertTrue(r["historical_development_negative_only"])
            self.assertEqual(r["independently_reaggregated_learned_correct_pairs"],0)
            self.assertEqual(r["independently_reaggregated_coded_control_pairs"],s["pair_count"])
            self.assertFalse(r["genenv_training_activated"])
    def test_mutated_rows_controls_and_outcomes_quarantined(self):
        for s in f99.frozen()["cohorts"]:
            for change in ("row_deleted","replayed_seed","wrong_truth","false_positive",
                           "missing_control","inflated_score","pretend_accepted","changed_dev_stage"):
                data=synthetic_fixture(s)
                models=data["rows"][0]["models" if s["lane"]=="Wingless" else "predictions"]
                if change=="row_deleted":data["rows"].pop()
                elif change=="replayed_seed":data["rows"][1]["seed"]=data["rows"][0]["seed"];data["rows"][1]["path_depth" if s["lane"]=="Wingless" else "family"]=data["rows"][0]["path_depth" if s["lane"]=="Wingless" else "family"]
                elif change=="wrong_truth":data["rows"][0]["truth"]=[True,True]
                elif change=="false_positive":models[s["coded_control"]]=[True,True]
                elif change=="missing_control":del models[s["coded_control"]]
                elif change=="inflated_score":data["scores"][s["learned_model"]]["paired_correct"]=1
                elif change=="pretend_accepted":data["source_birth_independent"]=True
                elif change=="changed_dev_stage":data["stage"]="SEALED_PROSPECTIVE"
                with self.subTest(lane=s["lane"],change=change):
                    with self.assertRaises(f99.Quarantined):f99.semantic(s,data)
    def test_graph_structure_counterfactual_and_role_tampering(self):
        for s in f99.frozen()["cohorts"]:
            data=synthetic_fixture(s)
            data["rows"][0]["edges"]=[]
            with self.assertRaises(f99.Quarantined):f99.semantic(s,data)
            if s["lane"]=="Yggdrasil":
                data=synthetic_fixture(s)
                data["rows"][0]["roles_swapped"][1]=1
                with self.assertRaises(f99.Quarantined):f99.semantic(s,data)
            else:
                data=synthetic_fixture(s)
                data["rows"][0]["requested_depths"]=[0,1]
                with self.assertRaises(f99.Quarantined):f99.semantic(s,data)
    def test_json_duplicate_keys_nonfinite_and_incorrect_artifact(self):
        for raw in (b'{"x":1,"x":2}',b'{"x":NaN}',b'{"x":Infinity}',b'not-json'):
            with self.assertRaises(f99.Quarantined):f99.read_json(raw)
        with tempfile.TemporaryDirectory() as root:
            path=pathlib.Path(root)/"fake.zip"
            path.write_bytes(b"not-original-zip")
            for s in f99.frozen()["cohorts"]:
                with self.assertRaises(f99.Quarantined):f99.audit_archive(s,path)
    def test_frozen_policy_mutation_never_yields_training_permission(self):
        original=f99.frozen()
        original["assumptions"]["genenv_training_activated"]=True
        with tempfile.TemporaryDirectory() as root:
            p=pathlib.Path(root)/"bad.json"
            p.write_text(json.dumps(original),encoding="utf-8")
            with patch.object(f99,"FROZEN",p):
                with self.assertRaises(f99.Quarantined):f99.frozen()
if __name__=="__main__":
    unittest.main()
