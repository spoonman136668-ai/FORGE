"""One-shot MP-AI06 no-production-writer negative contract tests."""
import pathlib,sys,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"tools"))
import mpai06_usage_feedback_gate as m
class TestRealFeedbackContract(unittest.TestCase):
    def test_runs_frozen(self):
        self.assertEqual(len(m.RUNS),2)
        self.assertEqual(m.RUNS["40865946484"],
            "f5900a0336995123238e22d124f90875ea1154c0")
    def test_two_accepted_lessons(self):
        self.assertEqual(set(m.IDS),{"Wingless","Yggdrasil"})
        self.assertNotEqual(*m.IDS.values())
    def test_candidate_correctly_cites_sources(self):
        b=m.batch()
        self.assertEqual(b["schema"],"mind-palace.collector-batch.v1")
        self.assertEqual(len(b["candidates"]),1)
        self.assertEqual(len(b["sources"]),3)
        self.assertEqual(b["candidates"][0]["details"]["scientific_acceptance"],False)
        self.assertEqual(b["candidates"][0]["kind"],"lesson")
    def test_primary_refs_protected(self):
        b=m.batch()
        src=b["sources"][0]
        self.assertEqual(src["role"],"primary")
        self.assertEqual(src["type"],"commit")
        self.assertEqual(src["ref"],b["candidates"][0]["source_refs"][0]["ref"])
    def test_disjoint_pending_record(self):
        self.assertNotIn(m.NEW,m.IDS.values())
        self.assertEqual(m.NEW.split("/",1)[0],"lesson")
    def test_nine_protected_paths(self):
        self.assertEqual(len(m.GUARD),9)
        self.assertIn(".ice/records.json",m.GUARD)
        self.assertIn(".ice/source-ledger.json",m.GUARD)
    def test_no_staging_writer_or_scheduler(self):
        script=pathlib.Path(m.__file__).read_text("utf-8")
        self.assertNotIn('"stage","-InputPath"',script)
        for banned in ("write_accepted_ice(","promote_candidate(","model.create_chat_completion(",
                       "openai.OpenAI(", "git push", "workflow_dispatch"):
            self.assertNotIn(banned,script)
    def test_fail_closed_identity(self):
        with self.assertRaisesRegex(RuntimeError,"MPAI06_CONTRACT_DENIED"):
            m.check(False,"CONTRACT_DENIED")
if __name__=="__main__":unittest.main()
