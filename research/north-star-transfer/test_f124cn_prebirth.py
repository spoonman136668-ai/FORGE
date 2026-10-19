"""F124-CN prebirth engineering tests: no new scientific source packet born."""
import ast
import copy
import importlib.util
import json
from pathlib import Path
import random
import unittest

HERE=Path(__file__).resolve().parent
def mod(path,name):
    spec=importlib.util.spec_from_file_location(name,HERE/path)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    return m
evaluator=mod("f124cn_blind_trajectory_eval.py","F124CN_source_blind_eval")
learner=mod("f124cm_learned_online_state.py","F124CN_engineering_fixture_model")

def engineering_fixture():
    # Separate ID -1; never use or invoke source code or a frozen science ID.
    rng=random.Random(0x7654310)
    frozen=learner.LearnedModel((0x1047,0x4143,0x8200b,0x100201))
    rows=[];used=set()
    while len(rows)<48:
        event,current,lagged=(rng.randrange(16) for _ in range(3))
        if (event,current,lagged) in used:continue
        used.add((event,current,lagged))
        out=learner.predict(frozen,event,learner.OnlineState(current,lagged))
        rows.append([event,current,lagged,out.current])
    current={"A":[1,3],"B":[5,7]}
    initial=copy.deepcopy(current)
    events=[]
    for i in range(8):
        role=("A","B")[i%2]
        event=rng.randrange(16)
        s=learner.OnlineState(*current[role])
        out=learner.predict(frozen,event,s)
        events.append({"role":role,"event":event,"observed":out.current})
        current[role]=[out.current,out.lagged]
    positive={"initial":initial,"events":events}
    negative=copy.deepcopy(positive)
    distinct=next((i,j) for i in range(8) for j in range(i+1,8)
                  if events[i]["role"]!=events[j]["role"]
                  and events[i]["observed"]!=events[j]["observed"])
    a,b=distinct
    negative["events"][a]["observed"],negative["events"][b]["observed"]=(
        negative["events"][b]["observed"],negative["events"][a]["observed"])
    return {"case_id":-1,"FIT":rows[:40],"CHECK":rows[40:],
            "positive":positive,"hard_negative":negative}

class PrebirthEngineering(unittest.TestCase):
    def test_source_module_has_no_model_dependency_and_no_born_cases(self):
        path=HERE/"f124cn_new_trajectory_source.py"
        tree=ast.parse(path.read_text())
        imports=[]
        for node in ast.walk(tree):
            if isinstance(node,ast.Import):imports += [a.name for a in node.names]
            if isinstance(node,ast.ImportFrom):imports += [node.module or ""]
        self.assertFalse(any("f124cm" in x or "nativeevidence" in x or "f124cn_blind" in x for x in imports))
        self.assertIn("932000",path.read_text())
        self.assertIn("933000",path.read_text())
    def test_model_learning_and_trajectory_scoring_synthetic_only(self):
        task=engineering_fixture()
        r=evaluator.evaluate(task,"CANDIDATE",synthetic=True)
        self.assertTrue(r["natural_admission"],r["training"])
        self.assertEqual(r["native_graph_score_calls"],2)
        self.assertEqual(r["native_event_transition_calls"],16)
        self.assertTrue(r["correct_pair"],r)
        self.assertFalse(r["hard_false_positive"])
        self.assertFalse(r["science_accepted"])
    def test_trained_peer_is_naturally_observed_not_forced(self):
        task=engineering_fixture()
        c=evaluator.evaluate(task,"CANDIDATE",synthetic=True)
        peer=evaluator.evaluate(task,"TRAINED_CONTROL",synthetic=True)
        self.assertEqual(c["public_task_sha256"],peer["public_task_sha256"])
        self.assertEqual(c["graph_sha256"],peer["graph_sha256"])
        self.assertEqual(peer["expected_event_transition_calls_if_admitted"],16)
        self.assertIn(peer["native_event_transition_calls"],(0,16))
        self.assertEqual(peer["native_graph_score_calls"],2 if peer["natural_admission"] else 0)
    def test_matched_graph_tamper_and_secret_metadata_rejected(self):
        t=engineering_fixture();t["private_seed"]="never_to_child"
        with self.assertRaises(ValueError):evaluator.evaluate(t,"CANDIDATE",synthetic=True)
        t=engineering_fixture()
        t["hard_negative"]["events"][0]["event"]^=1
        with self.assertRaises(ValueError):evaluator.evaluate(t,"TRAINED_CONTROL",synthetic=True)
    def test_no_synthetic_as_authentic_firstuse(self):
        with self.assertRaises(ValueError):
            evaluator.evaluate(engineering_fixture(),"CANDIDATE")
    def test_out_of_family_FIT_is_a_natural_abstention_not_a_rerun(self):
        t=engineering_fixture()
        # Public FIT labels with a contradiction in the frozen learner's
        # 25-dimensional class; no source generator or original science.
        for i,row in enumerate(t["FIT"]):
            row[3]=(row[3]+i%7)&15
        observed=evaluator.evaluate(t,"CANDIDATE",synthetic=True)
        self.assertFalse(observed["natural_admission"])
        self.assertEqual(observed["native_graph_score_calls"],0)
        self.assertEqual(observed["native_event_transition_calls"],0)
        self.assertFalse(observed["science_accepted"])
        self.assertTrue(observed["training"]["natural_FIT_inconsistent_abstention"])
    def test_no_earlier_born_case_identity(self):
        t=engineering_fixture();t["case_id"]=930000
        with self.assertRaises(ValueError):evaluator.evaluate(t,"CANDIDATE")
    def test_always_full_positive_and_negative_native_pass(self):
        t=engineering_fixture()
        baseline=evaluator.evaluate(t,"PERSISTENCE_REFERENCE",synthetic=True)
        self.assertEqual(baseline["native_graph_score_calls"],2)
        self.assertEqual(baseline["native_event_transition_calls"],16)

if __name__=="__main__":unittest.main()
