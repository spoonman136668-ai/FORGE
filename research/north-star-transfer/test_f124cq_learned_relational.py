"""F124-CQ source-free nonlinear delayed role-binding learning acceptance.

Engineering fixtures are explicitly NOT fresh scientific source families;
they never call F124-CO consumed sources or private oracles.
"""
from __future__ import annotations
import copy
import importlib.util
from pathlib import Path
import random
import unittest

HERE=Path(__file__).resolve().parent
def module(path,name):
    spec=importlib.util.spec_from_file_location(name,HERE/path)
    value=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value
candidate=module("f124cq_learned_relational_tree.py","f124cq_learned")
control=module("f124cq_trained_tree_control.py","f124cq_control")

def rule(event,current,lag):
    # Public deterministic source-free engineering sanity check, NOT research.
    return 15 if (event & 1) and (lag & 1) else 0

def fixture():
    rng=random.Random(0xC024)
    xs=rng.sample(range(4096),48)
    rows=[]
    for x in xs:
        event=x&15
        current=(x>>4)&15
        lag=(x>>8)&15
        rows.append([event,current,lag,rule(event,current,lag)])
    return rows[:40],rows[40:]

def public_graphs():
    states={"a":[3,1],"b":[5,0]}
    initial=copy.deepcopy(states)
    events=[]
    for step in range(10):
        role=("a","b")[step%2]
        event=(1,3,0,5,2,1,7,1,4,1)[step]
        curr,lag=states[role]
        nxt=rule(event,curr,lag)
        events.append({"role":role,"event":event,"observed":nxt})
        states[role]=[nxt,curr]
    pos={"initial":initial,"events":events}
    neg=copy.deepcopy(pos)
    pair=next(((i,j) for i in range(len(events))
               for j in range(i+1,len(events))
               if events[i]["role"]!=events[j]["role"]
               and events[i]["observed"]!=events[j]["observed"]),None)
    assert pair is not None
    i,j=pair
    neg["events"][i]["observed"],neg["events"][j]["observed"]=(
        neg["events"][j]["observed"],neg["events"][i]["observed"])
    return pos,neg

class NewLearnedRelationalMechanism(unittest.TestCase):
    def test_both_independently_fit_delayed_nonlinear_interaction(self):
        fit,check=fixture()
        model,receipt=candidate.train(fit,check)
        self.assertIsNotNone(model,receipt)
        self.assertEqual(receipt["FIT_bit_errors"],0)
        self.assertEqual(receipt["CHECK_bit_errors"],0)
        self.assertTrue(any(i>=12 for i in receipt["trained_predicate_ids"]))
        self.assertLessEqual(receipt["learned_tree_nodes"],60)
        self.assertFalse(receipt["scientific_accepted"])
        competitor,peer=control.fit(fit,check)
        self.assertIsNotNone(competitor,peer)
        self.assertEqual(peer["FIT_bit_errors"],0)
        self.assertEqual(peer["CHECK_bit_errors"],0)
        self.assertLessEqual(peer["learned_nodes"],60)
        self.assertFalse(peer["scientific_accepted"])
        self.assertTrue(peer["public_information_equal"])
        for event,current,lag,target in check:
            self.assertEqual(candidate.predict(model,event,candidate.OnlineState(current,lag)).current,target)
            self.assertEqual(control.next_state(competitor,event,control.State(current,lag)).current,target)

    def test_role_keyed_state_survives_interleaving_and_rejects_hard_negative(self):
        fit,check=fixture()
        pos,neg=public_graphs()
        for maker,predict in ((candidate.train,candidate.rollout),(control.fit,control.rollout)):
            model,receipt=maker(fit,check)
            self.assertIsNotNone(model,receipt)
            yes=predict(model,pos)
            no=predict(model,neg)
            self.assertEqual(yes["transitions_evaluated"],10)
            self.assertEqual(no["transitions_evaluated"],10)
            self.assertEqual(yes["role_count"],2)
            self.assertTrue(yes["full_trajectory_accepted"])
            self.assertFalse(no["full_trajectory_accepted"])
            self.assertTrue(no["all_events_evaluated"])

    def test_check_is_veto_only_for_both_trained_models(self):
        fit,check=fixture()
        bad=copy.deepcopy(check)
        bad[0][3]^=1
        for learner in (candidate.train,control.fit):
            good,good_receipt=learner(fit,check)
            rejected,receipt=learner(fit,bad)
            self.assertIsNotNone(good,good_receipt)
            self.assertIsNone(rejected)
            self.assertEqual(receipt["FIT_bit_errors"],good_receipt["FIT_bit_errors"])
            self.assertEqual(receipt["CHECK_bit_errors"],1)

    def test_invalid_input_and_unbounded_roles_fail_closed(self):
        fit,check=fixture()
        for learner in (candidate.train,control.fit):
            with self.assertRaises(ValueError):learner(fit[:39],check)
            corrupted=copy.deepcopy(fit);corrupted[0][0]=True
            with self.assertRaises(ValueError):learner(corrupted,check)
        model,_=candidate.train(fit,check)
        pos,_=public_graphs()
        pos["initial"]={str(j):[0,0] for j in range(17)}
        with self.assertRaises(ValueError):candidate.rollout(model,pos)

    def test_prior_original_case_modules_and_source_are_never_imported(self):
        import ast
        for path in ("f124cq_learned_relational_tree.py",
                     "f124cq_trained_tree_control.py"):
            tree=ast.parse((HERE/path).read_text())
            imports=[]
            for node in ast.walk(tree):
                if isinstance(node,ast.Import):
                    imports.extend(a.name for a in node.names)
                elif isinstance(node,ast.ImportFrom):
                    imports.append(node.module or "")
            self.assertFalse(any("f124co" in name or "f124cn" in name or
                                 "f124cm" in name for name in imports))
            self.assertNotIn("932000",(HERE/path).read_text())
            self.assertNotIn("933000",(HERE/path).read_text())

if __name__=="__main__":
    unittest.main()
