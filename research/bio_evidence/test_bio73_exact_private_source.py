"""Offline-only checks for the exact, private BIO-73 ENV0 source read.

No private token, original source bytes, external network or science execution.
"""
import base64
import hashlib
import io
import json
import unittest
import urllib.parse

from private_github import (
    GitHubBIO, BIO73_ENV0_BLOB, BIO73_ENV0_COMMIT, BIO73_ENV0_PATH
)

TOKEN = "offline-stub-token"

class Response:
    def __init__(self, body):
        self._io = io.BytesIO(body)
    def __enter__(self): return self
    def __exit__(self, *args): self._io.close()
    def read(self, amount=-1): return self._io.read(amount)
    def getcode(self): return 200

def git_blob(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\x00" + data).hexdigest()

def payload(data, sha=None):
    return {"type":"file", "encoding":"base64",
            "size":len(data), "sha":sha or git_blob(data),
            "content":base64.b64encode(data).decode("ascii")}

class BIO73FrozenReadTest(unittest.TestCase):
    def test_verifier_accepts_synthetic_exact_blob(self):
        fake=b"offline fixture: not upstream scientific source\n"
        out=GitHubBIO._verify_frozen_file(payload(fake),git_blob(fake),16384)
        self.assertEqual(fake,out)

    def test_refuse_forged_claimed_blob(self):
        fake=b"forged simulation\n"
        with self.assertRaisesRegex(ValueError,"FROZEN_SOURCE_GIT_BLOB_SHA"):
            GitHubBIO._verify_frozen_file(payload(fake, "1"*40),"1"*40,16384)

    def test_refuse_wrong_metadata_or_size(self):
        fake=b"offline fixture\n"
        good=payload(fake)
        for bad in (
            {**good,"type":"dir"},
            {**good,"size":len(fake)+1},
            {**good,"size":True},
            {**good,"encoding":"utf-8"},
            {**good,"content":"?"},
        ):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    GitHubBIO._verify_frozen_file(bad,git_blob(fake),16384)

    def test_exact_commit_route_and_no_main_or_arbitrary_path(self):
        calls=[]
        def opener(req,timeout):
            calls.append(req)
            self.assertEqual("GET",req.get_method())
            self.assertEqual("api.github.com",urllib.parse.urlparse(req.full_url).hostname)
            self.assertEqual("Bearer "+TOKEN,req.get_header("Authorization"))
            u=urllib.parse.urlparse(req.full_url)
            self.assertEqual("/repos/spoonman136668-ai/Mind-Palace/contents/"+BIO73_ENV0_PATH,u.path)
            self.assertEqual({"ref":[BIO73_ENV0_COMMIT]},urllib.parse.parse_qs(u.query))
            # Correct claimed SHA, deliberately wrong original bytes: must deny.
            bad=payload(b"not the frozen original source\n",BIO73_ENV0_BLOB)
            return Response(json.dumps(bad).encode("utf-8"))
        reader=GitHubBIO(TOKEN,opener=opener)
        with self.assertRaisesRegex(ValueError,"FROZEN_SOURCE_GIT_BLOB_SHA"):
            reader.read_frozen_bio73_env0()
        self.assertEqual(1,len(calls))
        # Existing historical evidence read remains unpinned and unavailable
        # unless the historical caller separately resolves and checks main.
        with self.assertRaisesRegex(ValueError,"NOT_PINNED"):
            reader.read_at("docs/RESEARCH_EVIDENCE_CATALOG.json",32768)
        self.assertEqual(1,len(calls))

    def test_no_unpinned_runtime_permission_from_result(self):
        self.assertRegex(BIO73_ENV0_BLOB,r"^[0-9a-f]{40}$")
        self.assertRegex(BIO73_ENV0_COMMIT,r"^[0-9a-f]{40}$")
        self.assertTrue(BIO73_ENV0_PATH.endswith("/bio73_source_preflight.py"))
        reader=GitHubBIO(TOKEN,opener=lambda req,timeout: Response(b"{}"))
        with self.assertRaisesRegex(ValueError,"FROZEN_SOURCE_FORMAT"):
            reader.read_frozen_bio73_env0()

if __name__=="__main__":
    unittest.main()
