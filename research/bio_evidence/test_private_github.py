import base64
import hashlib
import io
import json
import unittest
import urllib.parse

from private_github import GitHubBIO
from shared_evidence_preflight import lookup

PIN = "a" * 40
TOKEN = "fixture-read-only-token"
CATALOG = "docs/RESEARCH_EVIDENCE_CATALOG.json"
INDEX = "archive/research/bio/2026-10-23/findings.json"
SOURCE = "archive/research/bio/2026-10-23/original_reports/BIO01_report.md"

class Response:
    def __init__(self, raw, code=200):
        self._reader = io.BytesIO(raw)
        self._code = code
    def __enter__(self): return self
    def __exit__(self, *args): self._reader.close()
    def getcode(self): return self._code
    def read(self, size=-1): return self._reader.read(size)

class PrivateBIOTest(unittest.TestCase):
    def setUp(self):
        self.calls=[]
        self.original=b"Original source: memory replay versus uniform rehearsal.\n"
        digest=hashlib.sha256(self.original).hexdigest()
        self.catalog=json.dumps({
            "schema":"mind-palace.research-evidence-catalog.v1",
            "authority":"ADVISORY_HISTORICAL_ONLY",
            "research_archives":[{
                "program":"BIO",
                "index":INDEX,
                "scientific_acceptance":"NOT_AUTHENTICATED_OR_ESTABLISHED",
                "scientific_finding_count":1}]
        }).encode()
        self.index=json.dumps({
            "schema":"bio.findings.repo.historical.v1",
            "status":"ADVISORY_HISTORICAL_NOT_ACCEPTED",
            "record_count":1,
            "findings":[{
                "finding_id":"BIOF-001","experiment_id":"BIO-01",
                "claim":"Memory replay improved retention",
                "control_comparison":"Uniform replay stronger than priority",
                "limitations":"synthetic task only",
                "gate_verdict":"SCIENTIFIC_FAIL",
                "source_repo_path":SOURCE,
                "source_sha256":digest,
                "evidence_status":"HISTORICAL_PROVISIONAL_ONLY",
                "wingless_yggdrasil_integration":"NOT_AUTHORIZED"
            }]
        }).encode()
        self.docs={CATALOG:self.catalog, INDEX:self.index, SOURCE:self.original}

    def opener(self, req, timeout):
        self.calls.append(req)
        self.assertEqual("GET",req.get_method())
        self.assertEqual("api.github.com",urllib.parse.urlparse(req.full_url).hostname)
        self.assertEqual("Bearer "+TOKEN,req.get_header("Authorization"))
        path=urllib.parse.urlparse(req.full_url).path
        if path.endswith("/commits/main"):
            return Response(json.dumps({"sha":PIN}).encode())
        self.assertEqual(PIN,urllib.parse.parse_qs(urllib.parse.urlparse(req.full_url).query).get("ref")[0])
        rel=path.split("/contents/",1)[1]
        self.assertIn(rel,self.docs)
        raw=self.docs[rel]
        declared=hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\x00"+raw).hexdigest()
        payload={"type":"file","encoding":"base64","content":base64.b64encode(raw).decode(),
                 "size":len(raw),"sha":declared}
        return Response(json.dumps(payload).encode())

    def test_private_end_to_end_advisory_lookup(self):
        reader=GitHubBIO(TOKEN, opener=self.opener)
        pin=reader.resolve_main()
        output=lookup(None,pin,"memory replay",5,source_read=reader.read_at)
        self.assertEqual(1,len(output["retrieved"]))
        self.assertEqual("SCIENTIFIC_FAIL",output["retrieved"][0]["verdict"])
        self.assertFalse(output["scientific_acceptance"])
        self.assertEqual(4,len(self.calls))
        self.assertTrue(all(req.get_method()=="GET" for req in self.calls))

    def test_no_unpinned_or_arbitrary_reads(self):
        reader=GitHubBIO(TOKEN,opener=self.opener)
        with self.assertRaisesRegex(ValueError,"NOT_PINNED"):
            reader.read_at(CATALOG,32768)
        reader.resolve_main()
        with self.assertRaisesRegex(ValueError,"PATH_DENIED"):
            reader.read_at("../secrets",100)
        self.assertEqual(1,len(self.calls))

    def test_source_blob_identity_is_mandatory(self):
        original=self.opener
        def corrupted(req,timeout):
            response=original(req,timeout)
            if "/contents/" in req.full_url:
                raw=json.loads(response.read())
                raw["sha"]="0"*40
                return Response(json.dumps(raw).encode())
            return response
        reader=GitHubBIO(TOKEN,opener=corrupted)
        reader.resolve_main()
        with self.assertRaisesRegex(ValueError,"GIT_BLOB_SHA"):
            reader.read_at(CATALOG,32768)

    def test_token_and_pin_are_fail_closed(self):
        for token in (""," a ","unsafe\n"):
            with self.assertRaises(ValueError): GitHubBIO(token,opener=self.opener)
        reader=GitHubBIO(TOKEN,opener=lambda req,timeout:Response(b'{"sha":"main"}'))
        with self.assertRaisesRegex(ValueError,"PIN_UNVERIFIED"):reader.resolve_main()

    def test_no_match_makes_no_original_source_request(self):
        reader=GitHubBIO(TOKEN,opener=self.opener)
        out=lookup(None,reader.resolve_main(),"astronomy",5,source_read=reader.read_at)
        self.assertEqual([],out["retrieved"])
        self.assertEqual(3,len(self.calls))

if __name__=="__main__": unittest.main()
