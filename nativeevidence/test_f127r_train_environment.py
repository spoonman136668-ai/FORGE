"""F127-R distinct FIT/TRAIN_CHECK and protected seed denial."""
from pathlib import Path
import copy,sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parent))
import f127r_train_environment as env
class TrainSource(unittest.TestCase):
    def test_source_fit_check_and_label_pairing(self):
        for lane in ("Wingless","Yggdrasil"):
            for stage in ("FIT","TRAIN_CHECK"):
                rows=env.cohort_rows(lane,[[1,2,3],[2,3,1]],stage)
                self.assertEqual(len(rows),64)
                self.assertEqual(sum(y for _,y in rows),32)
                for k in range(0,len(rows),2):
                    p,_=rows[k];n,_=rows[k+1]
                    self.assertEqual(env.marginals(p),env.marginals(n))
                    self.assertEqual(env.graph_paths(p,True),1)
                    self.assertEqual(env.graph_paths(n,True),0)
                    self.assertIn(env.graph_paths(p),range(6,13))
    def test_reserved_not_constructible(self):
        for lane,seed in (("Wingless",180200),("Yggdrasil",190200),
                          ("Wingless",160100),("Yggdrasil",170100)):
            for stage in ("FIT","TRAIN_CHECK"):
                with self.assertRaises(env.Invalid):
                    env.build(seed,[1,2,3],lane,stage)
    def test_disjoint_source_ids_and_public_only(self):
        a=env.cohort_rows("Wingless",[[1,2,3],[2,3,1]],"FIT")
        b=env.cohort_rows("Wingless",[[1,2,3],[2,3,1]],"TRAIN_CHECK")
        self.assertFalse(set(env.digest(x) for x,y in a)&set(env.digest(x) for x,y in b))
        p,_=env.build(180100,[1,2,3],"Wingless","FIT")
        rev=copy.deepcopy(p);rev["edges"].reverse()
        self.assertEqual(env.graph_paths(rev,True),1)
        p["oracle_true_path"]=0
        with self.assertRaises(env.Invalid):env.validate(p)
if __name__=="__main__":unittest.main()
