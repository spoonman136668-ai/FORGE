"""F124-DA sourcefree causal OPERATOR PROGRAM engineering qualification.

Checks that a causal program is actually learned from sequences, original
source programs remain generator-only, strong pooled competitor receives
identical grammar/public information, and no observed labels are fed back
during CHECK or HELDOUT. Scientific firstuse cannot be claimed by this test.
"""
from __future__ import annotations
import ast
import copy
from pathlib import Path
import unittest

import f124da_sourcefree_program_worlds as worlds
import f124da_shared_program_synthesis as model
import f124da_independent_program_control as peer
import f124da_edge_program_control as edge
import f124da_program_trial as trial

HERE=Path(__file__).resolve().parent

class CausalOperatorSynthesis(unittest.TestCase):
    def test_full_exact_program_search_is_same_size_both_independent_arms(self):
        self.assertEqual(model.COUNT,3456)
        self.assertEqual(len(tuple(model.all_programs())),3456)
        self.assertEqual(len(tuple(peer.candidate_programs())),3456)
        self.assertEqual(tuple(model.all_programs()),tuple(peer.candidate_programs()))
    def test_original_FIT_inferred_program_not_provided(self):
        for seed in worlds.SEEDS:
            public=worlds.born(worlds.FAMILIES[0],seed)
            learner,receipt=model.train(public["FIT"])
            comparator,independent=peer.train(public["FIT"])
            self.assertIsNotNone(learner,(seed,receipt))
            self.assertIsNotNone(comparator,(seed,independent))
            self.assertEqual(learner["discovered_program"],comparator["program"])
            self.assertGreaterEqual(receipt["FIT_consistent_programs"],1)
            self.assertEqual(receipt["FIT_event_rows"],192)
            self.assertEqual(independent["FIT_rows"],192)
            self.assertEqual(receipt["syntax_trees_searched"],3456)
            self.assertTrue(receipt["CHECK_or_HELDOUT_in_fit"] is False)
    def test_recurrent_role_binding_and_teacher_free_heldout(self):
        ep=worlds.born(worlds.FAMILIES[0],51)
        learned,_=model.train(ep["FIT"])
        before=model.trajectory(learned,ep["HELDOUT"][0])
        altered=copy.deepcopy(ep["HELDOUT"][0])
        for row in altered["events"]:row["observed"]^=15
        self.assertEqual(before,model.trajectory(learned,altered))
        independent,_=peer.train(ep["FIT"])
        self.assertEqual(peer.predict(independent,ep["HELDOUT"][0]),
                         peer.predict(independent,altered))
    def test_role_permutation_equivariance(self):
        ep=worlds.born(worlds.FAMILIES[0],52)
        trained,_=model.train(ep["FIT"])
        source=ep["HELDOUT"][0]
        perm={"alpha":"gamma","beta":"alpha","gamma":"beta"}
        renamed={"initial":{perm[k]:list(v) for k,v in source["initial"].items()},
           "events":[{**row,"target":perm[row["target"]],
                      "source":perm[row["source"]]} for row in source["events"]]}
        self.assertEqual(model.trajectory(trained,source),
                         model.trajectory(trained,renamed))
    def test_independent_role_pair_comparator_trains_every_edge(self):
        public=worlds.born(worlds.FAMILIES[0],51)
        trained,receipt=edge.train(public["FIT"])
        self.assertIsNotNone(trained,receipt)
        self.assertEqual(receipt["edge_programs"],6)
        self.assertEqual(receipt["full_FIT_rows"],192)
    def test_source_generator_not_imported_in_both_pooled_solvers(self):
        for script in ("f124da_shared_program_synthesis.py",
                       "f124da_independent_program_control.py",
                       "f124da_edge_program_control.py"):
            tree=ast.parse((HERE/script).read_text())
            deps=[]
            for n in ast.walk(tree):
                if isinstance(n,ast.Import):deps.extend(x.name for x in n.names)
                elif isinstance(n,ast.ImportFrom):deps.append(n.module or "")
            self.assertNotIn("f124da_sourcefree_program_worlds",deps)
            self.assertFalse(any(n.startswith(("f124cu_","f124cz_outofclass_fixture"))
                                 for n in deps))
    def test_same_public_case_and_no_scientific_acceptance(self):
        for family in worlds.FAMILIES:
            for arm in trial.ARMS:
                x=trial.run(family,51,arm)
                self.assertEqual(x["FIT_episodes"],24)
                self.assertEqual(x["CHECK_veto_only_episodes"],8)
                self.assertEqual(x["scientific_firstuse_consumed"],0)
                self.assertFalse(x["scientific_acceptance"])
                self.assertTrue(x["all_old_original_scientific_924_to_937_sources_untouched"])
                self.assertEqual(x["HELDOUT_positive_episodes"],8)
    def test_reject_oracle_extra_source_field_and_wrong_sequence_length(self):
        public=worlds.born(worlds.FAMILIES[0],51)
        bad=copy.deepcopy(public["FIT"])
        bad[0]["events"][0]["private_program"]="no"
        with self.assertRaises(ValueError):model.train(bad)
        bad=copy.deepcopy(public["FIT"]);bad[0]["events"].pop()
        with self.assertRaises(ValueError):peer.train(bad)

if __name__=="__main__":unittest.main()
