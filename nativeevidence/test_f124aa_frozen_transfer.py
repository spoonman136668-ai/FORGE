"""F124-AA exact frozen identity, changed source families, and 7+9/packed guards."""
import unittest
from collections import Counter
import math

import f124aa_frozen_source as s
import f124aa_packed_transfer as m
import f124z_sparse_continuity as z
import f124q_independent_binding as q


class FrozenAA(unittest.TestCase):
    def test_frozen_parent_and_authority(self):
        p=s.frozen()
        self.assertEqual(s.witness.blob(s.FREEZE),s.FREEZE_BLOB)
        self.assertEqual(p["lineage"]["parent_run"],39087469247)
        self.assertTrue(all(v is False for v in p["authority"].values()))
        self.assertEqual(p["Wingless"]["constraints"]["max_states_per_node"],1)

    def test_all_four_families_admitted_on_fresh_fit_only(self):
        for lane in ("Wingless","Yggdrasil"):
            self.assertTrue(set(s.COHORTS[lane]["FIT"]).isdisjoint(
                            s.COHORTS[lane]["DEV"]))
            cases=s.pairs(lane,"FIT")
            self.assertEqual(len(cases),48)
            families=Counter(x[2] for x in cases)
            self.assertEqual(families,Counter({f:12 for f in s.FAMILIES}))
            for family in s.FAMILIES:
                depths=Counter(len(p["roles"]) for _,_,f,p,n in cases
                               if f==family)
                nominal=(10,11,12) if family=="extended_depth" else (7,8,9)
                self.assertEqual(depths,Counter({d:4 for d in nominal}))
            for _,_,family,p,n in cases:
                s.validate_extended(p)
                s.validate_extended(n)
                self.assertEqual(s.routes(p,relaxed=family=="one_bit_relaxed_keys"),1)
                self.assertEqual(s.routes(n,relaxed=family=="one_bit_relaxed_keys"),0)
                self.assertEqual(set(p),{"start","target","roles","edges"})
            with self.assertRaises(s.q.Quarantined):
                s.build(lane,1280000,(2,1,1),"FIT")

    def test_original_T_and_continuity_parity_within_old_depths(self):
        base=[.4,.9,.65,.75,.8,.2,-.5]
        delta=[1.3,.2]
        for _,_,family,p,n in s.pairs("Yggdrasil","FIT")[:8]:
            if family=="extended_depth":
                continue  # historical original Q explicitly rejects >9 hops
            for graph in (p,n):
                new_orig,wo=m.ygg_original(graph,base,delta)
                orig,work=q.forward("Yggdrasil",graph,base,delta)
                self.assertEqual(new_orig,orig)
                self.assertEqual(wo,work)
                corrected,ratio,raw,wl=m.ygg_continuity(graph,base,delta)
                expected,r,existing=z.continuity_head(graph,base,delta)
                self.assertEqual(raw,expected)
                self.assertEqual(ratio,r)
                self.assertEqual(wl,existing)
                self.assertEqual(corrected,z.corrected_logit(raw,ratio,.5))

    def test_cross_12_hop_support_without_mutating_original_validator(self):
        _,_,f,graph,_=next(row for row in s.pairs("Yggdrasil","FIT")
                            if row[2]=="extended_depth")
        self.assertEqual(f,"extended_depth")
        with self.assertRaises(s.q.Quarantined):
            s.q.validate_public(graph)
        base=[.4,.9,.65,.75,.8,.2,-.5]
        delta=[1.3,.2]
        raw,work=m.ygg_original(graph,base,delta)
        corrected,ratio,original,extra=m.ygg_continuity(graph,base,delta)
        self.assertEqual(raw,original)
        self.assertTrue(math.isfinite(corrected))
        self.assertLessEqual(extra["max_active"],7)
        self.assertLessEqual(extra["max_retained"],9)

    def test_one_packed_slot_and_public_only_prediction(self):
        base=[.6,.7,.9,.5,.85,.15,-.55]
        delta=[.05,-.03,.02,-.04]
        for _,_,_,p,n in s.pairs("Wingless","FIT")[:8]:
            for g in (p,n):
                score,c=m.packed_one_state(g,base,delta)
                self.assertTrue(math.isfinite(score))
                self.assertLessEqual(c["max_active"],64)
                self.assertEqual(c["max_packed_bits_per_state"],12)
                self.assertEqual(c["max_encoded_cache"],0)
                self.assertEqual(c["max_lookahead_cache"],0)


if __name__=="__main__":
    unittest.main()
