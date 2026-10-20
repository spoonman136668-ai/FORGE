"""F124-DD engineering qualification: exact learned-gate compilation & cost.

All meta training, new causal structural cases and independently learned
strong peers are source-free. The original scientific first-use pause and
entire previous source family exclusion must remain intact.
"""
from __future__ import annotations
import ast
import copy
from pathlib import Path
import sys
import unittest
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import f124dd_sourceonly_new_structures as source
import f124dd_meta_compact_nand as nand
import f124dd_independent_compact_anf as peer
import f124dd_compact_trial as trial

class CompactCausalCompiler(unittest.TestCase):
    def test_frozen_new_source_only_families_and_fresh_seeds(self):
        self.assertEqual(source.SEEDS,(81,82,83,84))
        self.assertEqual(len(source.FAMILIES),4)
        self.assertEqual(len(source.meta_training()),12)
        self.assertEqual(len(source.meta_training()[0]),24)
        for family in source.FAMILIES:
            for seed in source.SEEDS:
                d=source.heldout(family,seed)
                self.assertEqual(set(d),{"FIT","CHECK","HELDOUT"})
                self.assertEqual(tuple(len(d[k]) for k in ("FIT","CHECK","HELDOUT")),
                                 (24,8,8))
                self.assertEqual(d,source.heldout(family,seed))
                for ep in d["HELDOUT"]:
                    negative=source.hard_negative(ep)
                    self.assertNotEqual(ep,negative)
                    self.assertEqual(sorted(e["observed"] for e in ep["events"]),
                                     sorted(e["observed"] for e in negative["events"]))
    def test_both_strong_meta_train_from_equally_informed_public_episodes(self):
        tasks=source.meta_training()
        m,a=nand.train_meta(tasks)
        peer_m,b=peer.train_meta(tasks)
        self.assertIsNotNone(m,a)
        self.assertIsNotNone(peer_m,b)
        self.assertEqual(m["learned_gate"],7)
        self.assertEqual(peer_m["xor_gate"],6)
        self.assertEqual(peer_m["and_gate"],8)
        self.assertEqual(a["meta_training_event_rows"],2304)
        self.assertEqual(b["meta_fit_event_rows"],2304)
    def test_bit_parallel_NAND_compiler_is_exact_and_learned_gate_dependent(self):
        for n in (2,3,4):
            # Qualify every possible Boolean program for arity 2, and a
            # deterministic broad selection for arity 3 and 4, including
            # full negation/compositions. Test all input assignments.
            mask=(1<<(1<<n))-1
            truths=range(16) if n==2 else [
                0,mask,0x6996&mask,0x9669&mask,0xfeca&mask,0x155a&mask,
                0x1234&mask,0x8421&mask,0xefff&mask]
            for truth in truths:
                nodes,root=nand.graph(n,truth)
                self.assertEqual(nand.compiled_truth(nodes,root,n,7),truth)
                for pattern in range(1<<n):
                    vals=tuple((pattern>>i)&1 for i in range(n))
                    self.assertEqual(nand.eval_graph_bit(nodes,root,vals,7),
                                     (truth>>pattern)&1)
        nodes,root=nand.graph(4,0x6996)
        self.assertNotEqual(nand.compiled_truth(nodes,root,4,7),
                            nand.compiled_truth(nodes,root,4,0))
    def test_sourcefree_four_input_structures_candidate_and_independent_peer(self):
        m,_=nand.train_meta(source.meta_training())
        other,_=peer.train_meta(source.meta_training())
        for family in source.FAMILIES[:3]:
            for seed in source.SEEDS:
                d=source.heldout(family,seed)
                cm,cr=nand.train_new(m,d["FIT"],mode="compact")
                pm,pr=peer.fit(other,d["FIT"])
                self.assertIsNotNone(cm,(family,seed,cr))
                self.assertIsNotNone(pm,(family,seed,pr))
                self.assertEqual(cr["FIT_bit_errors"],0)
                self.assertEqual(pr["FIT_bit_errors"],0)
                if family!=source.FAMILIES[0]:
                    self.assertEqual(cm["arity"],4)
                self.assertTrue(all(nand.score(cm,x)["exact"] for x in d["CHECK"]))
                self.assertTrue(all(peer.score(pm,x)["exact"] for x in d["CHECK"]))
                self.assertTrue(all(nand.score(cm,x)["exact"] for x in d["HELDOUT"]))
                self.assertTrue(all(peer.score(pm,x)["exact"] for x in d["HELDOUT"]))
                self.assertTrue(all(not nand.score(cm,source.hard_negative(x))["exact"]
                                    for x in d["HELDOUT"]))
    def test_compact_and_slow_graph_identical_trajectories_on_new_sources(self):
        m,_=nand.train_meta(source.meta_training())
        for family in source.FAMILIES[:3]:
            d=source.heldout(family,81)
            fast,_=nand.train_new(m,d["FIT"],mode="compact")
            slow,_=nand.train_new(m,d["FIT"],mode="graph")
            self.assertEqual(fast["compiled_lut"],slow["compiled_lut"])
            for ep in d["CHECK"]+d["HELDOUT"]:
                self.assertEqual(nand.rollout(fast,ep),nand.rollout(slow,ep))
    def test_carry_out_of_bitwise_family_fails_closed(self):
        m,_=nand.train_meta(source.meta_training())
        peer_m,_=peer.train_meta(source.meta_training())
        for seed in source.SEEDS:
            d=source.heldout(source.FAMILIES[3],seed)
            candidate,cr=nand.train_new(m,d["FIT"])
            equal,pr=peer.fit(peer_m,d["FIT"])
            self.assertIsNone(candidate,cr)
            self.assertIsNone(equal,pr)
    def test_labels_never_teacher_forced_during_heldout(self):
        d=source.heldout(source.FAMILIES[1],81)
        m,_=nand.train_meta(source.meta_training())
        mm,_=peer.train_meta(source.meta_training())
        cm,_=nand.train_new(m,d["FIT"])
        pm,_=peer.fit(mm,d["FIT"])
        original=d["HELDOUT"][0]
        flipped=copy.deepcopy(original)
        for x in flipped["events"]:x["observed"]^=15
        self.assertEqual(nand.rollout(cm,original),nand.rollout(cm,flipped))
        self.assertEqual(peer.rollout(pm,original),peer.rollout(pm,flipped))
    def test_source_generator_not_imported_by_models_or_older_originals(self):
        for file in ("f124dd_meta_compact_nand.py","f124dd_independent_compact_anf.py"):
            imports=[]
            for node in ast.walk(ast.parse((HERE/file).read_text())):
                if isinstance(node,ast.Import):imports.extend(n.name for n in node.names)
                if isinstance(node,ast.ImportFrom):imports.append(node.module or "")
            self.assertNotIn("f124dd_sourceonly_new_structures",imports)
            self.assertFalse(any(x.startswith(("f124dc_sourcefree_structures",
                           "f124cr_","f124cu_","f124co_")) for x in imports))
    def test_matched_public_data_and_no_firstuse(self):
        family=source.FAMILIES[1]
        rows=[trial.run(family,81,arm) for arm in trial.ARMS]
        for field in ("meta_task_public_sha256","FIT_public_sha256",
                      "CHECK_public_sha256","holdout_public_sha256"):
            self.assertEqual(len({x[field] for x in rows}),1)
        for row in rows:
            self.assertFalse(row["scientific_accepted"])
            self.assertEqual(row["new_original_scientific_firstuse"],0)
            self.assertFalse(row["old_DC_sciencefree_holdouts_reused"])
if __name__=="__main__":unittest.main()
