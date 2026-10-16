import io,sys,unittest,zipfile,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import f84_wingless_fit as m
class Tests(unittest.TestCase):
 def test_bad_run_denied(self):
  with self.assertRaisesRegex(m.Denied,"RUN_IDENTITY"):m.audit({"id":m.RUN}, {}, b"")
 def test_bad_artifact_denied(self):
  run={"id":m.RUN,"head_sha":m.SHA,"run_attempt":1,"event":"push","path":".github/workflows/w-f61b-once-fit-source-20261016.yml","status":"completed","conclusion":"success"}
  with self.assertRaisesRegex(m.Denied,"ARTIFACT_IDENTITY"):m.audit(run,{},b"")
 def test_invented_archive_denied(self):
  run={"id":m.RUN,"head_sha":m.SHA,"run_attempt":1,"event":"push","path":".github/workflows/w-f61b-once-fit-source-20261016.yml","status":"completed","conclusion":"success"}
  meta={"id":m.ART,"name":"wingless-f61b-once-fit-receipts","expired":False,"digest":m.DIGEST,"workflow_run":{"head_sha":m.SHA,"id":m.RUN}}
  with self.assertRaisesRegex(m.Denied,"ARCHIVE_DIGEST"):m.audit(run,meta,b"invented")
