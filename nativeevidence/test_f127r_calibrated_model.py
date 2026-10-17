import unittest
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import f127r_calibrated_model as model
import f127r_train_environment as env
class TestModel(unittest.TestCase):
    def test_forward(self):
        graph,_=env.build(180100,[1,2,3],'Wingless','FIT')
        p,gradient=model.forward(graph,model.INIT)
        self.assertEqual(len(gradient),22)
        self.assertGreater(p,0)
        self.assertLess(p,1)
if __name__=='__main__':unittest.main()
