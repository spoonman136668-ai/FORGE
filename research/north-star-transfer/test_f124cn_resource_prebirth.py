"""F124-CN resource machinery engineering qualification; -1 synthetic only."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

HERE=Path(__file__).resolve().parent
def module(file,name):
    spec=importlib.util.spec_from_file_location(name,HERE/file)
    m=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m
fixture=module("test_f124cn_prebirth.py","CN_synthetic_source_free_fixture")
observer=module("f124cn_complete_os_resource.py","CN_original_resource_observer")

class ResourcePrebirth(unittest.TestCase):
    @unittest.skipUnless(sys.platform=="linux","Linux wait4 OS CPU/RSS only")
    def test_real_os_cpu_rss_on_non_science_fixture(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            case=root/"synthetic.json"
            case.write_text(json.dumps(fixture.engineering_fixture()))
            original=observer.run_original_public_process(case,"CANDIDATE",synthetic=True)
            peer=observer.run_original_public_process(case,"TRAINED_CONTROL",synthetic=True)
            self.assertEqual(original["case_id"],-1)
            self.assertTrue(original["synthetic_engineering_only"])
            self.assertTrue(original["whole_OS_boot_import_train_score_included"])
            self.assertGreater(original["whole_OS_process_CPU_ns"],0)
            self.assertGreater(original["whole_OS_process_peak_RSS_bytes"],0)
            self.assertEqual(original["public_task_sha256"],peer["public_task_sha256"])
            self.assertEqual(original["graph_sha256"],peer["graph_sha256"])
            observer.append_journal(root/"append.jsonl",original)
            observer.append_journal(root/"append.jsonl",peer)
            lines=(root/"append.jsonl").read_text().splitlines()
            self.assertEqual(len(lines),2)
            self.assertEqual(json.loads(lines[0])["schema"],
                             "mass.f124cn.append-only-original-OS-measurement.v1")
    def test_no_partial_roster_claims(self):
        with self.assertRaises(ValueError):observer.review([],[])
    def test_source_birth_not_triggered_by_resource_module(self):
        self.assertFalse(hasattr(observer,"task"))
        self.assertFalse(hasattr(observer,"generate"))
        self.assertFalse(hasattr(observer,"birth"))

if __name__=="__main__":unittest.main()
