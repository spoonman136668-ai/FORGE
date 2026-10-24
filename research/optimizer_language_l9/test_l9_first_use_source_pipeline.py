"""Synthetic-only qualification: graph-only source adapter, frozen seven-arm wiring.

No original WebNLG, DEV reference, training fit or neural checkpoint is read.
"""
from __future__ import annotations
from unittest.mock import patch
import dataclasses
import json
import unittest
import l9_first_use_source_pipeline as p
import l9_first_use_scoring_core as score
import l9_split_builder as split
import l9_model_suite as model

SENTINEL="DO_NOT_LEAK_REFERENCE_634909"
def categories():
    names=[]
    for n in range(250):
        key="invented-out-of-training-"+str(n)
        if split.category_partition(key)=="L9_AUDIT_CATEGORY":names.append(key)
        if len(names)==3:return names
    raise AssertionError("failed invented categories")
def xml(cat,subject,city):
    return (f'<benchmark><entries><entry category="{cat}">'
            f'<modifiedtripleset><mtriple>{subject} | livesIn | {city}</mtriple></modifiedtripleset>'
            f'<lex>{SENTINEL}</lex></entry></entries></benchmark>').encode("utf-8")
def fake_rows():
    rows=[]
    for i,cat in enumerate(categories()):
        rows+=p.graph_only_xml(xml(cat,"Person"+str(i),"Town"+str(i)),"f"*40)
    return rows
def renderers():
    def output(triples):
        return triples[0].subject+" is in "+triples[0].object+"."
    return {arm:output for arm in score.ARMS}

class FirstUseSourceTests(unittest.TestCase):
    def test_graph_only_never_extracts_lex(self):
        rows=fake_rows()
        self.assertEqual(len(rows),3)
        for row in rows:
            self.assertIs(type(row),p.GraphOnly)
            self.assertFalse(hasattr(row,"references"))
            self.assertFalse(hasattr(row,"reference"))
            self.assertEqual(row.entry_index,0)
            self.assertEqual(row.blob_oid,"f"*40)
            self.assertNotIn(SENTINEL,repr(row))
        p.validate_graph_inputs(rows,{"a"*64},expected_count=3,expected_categories=3)

    def test_reference_reader_called_only_after_all_21_predictions(self):
        rows=fake_rows();seen=[]
        callbacks={}
        for arm in score.ARMS:
            def do(triples,a=arm):
                seen.append(("prediction",a))
                self.assertTrue(all(isinstance(t,model.Triple) for t in triples))
                return triples[0].subject+" is in "+triples[0].object+"."
            callbacks[arm]=do
        outputs=p.prediction_only_pass(rows,callbacks,{"a"*64},3,3)
        self.assertEqual(len(seen),21)
        def read_graph(row):
            self.assertEqual(len(seen),21,"reference exposed before all model predictions")
            seen.append(("reference",row.graph_sha256))
            return (SENTINEL,"Other human text")
        cases=p.attach_refs_after_prediction(rows,outputs,read_graph,{"a"*64},3,3)
        self.assertEqual(len(cases),3)
        self.assertEqual(len([x for x in seen if x[0]=="reference"]),3)
        reports=[p.score_precomputed_arm(arm,cases,outputs,{"livesin":["is in"]},
                          {"a"*64},3,3) for arm in score.ARMS]
        bundle=score.combine_reports(reports,3,3)
        self.assertEqual(bundle["arm_count"],7)
        self.assertEqual(bundle["heldout_examples"],3)
        self.assertNotIn(SENTINEL,json.dumps(bundle))
        self.assertFalse(bundle["scientific_go"])

    def test_missing_neural_arm_blocks_before_reference_read(self):
        rows=fake_rows()
        partial=renderers();partial.pop(score.ARMS[-1])
        with self.assertRaises(ValueError):
            p.prediction_only_pass(rows,partial,{"a"*64},3,3)
        valid=p.prediction_only_pass(rows,renderers(),{"a"*64},3,3)
        valid.pop(score.ARMS[3])
        accessed=[]
        def read(row):
            accessed.append(1);return (SENTINEL,)
        with self.assertRaises(ValueError):
            p.attach_refs_after_prediction(rows,valid,read,{"a"*64},3,3)
        self.assertEqual(accessed,[])

    def test_bad_graph_category_and_train_overlap_fail(self):
        rows=fake_rows()
        for method in ("bad_category","overlap","bad_graph","missing","bad_type"):
            mutated=list(rows);seen={"a"*64}
            if method=="bad_category":
                row=mutated[0];mutated[0]=dataclasses.replace(row,category="another-training-category")
            if method=="overlap":seen={rows[0].graph_sha256}
            if method=="bad_graph":
                mutated[0]=dataclasses.replace(mutated[0],graph_sha256="0"*64)
            if method=="missing":mutated.pop()
            if method=="bad_type":mutated[1]="unexpected string"
            with self.subTest(method=method),self.assertRaises(ValueError):
                p.validate_graph_inputs(mutated,seen,3,3)

    def test_training_fit_requires_exact_train_role(self):
        fake=type("E",(),{"role":"L9_SELECT"})()
        with self.assertRaises(ValueError):
            p.fit_frozen_train_states([fake]*8480)
        with self.assertRaises(ValueError):
            p.fit_frozen_train_states([])

    def test_selected_neural_checkpoint_grid_is_exact(self):
        self.assertEqual(set(p.EXPECTED_NEURAL),set(score.ARMS[3:]))
        self.assertTrue(all(e==12 for _,_,e,_ in p.EXPECTED_NEURAL.values()))
        with patch.object(p.neural,"model_from_checkpoint") as load:
            load.side_effect=lambda arm,seed,epoch,path: (
                f"frozen-{arm}-{seed}",
                {"inference_sha256":next(info[3] for info in p.EXPECTED_NEURAL.values()
                                   if info[:3]==(arm,seed,epoch)), "inference_bytes":1234})
            result=p.load_exact_neural_checkpoints(__import__("pathlib").Path("synthetic"))
            self.assertEqual(set(result),set(p.EXPECTED_NEURAL))
            self.assertEqual(load.call_count,4)
            self.assertTrue(all(args.args[2]==12 for args in load.call_args_list))

    def test_frozen_render_method_routing_and_no_model_reference(self):
        candidate={"fake_state":1};retrieval={"fake_state":2}
        with patch.object(p,"exact_sha",side_effect=lambda s:
             p.CANDIDATE_STATE_SHA if s is candidate else p.RETRIEVAL_STATE_SHA):
            selected={arm:"stub-"+arm for arm in p.EXPECTED_NEURAL}
            with patch.object(p.neural,"inference_one",side_effect=lambda n,arm,triples:"GRU_RESULT"), \
                 patch.object(p.transformer,"reuse_inference_one",side_effect=lambda n,triples:"TRANS_RESULT"), \
                 patch.object(p.model,"realize_candidate",return_value="CANDIDATE"), \
                 patch.object(p.model,"realize_retrieval",return_value="RETRIEVAL"):
                render=p.frozen_renderers(candidate,retrieval,selected)
                self.assertEqual(tuple(render),score.ARMS)
                triples=fake_rows()[0].triples
                self.assertEqual(render["COMPOSITIONAL_PATTERN"](triples),"CANDIDATE")
                self.assertEqual(render["TRAIN_REFERENCE_RETRIEVAL"](triples),"RETRIEVAL")
                for arm in score.ARMS[3:]:
                    self.assertEqual(render[arm](triples),
                       "GRU_RESULT" if arm.startswith("GRU_") else "TRANS_RESULT")

    def test_no_reselection_and_no_original_reference_copy(self):
        self.assertEqual(p.SELECTED_CONFIG,model.CandidateConfig(1,4," "))
        self.assertEqual(p.CANDIDATE_STATE_SHA,
           "6bfcae415a3f1145397875b715c7d5015143e1544381be6a031eed636be88c3c")
        self.assertEqual(p.RETRIEVAL_STATE_SHA,
           "ed7b21b6c4f648b337491aa5240ed1a7326f23164a13a0503748aded689e377b")
        self.assertEqual(len(p.EXPECTED_NEURAL),4)
        self.assertEqual(p.EXPECTED_TOTAL,319)
        self.assertEqual(p.EXPECTED_CATEGORIES,3)

if __name__=="__main__":unittest.main()
