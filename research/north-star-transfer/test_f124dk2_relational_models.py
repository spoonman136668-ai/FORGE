"""Focused, source-only F124-DK-2 test; no reserved cohort is generated."""
from __future__ import annotations
import ast
import copy
import random
import unittest
from pathlib import Path

import torch
import f124dk2_relational_models as m


def analytic_fit():
    # Explicit deterministic source-only toy. Not hidden causal family or new
    # scientific case; reserved seeds 901..904 are never accessed.
    rng = random.Random(1642)
    out = []
    for _ in range(24):
        state = {r:[rng.randrange(16),rng.randrange(16)] for r in m.ROLES}
        initial=copy.deepcopy(state)
        events=[]
        for _ in range(8):
            target, source = rng.sample(m.ROLES, 2)
            event = rng.randrange(16)
            y = state[target][0] ^ state[source][0]
            events.append({"target":target,"source":source,"event":event,"observed":y})
            state[target] = [y,state[target][0]]
        out.append({"initial":initial,"events":events})
    return out


class LearningInterfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fit = analytic_fit()

    def test_stated_fit_contract(self):
        self.assertEqual(len(self.fit), 24)
        a,b=m.fit_rows(self.fit)
        self.assertEqual(tuple(a.shape),(192,20))
        self.assertEqual(tuple(b.shape),(192,4))

    def test_trainable_parameter_parity(self):
        for arm in ('candidate','peer'):
            model=m.new_model(arm)
            self.assertEqual(sum(p.numel() for p in model.parameters()),180)

    def test_no_generator_or_hidden_law_import(self):
        p=Path(m.__file__)
        imports=[]
        for node in ast.walk(ast.parse(p.read_text())):
            if isinstance(node,ast.Import):
                imports += [n.name for n in node.names]
            if isinstance(node,ast.ImportFrom):
                imports.append(node.module or '')
        self.assertFalse(any('sourcefree_development' in a or 'source_law' in a for a in imports))

    def test_reject_non_fit_training(self):
        with self.assertRaises(ValueError): m.fit_rows(self.fit[:8])

    def test_fit_local_cv_is_train_only(self):
        for arm in ('candidate','peer'):
            result=m.fit_only_diagnostics(arm,self.fit)
            self.assertEqual(result['receipt']['updates'],240)
            self.assertEqual(result['receipt']['training_rows'],192)
            self.assertEqual(result['cv_receipt']['training_rows'],160)
            self.assertFalse(result['used_CHECK_or_HELDOUT'])
            self.assertEqual(result['receipt']['FIT_sha256'],m.digest(self.fit))

    def test_candidate_learns_distinct_compositional_parameters(self):
        initial=m.new_model('candidate')
        fitted,_=m.fit_model('candidate',self.fit)
        self.assertFalse(torch.equal(initial.a,fitted.a))
        self.assertFalse(torch.equal(initial.b,fitted.b))

    def test_compositional_ablation_uses_same_parameter_shape(self):
        model,_=m.fit_model('candidate',self.fit)
        x=torch.tensor([m.encode((1,2,3,4,5)),m.encode((5,4,3,2,1))])
        self.assertEqual(model(x).shape,model(x,ablate=True).shape)
        self.assertFalse(torch.equal(model(x),model(x,ablate=True)))

    def test_no_teacher_forcing_in_rollout(self):
        for arm in ('candidate','peer'):
            model,_=m.fit_model(arm,self.fit)
            ep=self.fit[-1]
            malicious=copy.deepcopy(ep)
            for event in malicious['events']:
                event['observed'] ^= 15
            self.assertEqual(m.rollout(model,ep),m.rollout(model,malicious))

    def test_deterministic_training(self):
        a,_=m.fit_model('candidate',self.fit)
        b,_=m.fit_model('candidate',self.fit)
        for pa,pb in zip(a.parameters(),b.parameters()):
            self.assertTrue(torch.equal(pa,pb))

    def test_reject_invalid_public_values(self):
        with self.assertRaises(ValueError):m.encode((1,2,3,4,16))
        with self.assertRaises(ValueError):m.encode((1,2,3,True,5))


if __name__ == '__main__': unittest.main()
