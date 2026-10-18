"""F124-AC original inference trace parity, causal reference separation and strata."""
import unittest,inspect,math
from collections import Counter
import f124ac_frozen_source as src
import f124ac_passive_trace as obs
import f124ac_development_evidence as evidence
import f124ab_soft_hamming_pareto as original_ab
import f124aa_packed_transfer as original_aa


class F124ACTests(unittest.TestCase):
    def test_preregistration_source_birth(self):
        p=src.frozen()
        self.assertEqual(src.guard.blob(src.FREEZE),src.FREEZE_BLOB)
        self.assertEqual(p["lineage"]["parent_run"],39090219587)
        self.assertEqual(p["Yggdrasil"]["held_constant"]["gamma"],.25)
        self.assertTrue(all(v is False for v in p["authority"].values()))
        for lane in ("Yggdrasil","Wingless"):
            self.assertTrue(set(src.COHORTS[lane]["FIT"]).isdisjoint(
                            src.COHORTS[lane]["DEV"]))
            self.assertTrue(set(src.COHORTS[lane]["FIT"]).isdisjoint(
                            src.original.COHORTS[lane]["FIT"]))
            cases=src.pairs(lane,"FIT")
            self.assertEqual(len(cases),48)
            self.assertEqual(Counter(x[2] for x in cases),
                             Counter({name:12 for name in src.FAMILIES}))

    def test_ygg_trace_identical_every_original_cost_and_logit(self):
        base=[.4,.9,.65,.75,.8,.2,-.5]
        delta=[1.3,.2]
        for _,_,family,pos,neg in src.pairs("Yggdrasil","FIT")[:9]:
            for graph in (pos,neg):
                result,raw,ratio,work,trace=obs.observe_ygg(graph,base,delta)
                original_raw,orig_ratio,orig_work=original_ab.soft_continuity(
                    graph,base,delta,.25)
                frozen_raw,baseline_work=original_aa.ygg_original(
                    graph,base,delta)
                self.assertEqual(raw,original_raw)
                self.assertEqual(raw,frozen_raw)
                self.assertEqual(ratio,orig_ratio)
                self.assertEqual(result,original_ab.logit(raw,ratio,.25))
                self.assertTrue(all(work[k]==orig_work[k] for k in orig_work))
                self.assertTrue(all(work[k]==baseline_work[k] for k in baseline_work))
                self.assertEqual(len(trace),len(graph["roles"]))
                self.assertTrue(all(len(t["active"])<=7 and
                                    len(t["retained"])<=9 for t in trace))
            reference=evidence.public_reference(
                pos,relaxed=family=="one_bit_relaxed_keys")
            joined=evidence.causal_join(trace,reference)
            self.assertEqual(len(joined["by_hop"]),len(pos["roles"]))

    def test_wing_one_slot_exact_and_public_alias_audit(self):
        base=[.6,.7,.9,.5,.85,.15,-.55]
        delta=[.05,-.03,.02,-.04]
        for _,_,family,pos,neg in src.pairs("Wingless","FIT")[:9]:
            for graph in (pos,neg):
                score,work,trace=obs.observe_wing(graph,base,delta)
                unchanged,orig_work=original_aa.packed_one_state(
                    graph,base,delta)
                self.assertEqual(score,unchanged)
                self.assertEqual(work,orig_work)
                self.assertLessEqual(work["max_active"],64)
                self.assertEqual(len(trace),len(graph["roles"]))
                aliases=evidence.collision_census(graph)
                self.assertGreaterEqual(
                    aliases["all_public_packed_alias_sets"],0)
            joined=evidence.causal_join(
                trace,evidence.public_reference(
                    pos,relaxed=family=="one_bit_relaxed_keys"),wing=True)
            self.assertEqual(len(joined["by_hop"]),len(pos["roles"]))

    def test_inference_never_reads_oracle_or_label(self):
        for fn in (obs.observe_ygg,obs.observe_wing):
            raw=inspect.getsource(fn)
            for banned in ("public_reference(","routes(","paired_admit(",
                           "candidate_label","protected(","case_success"):
                self.assertNotIn(banned,raw)
        self.assertEqual(len(obs.pack_public([0]*16)),4)

if __name__=="__main__":
    unittest.main()
