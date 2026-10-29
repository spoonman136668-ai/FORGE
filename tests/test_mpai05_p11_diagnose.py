"""P11 negative tests; synthetic source fields, no network, no inference."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
import mpai05_p11_diagnose as d

class P11DiagnosisTests(unittest.TestCase):
    def write(self, rows):
        directory=tempfile.TemporaryDirectory()
        path=Path(directory.name)/"trajectories.jsonl"
        path.write_text("\n".join(json.dumps(row) for row in rows)+"\n",encoding="utf-8")
        return directory,path
    def test_included_and_ignored_key_count(self):
        tr,path=self.write([{"id":"t1","domain":"web","states":[
            {"action":"saved address","observed_text":"confirmed account status",
             "screenshot":"private.png","thought":"check UI","accessible_tree":""},
            {"accessibility_tree":"UI shows saved address"}]}])
        try:
            metrics,keys,unused,contents=d.inspect_states(path,{"t1":"web"})
            self.assertEqual(metrics["state_objects"],2)
            self.assertEqual(metrics["supported_nonempty_fields"],3)
            self.assertEqual(metrics["trajectories_with_supported_text"],1)
            self.assertEqual(unused["observed_text"],1)
            self.assertEqual(keys["screenshot"],1)
            self.assertNotIn("private.png",str(contents))
        finally: tr.cleanup()
    def test_unsupported_only_is_detected(self):
        tr,path=self.write([{"id":"t1","domain":"web",
            "states":[{"observation":"required fact available","screenshot":"x"}]}])
        try:
            m,k,unused,_=d.inspect_states(path,{"t1":"web"})
            self.assertEqual(m["trajectories_without_supported_text"],1)
            self.assertEqual(unused["observation"],1)
        finally: tr.cleanup()
    def test_no_selected_trajectory_silent_skip(self):
        tr,path=self.write([{"id":"t1","domain":"web","states":[]}])
        try:
            with self.assertRaisesRegex(RuntimeError,"SELECTED_TRAJECTORIES_INCOMPLETE"):
                d.inspect_states(path,{"t1":"web","t2":"web"})
        finally:tr.cleanup()
    def test_duplicate_trajectory_denied(self):
        rows=[{"id":"t1","domain":"web","states":[]}]*2
        tr,path=self.write(rows)
        try:
            with self.assertRaisesRegex(RuntimeError,"DUPLICATE_SELECTED_TRAJECTORY"):
                d.inspect_states(path,{"t1":"web"})
        finally:tr.cleanup()
    def test_cross_domain_denied(self):
        tr,path=self.write([{"id":"t1","domain":"enterprise","states":[]}])
        try:
            with self.assertRaisesRegex(RuntimeError,"SELECTED_DOMAIN_DRIFT"):
                d.inspect_states(path,{"t1":"web"})
        finally:tr.cleanup()
    def test_literal_not_semantic_graded(self):
        self.assertTrue(d.has_literal("Shipping address","Your shipping address was updated"))
        self.assertFalse(d.has_literal("shipping address","Account settings changed"))
        self.assertFalse(d.has_literal("a","a"))
        self.assertFalse(d.has_literal(None,"foo"))
    def test_gold_cannot_choose_cohort(self):
        self.assertEqual(d.EXPECTED_COHORT,
           "103dbf87dda69f03b32f4c6a3a987b5ab5b7a8d3c3ceeb11f223ad5cf358ae52")
        self.assertEqual(d.EXPECTED_GRADED,11)
        self.assertEqual(d.EXPECTED_UNSCORABLE,5)
    def test_source_does_not_call_model_or_modify_ice(self):
        source=Path(d.__file__).read_text(encoding="utf-8")
        for forbidden in ("create_chat_completion(","Llama(","accepted_ice_write(",
                          "eval_from_spec(","openai.chat.completions"):
            self.assertNotIn(forbidden,source)
        self.assertIn("p10.get_text_trajectories(",source)
        self.assertIn("p10.retrieve(",source)
if __name__=="__main__":unittest.main()
