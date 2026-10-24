"""K4Y source-only tests: no original environment and no CHECK/DEV evaluation."""
import pathlib,sys,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
import k4y_fit_forward_identifiability as k

class K4Y(unittest.TestCase):
    def test_calibration_and_bacc(self):
        held=[{"moved":1},{"moved":1},{"moved":0},{"moved":0}]
        self.assertEqual(k.metrics(held,[1,1,0,0])["balanced_accuracy"],1.0)
        self.assertEqual(k.metrics(held,[1,1,1,1])["balanced_accuracy"],0.5)
        self.assertEqual(k.metrics(held,[0,0,1,1])["balanced_accuracy"],0.0)
    def test_conventional_sensor_count(self):
        t=[{"blocked":False,"dir":0,"moved":1} for _ in range(3)]+[
          {"blocked":True,"dir":0,"moved":0} for _ in range(3)]
        h=[{"blocked":True},{"blocked":False}]
        self.assertEqual(k.predict_count(t,h,lambda r:r["blocked"],1),[0,1])
        self.assertEqual(k.predict_count(t,h,lambda r:r["dir"] if "dir" in r else None,0),[0,0])
    def test_zero_class_denied(self):
        with self.assertRaisesRegex(ValueError,"MISSING_BINARY_CLASS"):
            k.metrics([{"moved":1}],[1])
    def test_no_counterfactual_action(self):
        conf={"roles":{"curricula":["random_equal_budget"],"families":["empty"]},
              "original":{"expected_original_fit_transitions_per_curriculum":2}}
        rows=[
          {"family":"empty","action":1,"seed":7300,"before":{"X":1},"after":{"X":1}},
          {"family":"empty","action":2,"seed":7300,"before":{"Direction":0,"FrontBlocked":True,"GoalX":2,"GoalY":3,"X":1,"Y":3},
             "after":{"Direction":0,"FrontBlocked":True,"GoalX":2,"GoalY":3,"X":1,"Y":3}}]
        out=k.forward_rows({"random_equal_budget":{"FIT_source_gate":{"qualified":True},"fit_stream":rows}},conf)
        self.assertEqual(len(out["random_equal_budget"]),1)
        self.assertEqual(out["random_equal_budget"][0]["moved"],0)
    def test_fail_closed_observation_drift(self):
        conf={"roles":{"curricula":["random_equal_budget"],"families":["empty"]},
              "original":{"expected_original_fit_transitions_per_curriculum":1}}
        r={"family":"empty","seed":7300,"action":2,"before":{"Direction":0,"FrontBlocked":True,"GoalX":2,"GoalY":3,"X":1,"Y":3},
           "after":{"Direction":1,"FrontBlocked":True,"GoalX":2,"GoalY":3,"X":1,"Y":3}}
        with self.assertRaisesRegex(ValueError,"FORWARD_ROTATION"):
            k.forward_rows({"random_equal_budget":{"FIT_source_gate":{"qualified":True},"fit_stream":[r]}},conf)
    def test_fit_only_parser_never_decodes_dev(self):
        raw=b'{"FIT":{"random_equal_budget":{"fit_stream":[]}},"DEV_original_public_traces":{INVALID_JSON},"scientific":false}'
        p=k.extract_fit_only(raw)
        self.assertEqual(p["random_equal_budget"]["fit_stream"],[])
        with self.assertRaisesRegex(ValueError,"FIT_FIELD"):
            k.extract_fit_only(b'{"CHECK":0}')
    def test_freeze_source_roles(self):
        import json
        f=json.loads(k.FREEZE.read_text())
        self.assertEqual(f["roles"]["FIT_RECONSTRUCTION_TRAIN_SEEDS"],[7300,7315])
        self.assertEqual(f["roles"]["FIT_RETROSPECTIVE_HOLD_SEEDS"],[7316,7323])
        self.assertTrue(f["governance"]["no_READ_dev_or_check_rows"])
        self.assertTrue(f["governance"]["no_first_use_or_FSA"])
if __name__=="__main__":unittest.main()
