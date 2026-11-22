"""F40 algorithm and custody DEV smoke only: fake physics is never scientific evidence."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np

SOURCE = Path(__file__).with_name('f40_original_cartpole_learning_dev.py')
spec = importlib.util.spec_from_file_location('f40_original_cartpole_learning_dev', SOURCE)
f40 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(f40)


class ActionSpace:
    n = 2


class PublicFakeCartpole:
    action_space = ActionSpace()

    def __init__(self):
        self.t = 0
        self.closed = False

    def reset(self, seed):
        self.t = 0
        self.s = [float((seed % 13)-6)/100, 0., float((seed % 7)-3)/200, 0.]
        return list(self.s), {'ignored': 'not a training oracle'}

    def step(self, action):
        if self.t >= 7:
            raise ValueError('STEPPED_AFTER_TERMINATION')
        self.t += 1
        v = 1 if action else -1
        x, xv, theta, tv = self.s
        self.s = [x + .02*xv, .98*xv+.01*v, theta+.02*tv, .96*tv+.012*v]
        return list(self.s), 1.0, self.t == 7, False, {'ignored': 42}

    def close(self):
        self.closed = True


class FakeGym:
    def make(self, identifier, render_mode):
        if identifier != 'CartPole-v1' or render_mode is not None:
            raise AssertionError('F40_CHANGED_ORIGINAL_INTERFACE')
        return PublicFakeCartpole()


class F40MechanismTests(unittest.TestCase):
    def test_training_shared_samples_and_frozen_coverage(self):
        train, counts = f40.training(FakeGym())
        self.assertEqual(128*7, len(train))
        self.assertEqual(len(train), sum(counts))
        self.assertTrue(all(counts))
        self.assertEqual(128*7, len([x for x in train if x['reward']==1]))
        model = f40.fit_models(train)
        self.assertEqual((6,4), np.asarray(model['causal-linear-mpc']).shape)
        self.assertEqual((2,11), np.asarray(model['trained-fitted-q']).shape)
        self.assertEqual(5, len(model['trained-linear-imitation']))
        self.assertNotEqual(model['causal-linear-mpc'],model['wrong-action'])
        self.assertNotEqual(model['causal-linear-mpc'],model['no-learned-dynamics'])
        self.assertEqual(f40.canonical(model),f40.canonical(json.loads(f40.canonical(model))))

    def test_frozen_fake_mechanics_not_science(self):
        gym = FakeGym()
        train, _ = f40.training(gym)
        model = f40.fit_models(train)
        report = f40.assess(gym, model, f40.digest(train), f40.ORIGINAL)
        self.assertTrue(report['development_only'])
        self.assertFalse(report['scientific_accepted'])
        self.assertFalse(report['first_use_consumed'])
        self.assertFalse(report['owner_eligible'])
        self.assertEqual(8, len(report['arms']['causal-linear-mpc']['worlds']))
        self.assertEqual(set(f40.KINDS),set(report['arms']))
        self.assertIn(report['selected_conventional'], ['behavior-rule','trained-linear-imitation','trained-fitted-q'])
        self.assertTrue(all(w['cold_matches'] for arm in report['arms'].values() for w in arm['worlds']))
        self.assertEqual(report['report_sha256'],f40.digest({k:v for k,v in report.items() if k!='report_sha256'}))
        for k, arm in report['arms'].items():
            self.assertEqual(7, arm['mean_return'])
            for w in arm['worlds']:
                self.assertIn(w['seed'],f40.EVAL_SEEDS)
                self.assertEqual(64, len(w['actions_sha256']))
                self.assertEqual(7, w['steps'])
        self.assertEqual('F40_ORIGINAL_RUNTIME_UNVERIFIED', report['classification'])
        self.assertFalse(report['frozen_thresholds_met'])

    def test_fake_source_string_cannot_label_original_science(self):
        train, _ = f40.training(FakeGym())
        model = f40.fit_models(train)
        report = f40.assess(FakeGym(), model, f40.digest(train), f40.ORIGINAL)
        self.assertEqual('F40_ORIGINAL_RUNTIME_UNVERIFIED', report['classification'])
        self.assertNotIn(report['classification'],
                         ('F40_DEV_NO_GO', 'F40_DEV_SIGNAL_UNVERIFIED'))
        self.assertIs(type(report['frozen_thresholds_met']), bool)
        self.assertEqual(report['report_sha256'],
                         f40.digest({k: v for k, v in report.items()
                                     if k != 'report_sha256'}))

    def test_first_use_and_terminal_guards(self):
        for seed in f40.FIRST_USE_FORBIDDEN:
            with self.assertRaisesRegex(ValueError, 'FIRST_USE'):
                f40.episode(FakeGym(),seed,'behavior-rule',cap=3)
        got = f40.episode(FakeGym(),701,'behavior-rule',cap=500)
        self.assertEqual(7,len(got['transitions']))
        self.assertTrue(got['transitions'][-1]['terminated'])
        with self.assertRaisesRegex(ValueError,'BAD_PUBLIC'):
            f40.public_obs([1,2,3,float('nan')])
        with self.assertRaisesRegex(ValueError,'BAD_PUBLIC'):
            f40.public_obs([1,2,3])

    def test_negative_action_and_input_rejection(self):
        obs=[0.,0.,0.,0.]
        model=f40.fit_models([{'s':obs,'a':a,'next':[.01*a,.02,-.01,.1*a],
                               'reward':1.,'done':False} for a in [0,1,0,1,1,0]])
        for kind in f40.KINDS:
            self.assertIn(f40.choose(obs,kind,model),(0,1))
        with self.assertRaisesRegex(ValueError,'BAD_TRAINING_ACTION'):
            f40.linear_design([obs],[2])
        with self.assertRaisesRegex(ValueError,'BAD_TRAINING_LABELS'):
            f40.fit_models([{'s':obs,'a':2,'next':obs,'reward':1,'done':False}])
        with self.assertRaisesRegex(ValueError,'NO_REAL_TRAINING'):
            f40.fit_models([])
        with self.assertRaisesRegex(ValueError,'BAD_DYNAMICS_SHAPE'):
            f40.mpc_action(obs, [[0]])

    def test_no_alternate_original_source_claims(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises((ValueError,RuntimeError,ModuleNotFoundError)):
                f40.original_gym(Path(root))
            with self.assertRaises(ValueError):
                f40.main([root, str(Path(root)/'report.json')])
        # No scientific result was computed against the uninstalled original package.
        self.assertNotIn('gymnasium', sys.modules)


if __name__ == '__main__':
    unittest.main(verbosity=2)
