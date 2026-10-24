"""K4R source-only public gridworld and real learned dynamics safeguards."""
import json
import unittest
from k4r_minigrid_source import (
    FROZEN,FAMILIES,POLICIES,EXPERT_MOVES,frozen,seeds,empirical_model,
    fitted,motion,bfs,learn_q,evidence,recorded_fit_transition,canon)

def fake_transition(a,d,blocked=False):
    moves=((1,0),(0,1),(-1,0),(0,-1))
    pos=[5,5]
    nxt=pos[:];nd=d
    if a==0:nd=(d-1)%4
    elif a==1:nd=(d+1)%4
    elif a==2 and not blocked:
        nxt=[pos[i]+moves[d][i] for i in range(2)]
    return {"family":"empty","world_seed":1000,
       "action":a,"pos":pos,"dir":d,"next_pos":nxt,"next_dir":nd,
       "public_front_blocked":bool(blocked),
       "start_key":"s"+str(d),"next_key":"s"+str(nd),
       "reward":0.0,"terminated":False}

def fake_fit():
    return [fake_transition(a,d,blocked)
            for a in (0,1,2) for d in range(4)
            for blocked in ([False,True] if a==2 else [False])
            for replicate in range(5)]

def state(x=1,y=1,d=0,goal=(4,4)):
    return {"x":x,"y":y,"dir":d,"goal":goal,
            "walls":frozenset({(0,k) for k in range(6)}|
               {(5,k) for k in range(6)}|
               {(k,0) for k in range(6)}|
               {(k,5) for k in range(6)}),"shape":(6,6)}

class K4RSourceGuard(unittest.TestCase):
    def test_frozen_true_independent_source(self):
        p=frozen()
        self.assertEqual(p["independent_source"]["commit"],
            "7f5853792ea7f04f75614661006d87fcf949f26d")
        self.assertEqual(list(seeds("FIT")),list(range(1100,1124)))
        self.assertEqual(list(seeds("CHECK")),list(range(2100,2104)))
        self.assertEqual(list(seeds("DEV")),list(range(3100,3108)))
        self.assertEqual(FAMILIES,("empty","fourrooms"))
        self.assertFalse(p["evaluation"]["governance"]["scientific_accepted"])

    def test_empirical_motion_not_hard_coded(self):
        model,counts=empirical_model(fake_fit())
        self.assertTrue(counts["matches_public_documented_semantics"])
        self.assertEqual(model["turns"],{"0":3,"1":1})
        self.assertEqual(tuple(model["moves"]["0"]),(1,0))
        self.assertEqual(tuple(model["blocked_forward"]),(0,0))

    def test_missing_real_forward_directions_fails_closed(self):
        source=[r for r in fake_fit() if not (r["action"]==2 and r["dir"]==3)]
        model,counts=empirical_model(source)
        self.assertIsNone(model)
        self.assertFalse(counts["FIT_motion_support_complete"])

    def test_semantic_mismatch_does_not_qualify(self):
        rows=fake_fit()
        for r in rows:
            if r["action"]==0:r["next_dir"]=(r["dir"]+1)%4
        model,counts=empirical_model(rows)
        self.assertFalse(counts["matches_public_documented_semantics"])

    def test_wall_bounded_navigation(self):
        m={"turns":{"0":3,"1":1},
            "moves":{str(i):list(EXPERT_MOVES[i]) for i in range(4)},
            "walls":state()["walls"],"shape":state()["shape"]}
        self.assertEqual(motion((1,1,2),2,m),(1,1,2))
        self.assertEqual(motion((1,1,0),2,m),(2,1,0))
        self.assertEqual(motion((1,1,0),0,m),(1,1,3))

    def test_public_bfs_first_decision_context_sensitive(self):
        a=bfs(state(1,1,0,goal=(4,1)),None)
        b=bfs(state(1,1,0,goal=(1,4)),None)
        self.assertNotEqual(a,b)
        self.assertIn(a,(0,1,2))
        self.assertIn(b,(0,1,2))

    def test_fit_q_only_same_source_transitions(self):
        a=learn_q(fake_fit())
        self.assertTrue(a)
        self.assertTrue(all(len(v)==3 for v in a.values()))

    def test_success_gates_on_both_unfamiliar_families(self):
        dev=[]
        for family in FAMILIES:
            for i in range(8):
                for method in POLICIES:
                    is_success=method in ("learned_model_bfs","public_bfs_expert")
                    dev.append({"family":family,"seed":3100+i,"policy":method,
                        "success":is_success,"reward":.9 if is_success else 0.,
                        "first_action":i%3 if method=="public_bfs_expert" else 2})
        v=evidence(frozen(),dev)
        self.assertEqual(v["result"],"INDEPENDENT_INTERACTIVE_SOURCE_QUALIFIED")
        self.assertFalse(v["scientific_accepted"] if "scientific_accepted" in v else v["original_scientific_acceptance"])

    def test_one_family_failure_vetoes_positive(self):
        dev=[]
        for family in FAMILIES:
            for i in range(8):
                for method in POLICIES:
                    win=method in ("learned_model_bfs","public_bfs_expert") and family=="empty"
                    dev.append({"family":family,"seed":3100+i,"policy":method,
                        "success":win,"reward":.9 if win else 0.,
                        "first_action":i%3 if method=="public_bfs_expert" else 2})
        self.assertEqual(evidence(frozen(),dev)["result"],"INDEPENDENT_SOURCE_NOT_QUALIFIED")

    def test_expert_optimal_action_diversity_is_required(self):
        dev=[]
        for family in FAMILIES:
            for i in range(8):
                for method in POLICIES:
                    success=method in ("learned_model_bfs","public_bfs_expert")
                    dev.append({"family":family,"seed":3100+i,"policy":method,
                        "success":success,"reward":.9 if success else 0.,
                        "first_action":2})
        self.assertEqual(evidence(frozen(),dev)["result"],"INDEPENDENT_SOURCE_NOT_QUALIFIED")

if __name__=="__main__":
    unittest.main()
