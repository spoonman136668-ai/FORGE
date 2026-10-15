"""R19 intake-negative tests: synthetic fixtures never qualify as research."""
import json,hashlib,pathlib,tempfile,unittest
import r19_intake as r

class R19IntakeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=pathlib.Path(self.tmp.name)
        self.entries=[]
        self.payloads={}
        for lane,short in (("Wingless","W"),("Yggdrasil","Y")):
            for i in range(3):
                num=i+1+(0 if short=="W" else 3)
                data=("SYNTHETIC_NOT_AUTHENTIC_"+str(num)).encode()
                sha=hashlib.sha256(data).hexdigest()
                e={"lane":lane,"experiment":short+str(num),"repository":"spoonman136668-ai/"+lane,
                   "run_id":100+num,"head_sha":"a"*40,"workflow_path":".github/workflows/qualify-unit.yml",
                   "artifact_id":200+num,"artifact_name":"fixture-"+str(num),"archive_sha256":sha}
                self.entries.append(e)
                self.payloads[e["run_id"]]=data
                (self.root/(str(e["run_id"])+".zip")).write_bytes(data)
        self.manifest=json.dumps({"schema":"forge.research-archive.frozen-cohort.v1",
                         "entries":self.entries},separators=(",",":")).encode()+b"\n"
        self.observation=self.make_observation()

    def tearDown(self):self.tmp.cleanup()

    def make_observation(self):
        return json.dumps({"schema":"forge.research-archive.original-byte-inventory.v1",
          "mode":"ORIGINAL_ARCHIVE_BYTE_PRESERVATION_NOT_SCIENTIFIC_CUSTODY",
          "manifest_sha256":r.sha(self.manifest),"archive_count":6,
          "wingless_count":3,"yggdrasil_count":3,
          "original_execution_authorized":False,"complete_ckb_custody":False,
          "scientific_accepted":False,"accepted_ref_mutation":False,
          "observations":[{"lane":e["lane"],"experiment":e["experiment"],
            "original_run_id":e["run_id"],"original_head_sha":e["head_sha"],
            "artifact_id":e["artifact_id"],"archive_sha256":e["archive_sha256"],
            "archival_integrity_verified":True,
            "scientific_classification":"UNQUALIFIED_ORIGINAL_EVIDENCE_PRESERVED",
            "preregistration_verified":False,"first_use_reconciled":False,
            "scientific_accepted":False} for e in self.entries]},
            separators=(",",":")).encode()

    def test_synthetic_metadata_generation_has_no_authority(self):
        s=r.statements(self.manifest,self.observation,self.root)
        self.assertEqual(len(s),18)
        self.assertEqual(sum("INSERT INTO forge_research_seals" in x for x in s),6)
        self.assertTrue(all(x.startswith("INSERT INTO forge_research_") for x in s))
        self.assertFalse(any("scientific_accepted" in x or "UPDATE" in x for x in s))
    def test_real_zip_bytes_cannot_drift(self):
        (self.root/"101.zip").write_bytes(b"tampered")
        with self.assertRaisesRegex(r.IntakeBlocked,"REAL_ZIP_MISSING_OR_HASH_DRIFT"):
            r.statements(self.manifest,self.observation,self.root)
    def test_false_first_use_flag_rejected(self):
        o=json.loads(self.observation);o["observations"][0]["first_use_reconciled"]=True
        with self.assertRaisesRegex(r.IntakeBlocked,"OBSERVATION_AUTHORITY_DRIFT"):
            r.statements(self.manifest,json.dumps(o).encode(),self.root)
    def test_archive_duplicate_blocked(self):
        m=json.loads(self.manifest);m["entries"][1]["experiment"]=m["entries"][0]["experiment"]
        with self.assertRaisesRegex(r.IntakeBlocked,"DUPLICATE_EXPERIMENT"):
            r.statements(json.dumps(m).encode(),self.observation,self.root)
    def test_cross_lane_source_rejected(self):
        m=json.loads(self.manifest);m["entries"][0]["repository"]="spoonman136668-ai/Yggdrasil"
        with self.assertRaisesRegex(r.IntakeBlocked,"CROSS_LANE_IDENTITY"):
            r.statements(json.dumps(m).encode(),self.observation,self.root)
    def test_preparation_is_exclusive(self):
        manifest=self.root/"manifest.json";manifest.write_bytes(self.manifest)
        (self.root/"observation.json").write_bytes(self.observation)
        target=self.root/"new.sql"
        r.prepare(manifest,self.root,target)
        self.assertTrue(target.exists())
        with self.assertRaisesRegex(r.IntakeBlocked,"PRIVATE_NEW_SQL_PATH_REQUIRED"):
            r.prepare(manifest,self.root,target)
    def test_unverified_go_observation_rejected(self):
        o=json.loads(self.observation);o["observations"][1]["archival_integrity_verified"]=False
        with self.assertRaisesRegex(r.IntakeBlocked,"OBSERVATION_SOURCE_DRIFT"):
            r.statements(self.manifest,json.dumps(o).encode(),self.root)
    def test_empty_zip_rejected(self):
        (self.root/"101.zip").write_bytes(b"")
        with self.assertRaisesRegex(r.IntakeBlocked,"REAL_ZIP_MISSING_OR_HASH_DRIFT"):
            r.statements(self.manifest,self.observation,self.root)
if __name__=="__main__":unittest.main()
