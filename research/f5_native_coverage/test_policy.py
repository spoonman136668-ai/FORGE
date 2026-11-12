"""F5 causal-sensor, bounded-memory and no-oracle qualification."""
import unittest
import inspect
from policy import PROBES,POLICIES,BASELINE,choose,calibration,audit_trace
from worker import decode,evaluate_historical,install_public_policy
from types import SimpleNamespace

def public_history(shock=False):
    def coordinate(cell,t):
        value=(3+5*cell+t)%16
        if shock and t==5 and cell==8:
            return (3+5*10+t)%16
        return value
    readings={}
    for time in PROBES:
        pair=choose("F5-COVERAGE",time,readings)
        readings[time]={c:coordinate(c,time) for c in pair}
    return readings

class PolicyTests(unittest.TestCase):
    def test_five_episode_ten_read_budget_and_baseline(self):
        for policy in POLICIES:
            h={}
            for time in PROBES:
                pair=choose(policy,time,h)
                self.assertEqual(len(pair),2)
                self.assertEqual(len(set(pair)),2)
                h[time]={cell:(3+5*cell+time)%16 for cell in pair}
            audited=audit_trace(policy,h)
            self.assertEqual(audited["public_read_budget"],10)
            self.assertLessEqual(len(audited["remembered_addresses"]),4)
            self.assertEqual(sum(len(x) for x in h.values()),10)
        self.assertEqual(tuple(choose("F5-FIXED",t,{tt: {0:(3+tt)%16,1:(8+tt)%16}
                  for tt in PROBES if tt<t}) for t in (0,1,3)),BASELINE[:3])
    def test_fresh_coverage_has_four_distinct_late_sensor_addresses(self):
        h=public_history()
        self.assertEqual(audit_trace("F5-COVERAGE",h)["late_unique_addresses"],4)
        self.assertEqual(set(h[5]).intersection(set(h[7])),set())
        self.assertTrue(set(h[5]).isdisjoint({0,1}))
    def test_memory_policy_only_uses_prior_public_uncertainty(self):
        # At episode 7, two observed residuals induce remeasurement
        # rather than choosing two unseen probes.
        h={}
        for t in PROBES:
            pair=choose("F5-MEMORY",t,h)
            h[t]={c:(3+5*c+t)%16 for c in pair}
        self.assertEqual(set(h[5]).intersection(set(h[7])),set())
        shocked={k:dict(v) for k,v in h.items() if k<7}
        changed=next(iter(shocked[5]))
        shocked[5][changed]=(shocked[5][changed]+1)%16
        self.assertEqual(set(choose("F5-MEMORY",7,shocked)),set(shocked[5]))
        self.assertNotEqual(set(choose("F5-COVERAGE",7,shocked)),set(shocked[5]))
    def test_future_and_hidden_values_rejected(self):
        h=public_history()
        with self.assertRaisesRegex(ValueError,"FUTURE_OR_CURRENT"):
            choose("F5-COVERAGE",5,h)
        with self.assertRaisesRegex(TypeError,"unexpected keyword"):
            choose("F5-COVERAGE",5,{k:v for k,v in h.items() if k<5},true_pair=(8,10))
        self.assertEqual(list(inspect.signature(choose).parameters),["policy","episode","history"])
    def test_tampered_trace_cannot_pass_causal_replay(self):
        h=public_history()
        poisoned={k:dict(v) for k,v in h.items()}
        pairs=list(poisoned[7])
        poisoned[7]={5:poisoned[7][pairs[0]],pairs[1]:poisoned[7][pairs[1]]}
        with self.assertRaisesRegex(ValueError,"CAUSAL_ADDRESS_TRACE"):
            audit_trace("F5-COVERAGE",poisoned)
    def test_public_decoder_positive_and_negative(self):
        def coordinate(c,t):return (3+5*c+t)%16
        seen={t:{str(c):coordinate(c,t) for c in pair}
              for t,pair in zip(PROBES,BASELINE)}
        self.assertIsNone(decode(seen,7)["first_detection_episode"])
        seen[5]["2"]=coordinate(4,5)
        self.assertEqual(decode(seen,7)["first_detection_episode"],5)
    def test_exception_restores_actual_pinned_hook(self):
        old=lambda *args:{}
        old_decoder=lambda *args:None
        mod=SimpleNamespace(
            y64=SimpleNamespace(dual_public_samples=old,
                y46=SimpleNamespace(coordinate=lambda c,s,t,f,r:(3+5*c+t)%16)),
            y61=SimpleNamespace(y60=SimpleNamespace(public_decoder=old_decoder)))
        source=SimpleNamespace(m=mod)
        witness=[]
        with self.assertRaisesRegex(RuntimeError,"interruption"):
            with install_public_policy(source,"F5-COVERAGE",witness):
                out=mod.y64.dual_public_samples(67204,(3,1,9))
                self.assertEqual(sum(map(len,out.values())),10)
                raise RuntimeError("interruption")
        self.assertIs(mod.y64.dual_public_samples,old)
        self.assertIs(mod.y61.y60.public_decoder,old_decoder)
        self.assertEqual(len(witness),1)
    def test_new_unverified_seed_fails_before_source(self):
        with self.assertRaisesRegex(ValueError,"UNAUTHORIZED_NEW_SEED"):
            evaluate_historical(None,67600,(8,10),1,(3,1,9),"full","F5-COVERAGE")
        with self.assertRaisesRegex(ValueError,"UNAUTHORIZED_NEW_SEED"):
            evaluate_historical(None,67640,(8,10),1,(3,1,9),"full","F5-MEMORY")
        with self.assertRaisesRegex(ValueError,"UNAUTHORIZED_PAIR"):
            evaluate_historical(None,67204,(6,9),1,(3,1,9),"full","F5-MEMORY")

if __name__=="__main__":
    unittest.main()
