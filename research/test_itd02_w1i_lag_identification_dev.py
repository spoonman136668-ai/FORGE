"""W1I source-free structural preflight. Never execute 940xx scored worlds."""
import ast
import inspect
import json
import math
import random
import unittest

import itd02_w1i_lag_identification_dev as w


def obs(t):
    return [math.sin(w.OMEGA*t+.1),math.cos(w.OMEGA*t+.1)]


class W1IFocused(unittest.TestCase):
    def test_frozen_protocol_cohorts_thresholds(self):
        self.assertEqual(w.PROTOCOL_COMMIT,"39cd0c72daf1d1853c83ea7791eb2c913630c665")
        self.assertEqual(w.SEEDS,(94011,94017,94021,94033))
        self.assertEqual(len(w.FAMILIES),4)
        self.assertEqual(len(w.ARMS),7)
        self.assertEqual(w.FROZEN_STEPS,17920)
        self.assertEqual(w.SCORED_STEPS,160)
        self.assertEqual(w.FIT_STEPS,96)
        self.assertEqual(w.SURPRISE_THRESHOLD,.70)
        self.assertEqual(w.SURPRISE_HAZARD,.40)

    def test_source_real_selected_action_causal_effect_and_latency(self):
        # First action under lag0 immediately affects the observed outcome.
        x=w.World("lag-cycle",93001,False)
        y=w.World("lag-cycle",93001,False)
        base=x.step(0)[1]
        probe=y.step(1)[1]
        self.assertAlmostEqual(probe-base,w.sign(math.sin(x.offset))-w.PROBE_COST)
        # Under lag2, today's action affects future outcomes, not this step
        a=w.World("lag-stationary",93001,False)
        b=w.World("lag-stationary",93001,False)
        reward_a=a.step(0)[1]
        reward_b=b.step(1)[1]
        self.assertAlmostEqual(reward_b-reward_a,-w.PROBE_COST,places=12)
        self.assertNotEqual(a.momentum,b.momentum)
        # Distinct physical action sequences then create distinct delayed outcomes.
        a.step(0);b.step(0)
        ra=a.step(0)[1];rb=b.step(0)[1]
        self.assertNotAlmostEqual(ra,rb)

    def test_periodic_action_trace_fails_identifiability(self):
        world=w.World("lag-cycle",93001,True)
        rows=[]
        for t in range(w.FIT_STEPS):
            old,reward,_,_=world.step(t%2)
            rows.append((old,t%2,reward))
        with self.assertRaisesRegex(ValueError,"LAGS_NOT_IDENTIFIABLE"):
            w.check_fit_actions(rows)
        self.assertEqual(all(rows[t][1]==rows[t-2][1]
                             for t in range(2,len(rows))),True)

    def test_independent_pulses_restore_identifiability(self):
        for family in w.FAMILIES:
            rows,diag=w.collect_fit(family,93001)
            self.assertEqual(len(rows),96)
            self.assertGreaterEqual(diag["separated_lag0_lag2"],24)
            self.assertGreater(diag["lag_design_determinant"],1.)
            self.assertEqual((rows,diag),w.collect_fit(family,93001))

    def test_bayesian_experience_and_actions_only(self):
        models=[w.LagBelief(name) for name in
                ("pulse-causal","bayes-active","bayes-greedy")]
        rows,_=w.collect_fit("lag-return",93003)
        for model in models:
            start=model.state()
            for observation,action,reward in rows:
                model.update(observation,action,reward)
            self.assertEqual(model.completed,96)
            self.assertNotEqual(model.state(),start)
            self.assertAlmostEqual(sum(model.posterior),1.,places=12)
            self.assertIn(model.choose(obs(15)),(0,1))
        self.assertEqual(models[0].kind,"pulse-causal")
        self.assertEqual(models[1].kind,"bayes-active")

    def test_adaptive_hazard_is_distinct_from_frozen_bayes(self):
        active=w.LagBelief("pulse-causal")
        conventional=w.LagBelief("bayes-active")
        for model in (active,conventional):
            model.posterior=[.99,.005,.005]
            model.history=[0,0]
        active.streak=2  # preexisting audited contradiction streak
        active.update(obs(0),0,0.)
        conventional.update(obs(0),0,0.)
        self.assertLess(active.posterior[0],conventional.posterior[0])
        self.assertAlmostEqual(sum(active.posterior),1.)
        self.assertAlmostEqual(sum(conventional.posterior),1.)

    def test_mid_episode_cold_restores_actual_lag_memory(self):
        before=w.LagBelief("pulse-causal")
        rows,_=w.collect_fit("lag-cycle",93001)
        for observation,action,reward in rows:
            before.update(observation,action,reward)
        before.reset_episode_history()
        for t in range(20):
            before.update(obs(t),t%2,.5 if t%2 else -.5)
        raw,digest=before.checkpoint()
        after=w.LagBelief.restore(raw,digest,minimum_completed=116)
        self.assertEqual(after.state(),before.state())
        for t in range(20,35):
            for model in (before,after):
                model.update(obs(t),t%2,.5 if t%2 else -.5)
        self.assertEqual(after.checkpoint(),before.checkpoint())
        self.assertEqual(after.choose(obs(36)),before.choose(obs(36)))

    def test_tamper_and_rollback_denied(self):
        agent=w.LagBelief("pulse-causal")
        agent.update(obs(0),1,1.)
        raw,correct=agent.checkpoint()
        for payload,sha,floor in ((raw+b" ",correct,1),
                                  (raw,"0"*64,1),(raw,correct,2)):
            with self.assertRaises(ValueError):
                w.LagBelief.restore(payload,sha,floor)
        content=json.loads(raw)
        content["model"]["posterior"]=[2.,0.,0.]
        broken=w.canonical(content)
        with self.assertRaises(ValueError):
            w.LagBelief.restore(broken,w.digest_bytes(broken),1)

    def test_models_receive_identical_fit_but_independent_state(self):
        fit,_=w.collect_fit("lag-distractor",93003)
        digests=[]
        for name in w.ARMS:
            model=w.policy(name,93003)
            for observation,action,reward in fit:
                model.update(observation,action,reward)
            model.reset_episode_history()
            choice=model.choose(obs(50))
            self.assertIn(choice,(0,1))
            digests.append(w.sha(model.state()))
        self.assertEqual(len(digests),len(w.ARMS))
        self.assertEqual(len(set(digests)),len(w.ARMS))

    def test_inert_no_physics_import_and_no_scored_world_called(self):
        source=inspect.getsource(w)
        imports=set()
        for node in ast.walk(ast.parse(source)):
            if isinstance(node,ast.Import):
                imports.update(x.name for x in node.names)
            if isinstance(node,ast.ImportFrom):
                imports.add(node.module)
        self.assertFalse(imports & {"gymnasium","subprocess","socket","requests",
                                    "cloudflare","websocket"})
        self.assertFalse(any(seed in (93001,93003) for seed in w.SEEDS))
        self.assertNotIn("scientific_accepted=True",source)
        self.assertNotIn("original_first_use=True",source)


if __name__=="__main__":
    unittest.main()
