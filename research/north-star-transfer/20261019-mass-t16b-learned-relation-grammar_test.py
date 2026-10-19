"""T16B Mass relational grammar unit tests: no T16 source materialization."""
import importlib.util,random,sys,unittest
from pathlib import Path
path=Path(__file__).with_name("20261019-mass-t16b-learned-relation-grammar.py")
spec=importlib.util.spec_from_file_location("mass_t16b",path)
m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)

def witnesses(role,perm):
    def repeat(n):return sum(n<<(4*j) for j in range(4))
    return role,tuple((repeat(x),repeat(perm[x])) for x in range(16))

class RelationalGrammarTests(unittest.TestCase):
    def setUp(self):
        self.p=tuple(random.Random(173).sample(range(16),16))
        self.q=m.invert(self.p)
        self.r=m.compose(self.p,self.p)

    def test_genuine_sourceblind_relation_discovery(self):
        training=[witnesses("ALPHA",self.p),witnesses("BETA",self.q),
                  witnesses("GAMMA",self.r)]
        learned=m.discover(training)
        self.assertEqual(learned["public_mismatches"],0)
        self.assertEqual(learned["maps"]["ALPHA"],self.p)
        self.assertEqual(learned["maps"]["BETA"],self.q)
        self.assertEqual(learned["maps"]["GAMMA"],self.r)
        self.assertLess(learned["model_bytes"],24)
        self.assertFalse(learned["source_defined_relationship_assumed"])

    def test_role_aliasing_invariance(self):
        a=m.discover([witnesses("ALPHA",self.p),witnesses("BETA",self.q),
                      witnesses("GAMMA",self.r)])
        b=m.discover([witnesses("JULIET",self.p),witnesses("KILO",self.q),
                      witnesses("LIMA",self.r)])
        self.assertEqual(tuple(a["maps"][s] for s in ("ALPHA","BETA","GAMMA")),
                         tuple(b["maps"][s] for s in ("JULIET","KILO","LIMA")))

    def test_unrelated_relationship_does_not_get_hardcoded(self):
        other=tuple(random.Random(142).sample(range(16),16))
        training=[witnesses("ALPHA",self.p),witnesses("BETA",other)]
        model=m.discover(training)
        self.assertEqual(model["public_mismatches"],0)
        self.assertEqual(model["maps"]["BETA"],other)
        self.assertEqual(model["operations"]["BETA"],"independent")
        self.assertEqual(model["model_bytes"],16)

    def test_structural_equal_info_strong_control_also_correct(self):
        cases=[witnesses("ALPHA",self.p),witnesses("BETA",self.q),
               witnesses("GAMMA",self.r)]
        learned=m.discover(cases)
        trained=m.equal_data_independent(cases)
        self.assertEqual(trained["public_mismatches"],0)
        self.assertEqual(learned["public_mismatches"],0)
        # Never mislabel compression on PUBLIC train as superior to this
        # equally informed trained full-map control on unseen tasks.
        self.assertEqual(m.infer_word(learned["maps"],("ALPHA","BETA","GAMMA")),
                         m.infer_word(trained["maps"],("ALPHA","BETA","GAMMA")))

    def test_ordered_noncommutative_composition(self):
        other=tuple(random.Random(327).sample(range(16),16))
        self.assertNotEqual(m.infer_word({"a":self.p,"b":other},("a","b")),
                            m.infer_word({"a":self.p,"b":other},("b","a")))

    def test_no_hidden_private_held_output_required(self):
        cases=[witnesses("A",self.p),witnesses("B",self.q)]
        learned=m.discover(cases)
        self.assertGreater(learned["train_nibble_observations"],0)
        self.assertTrue(learned["relationship_learned_from_public"])

    def test_invalid_nibble_bounds_are_rejected(self):
        with self.assertRaises(AssertionError):
            m.discover([("A",((65536,0),))])

if __name__=="__main__":
    unittest.main()
