"""F124-AC independent frozen terminal readout science tests."""
import json,unittest
import f124ac_source as src
import f124ac_terminal_intervention as A
import f124o_native_learners as O

class F124ACTests(unittest.TestCase):
    def test_preregistration_and_protected_quarantine(self):
        self.assertEqual(len(src.frozen()),64)
        p=json.loads(src.PROTOCOL.read_text())
        self.assertEqual(p["parent_head"],"ac2f08071101ef92e466ee85e0c1ba798ce2be99")
        self.assertEqual(p["parent_run"],39092921418)
        self.assertEqual(p["design"]["state"],[7,9])
        self.assertEqual(A.GRID,(0.,.1,.2,.4,.8,1.6,3.2))
        self.assertTrue(p["qualification"]["draft_only"])
        with self.assertRaises(src.Quarantined):src.protected()

    def test_entire_new_paired_source_admitted_on_FIT_and_DEV(self):
        self.assertTrue(set(src.COHORTS["YggdrasilStress"]["FIT"]).isdisjoint(
                        src.COHORTS["YggdrasilStress"]["DEV"]))
        for phase in ("FIT","DEV"):
            depth={10:0,11:0,12:0}
            for vec in src.VECTORS:
                for seed in src.COHORTS["YggdrasilStress"][phase]:
                    p,n=src.transfer_pair(seed,vec,phase,"long_depth")
                    self.assertTrue(src.paired_admit(p,n))
                    depth[len(p["roles"])]+=1
            self.assertEqual(depth,{10:16,11:16,12:16})

    def test_terminal_readout_is_label_and_oracle_blind(self):
        weights={"base":list(O.YGGDRASIL_INIT),"R":[.05,.02],
                 "S":[.1,.07],"U":[.06,-.09]}
        pos,neg=src.transfer_pair(2090000,[2,1,1],"FIT","long_depth")
        path=A.exact_positive_prefix(pos)
        for arm in A.ARMS:
            for graph in (pos,neg):
                before=A.forward(arm,graph,weights,"diverse",alpha=0.,beta=0.)
                with_correction=A.forward(arm,graph,weights,"diverse",
                                           alpha=.2,beta=.4)
                self.assertEqual(before["final_active"],with_correction["final_active"])
                self.assertEqual(before["final_retained"],with_correction["final_retained"])
                self.assertLessEqual(before["final_active"],7)
                self.assertLessEqual(before["final_retained"],9)
            after=A.forward(arm,pos,weights,"diverse",positive_prefix=path)
            before=A.forward(arm,pos,weights,"diverse")
            self.assertEqual(before["logit_hex"],after["logit_hex"])
            self.assertEqual(before["terminal_exact_link_confirmed"],
                             after["terminal_exact_link_confirmed"])

    def test_selection_never_touches_DEV(self):
        fake={arm:[{"depth":10+i//16,"positive_base":-.1,"negative_base":-2.,
                    "positive_exact_link":True,"negative_exact_link":False,
                    "case":i,"original_path_lost":False,
                    "positive_terminal_cell_count":1,
                    "negative_terminal_cell_count":0} for i in range(48)]
              for arm in A.ARMS}
        chosen,_=A.choose_fit(fake)
        for arm in A.ARMS:
            self.assertEqual(chosen[arm]["unchanged"]["alpha"],0.)
            self.assertEqual(chosen[arm]["unchanged"]["beta"],0.)
            self.assertEqual(chosen[arm]["combined"]["FP"],0)
        self.assertEqual(len(A.candidates("combined")),49)

if __name__=="__main__": unittest.main()
