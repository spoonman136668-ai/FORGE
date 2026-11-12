"""F99 regression tests: no fabricated archive, no training grant."""
import io
import json
import pathlib
import sys
import unittest
import zipfile
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
from f99_archive_extract import (
 SCHEMA,PINS,Blocked,archive_bytes,extract,parse_json,
 wingless,yggdrasil,rescore,audit_scores
)
SOURCE="1"*40
def mkzip(name,payload):
 stream=io.BytesIO()
 with zipfile.ZipFile(stream,"w",zipfile.ZIP_DEFLATED) as zipf:
  zipf.writestr(name,payload)
 return stream.getvalue()
class F99(unittest.TestCase):
 def test_no_missing_or_forged_source(self):
  for raw in (b"",b"not zip",mkzip(PINS["Wingless"]["member"],b'{"schema":"fake"}')):
   with self.assertRaises(Blocked):
    archive_bytes(raw,"Wingless")
  with self.assertRaises(Blocked):
   extract({"Wingless":b""},SOURCE)
  for source in ("A"*40,"",None,"f"):
   with self.assertRaises(Blocked):
    extract({"Wingless":b"", "Yggdrasil":b""},source)
 def test_zip_payload_names_not_sufficient_without_exact_digest(self):
  for name in (PINS["Wingless"]["member"],"../../escape.json",PINS["Yggdrasil"]["member"]):
   z=mkzip(name,b'{"ok":true}')
   with self.assertRaises(Blocked):
    archive_bytes(z,"Wingless")
 def test_duplicate_nonfinite_and_bombed_json_denied(self):
  for text in (b'{"a":1,"a":2}',b'{"a":Infinity}',b'[]',b'{"a":1}'*160000):
   with self.assertRaises(Blocked):
    parse_json(text)
 def test_rescoring_detects_relabelled_outcomes(self):
  rows=[{"truth":[False,True],"models":{"blind":[True,True],"oracle":[False,True]}}]*4
  report=rescore(rows,{"blind","oracle"},"models")
  self.assertEqual(report["blind"]["paired_correct"],0)
  self.assertEqual(report["oracle"]["paired_correct"],4)
  audit_scores(report,report)
  altered=json.loads(json.dumps(report))
  altered["blind"]["paired_correct"]=4
  with self.assertRaises(Blocked):
   audit_scores(report,altered)
 def test_dev_not_auto_approved_as_training(self):
  rows=[{"truth":[True,False],"predictions":{"blind":[True,True],"oracle":[True,False]}}]*3
  result=rescore(rows,{"blind","oracle"},"predictions")
  self.assertEqual(result["blind"]["negative_false_positives"],3)
  self.assertEqual(result["oracle"]["paired_correct"],3)
  with self.assertRaises(Blocked):
   wingless({"stage":"DEVELOPMENT_ONLY","rows":[],"sealed_first_use":False})
  with self.assertRaises(Blocked):
   yggdrasil({"stage":"DEVELOPMENT_ONLY","rows":[],"sealed_first_use":False})
 def test_real_source_cannot_be_assumed_from_pinned_string(self):
  self.assertEqual(PINS["Wingless"]["rows"],96)
  self.assertEqual(PINS["Yggdrasil"]["rows"],192)
  self.assertNotEqual(PINS["Wingless"]["commit"],PINS["Yggdrasil"]["commit"])
  self.assertTrue(SCHEMA.startswith("forge.autonomy.f99."))
if __name__=="__main__":
 unittest.main()
