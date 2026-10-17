"""F125-R fixed public control and paired source headroom guards."""
import pathlib,sys,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
import f125r_train_headroom as m
import f125r_train_environment as env

class FrozenHeadroom(unittest.TestCase):
    def test_exact_public_ceiling(self):
        rows=env.train_rows("Wingless",[[1,2,3],[2,3,1]])
        self.assertEqual(m.score(rows,m.exact_ceiling)["paired_correct"],64)
    def test_full_source_pairs_and_no_selective_exclusion(self):
        rows=env.train_rows("Yggdrasil",[[1,2,3],[3,1,2]])
        result=m.score(rows,m.approximate_12_of_16)
        self.assertEqual(result["pairs"],64)
        self.assertGreaterEqual(result["paired_correct"],0)
        self.assertLessEqual(result["paired_correct"],64)
        with self.assertRaises(env.Invalid):
            m.score(rows[:126],m.exact_ceiling)
    def test_role_only_is_label_blind(self):
        p,n=env.build(100100,[1,2,3],"Wingless")
        self.assertTrue(m.role_only(p))
        self.assertTrue(m.role_only(n))
    def test_unread_protected_confirmation(self):
        with self.assertRaises(env.Invalid):
            env.build(100200,[1,2,3],"Wingless")

if __name__=="__main__":unittest.main()
