"""F124-CT engineering-only sequence training tests; NO new science source birth.

These deterministic fixtures exercise delayed role-specific information and
interleaved source-pointer retrieval, not any consumed 924-935 source or
private oracle. A training success is not unfamiliar-source transfer.
"""
from __future__ import annotations
import ast
import random
import unittest
import numpy as np

import f124ct_sequence_protocol as p
import f124ct_attentive_causal_memory as candidate
import f124ct_gated_sequence_control as peer

def toy_episodes():
    rng=random.Random(149200)
    cases=[]
    for index in range(p.FIT_EPISODES+p.CHECK_EPISODES):
        initial={name:[rng.choice((0,15)),rng.choice((0,15))]
                 for name in p.ROLES}
        state={name:list(pair) for name,pair in initial.items()}
        events=[]
        # A genuine *causal sequential* target/source-copy law, where each
        # output changes a role's future memory; no isolated FIT rows exist.
        for step in range(p.STEPS_PER_EPISODE):
            target=p.ROLES[(step+index)%3]
            source=p.ROLES[(step+index+1+(index%2))%3]
            event=(step+2*index)%16
            observed=state[source][0]
            events.append({"target":target,"source":source,
                           "event":event,"observed":observed})
            prior=state[target][0]
            state[target]=[observed,prior]
        cases.append({"initial":initial,"events":events})
    return cases[:p.FIT_EPISODES],cases[p.FIT_EPISODES:]

class LearnedCausalSequence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fit,cls.check=toy_episodes()
        cls.candidate,cls.candidate_receipt=candidate.train(cls.fit,cls.check)
        cls.control,cls.control_receipt=peer.train(cls.fit,cls.check)
    def test_both_are_actually_trained_on_full_sequences(self):
        for model,receipt in ((self.candidate,self.candidate_receipt),
                              (self.control,self.control_receipt)):
            self.assertIsNotNone(model,receipt)
            self.assertTrue(receipt["full_sequential_BPTT"])
            self.assertEqual(receipt["FIT_count"],24)
            self.assertEqual(receipt["CHECK_veto_only_count"],8)
            self.assertEqual(receipt["training_epochs"],p.EPOCHS)
            self.assertFalse(receipt["CHECK_used_to_update_weights"])
            self.assertGreaterEqual(receipt["FIT_relative_loss_reduction"],
                                    p.MIN_FIT_LOSS_REDUCTION)
            self.assertFalse(receipt["scientific_accepted"])
    def test_learned_associative_source_retrieval_receives_gradients(self):
        raw=candidate.new()
        grads,_=candidate.gradients(raw,self.fit[0])
        for key in ("K","Wq","Wctx","Wself","Einit","Wy"):
            self.assertGreater(float(np.linalg.norm(grads[key])),1e-12,key)
            self.assertGreater(float(np.linalg.norm(self.candidate[key]-raw[key])),
                               1e-6,key)
    def test_control_learns_separate_recurrent_roles_and_gates(self):
        raw=peer.new()
        grads,_=peer.gradients(raw,self.fit[0])
        for key in ("Gh","Gs","Wh","Ws","Einit","Wy"):
            self.assertGreater(float(np.linalg.norm(grads[key])),1e-12,key)
            self.assertGreater(float(np.linalg.norm(self.control[key]-raw[key])),
                               1e-6,key)
    def test_both_predict_without_reusing_observed_as_memory_input(self):
        # Mutating public observed targets cannot change the predictions,
        # only their scored loss. This catches hidden teacher-forcing leaks.
        ep=self.check[0]
        changed={"initial":ep["initial"],"events":[dict(x) for x in ep["events"]]}
        for event in changed["events"]:
            event["observed"]^=15
        for model,module in ((self.candidate,candidate),(self.control,peer)):
            original=module.predict_sequence(model,ep)
            changed_result=module.predict_sequence(model,changed)
            self.assertEqual(original,changed_result)
            self.assertEqual(len(original),p.STEPS_PER_EPISODE)
    def test_frozen_training_is_deterministic_and_independent(self):
        for mod,trained in ((candidate,self.candidate_receipt),
                            (peer,self.control_receipt)):
            model,receipt=mod.train(self.fit,self.check)
            self.assertEqual(receipt["FIT_episode_sha256"],
                             trained["FIT_episode_sha256"])
            self.assertAlmostEqual(receipt["final_FIT_bit_cross_entropy"],
                                   trained["final_FIT_bit_cross_entropy"],places=11)
            self.assertIsNotNone(model,receipt)
    def test_reject_stateless_rows_and_unbounded_source_oracle(self):
        with self.assertRaises(ValueError):p.validate([[]]*24,24)
        bad=list(self.fit);bad[0]={"initial":bad[0]["initial"],
                   "events":[dict(x) for x in bad[0]["events"]]}
        bad[0]["events"][0]["private_oracle"]=1
        with self.assertRaises(ValueError):candidate.train(bad,self.check)
    def test_old_source_and_competing_model_import_absent(self):
        for mod in (candidate,peer):
            file=mod.__file__
            tree=ast.parse(open(file,encoding="utf8").read())
            imported=[]
            for node in ast.walk(tree):
                if isinstance(node,ast.Import):
                    imported.extend(x.name for x in node.names)
                elif isinstance(node,ast.ImportFrom):
                    imported.append(node.module or "")
            self.assertFalse(any("f124c" in x and not x.startswith("f124ct_sequence_protocol")
                                 for x in imported))
        self.assertEqual(p.ROLES,("alpha","beta","gamma"))
        self.assertEqual(p.HIDDEN,8)

if __name__=="__main__":
    unittest.main()
