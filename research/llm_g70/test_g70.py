"""No-network frozen ONNX compatibility contract; original model run is hosted."""
import importlib.util
import inspect
from pathlib import Path
import unittest
p=Path(__file__).with_name("g70_onnx_compat.py")
spec=importlib.util.spec_from_file_location("g70",p)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class FrozenG70(unittest.TestCase):
    def test_frozen(self):m.pure_contract()
    def test_prereg(self):self.assertEqual(m.PREREG,"51469831afc16ff1fd320656c2bd3960c4e812d6")
    def test_model_id(self):
        self.assertEqual(m.MODEL_REV,"607a30d783dfa663caf39e06633721c8d4cfcd7e")
        self.assertEqual(m.WEIGHTS_SHA,"248dfc3911869ec493c76e65bf2fcf7f615828b0254c12b473182f0f81d3a707")
    def test_dataset(self):
        self.assertEqual(m.DATA_REV,"3101c7d5072418e28b9008a6636bde82a006892c")
        self.assertEqual(m.DATA_SHA,"3730d312f6e3440559ace48831e51066acaca737f6eabec99bccb9e4b3c39d14")
    def test_selector(self):self.assertEqual(m.POSITIONS,(0,5,11))
    def test_cohorts(self):
        self.assertEqual(m.COHORTS,("high_shared_system","unique_system"))
    def test_length(self):self.assertEqual((m.TOKENS,m.REPEATS,m.CPU_BUDGET),(8,2,3))
    def test_original_source(self):self.assertEqual(m.BASE,"a3ef4e4d7fb16211367ebbdfa9367cc862ceb02f")
    def test_nonpromotion(self):
        s=inspect.getsource(m.main)
        self.assertIn('"scientific_acceptance":"NOT_GRANTED"',s)
        self.assertIn('"promotion_allowed":False',s)
        self.assertIn('"performance_acceptance":"NOT_EVALUATED"',s)
    def test_no_weight_substitute(self):
        s=inspect.getsource(m.main)
        self.assertIn('use_safetensors=True',s)
        self.assertIn('export=True',s)
    def test_exact_model_generation(self):
        s=inspect.getsource(m.main)
        self.assertIn('min_new_tokens=TOKENS',s)
        self.assertIn('if observed!=baseline:',s)
if __name__=="__main__":
    unittest.main()
