"""Adversarial F138-C2 exact archived provider-source reconstruction."""
import copy
import hashlib
import json
from pathlib import Path
import unittest

import f138_archive_c2 as c

class ArchiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.members = c.load_bundle()

    def check_fail(self, altered):
        with self.assertRaises(c.InvalidCustody):
            c.verify(altered)

    def edited_json(self, filename, edit):
        obj = json.loads(self.members[filename])
        edit(obj)
        mutated = dict(self.members)
        mutated[filename] = (json.dumps(obj,sort_keys=True,separators=(",",":"))
                             + "\n").encode("ascii")
        return mutated

    def test_complete_original_member_set_source_history_and_negative(self):
        r=c.verify(self.members)
        self.assertEqual(r["archive_member_count"],24)
        self.assertEqual(r["provider_integrated_history_count"],45)
        self.assertEqual(r["provider_controller_history_count"],43)
        self.assertEqual(r["controller_source_decisions"],4)
        self.assertEqual(r["os_lineage_reports"],8)
        self.assertFalse(r["original_github_zip_envelope_preserved"])
        self.assertTrue(r["all_original_archive_member_bytes_preserved"])
        self.assertFalse(r["permanent_main_custody_qualified"])
        self.assertEqual(r["f138_operational_verdict"],"PENDING")
        self.assertFalse(r["scientific_first_use_authorized"])

    def test_all_receipts_have_original_sha256(self):
        for name in ("snapshot.json","decision.json"):
            self.assertEqual(self.members[name+".sha256"],(
                hashlib.sha256(self.members[name]).hexdigest() +
                "  "+name+"\n").encode())
        for rid in c.CHILDREN:
            for osname in c.OS:
                name=f"{rid}/{osname}/f138-lineage.json"
                expected=(hashlib.sha256(self.members[name]).hexdigest() +
                          "  f138-lineage.json\n").encode()
                self.assertEqual(self.members[name[:-4]+"sha256"],expected)

    def test_reject_modified_snapshot(self):
        self.check_fail(self.edited_json("snapshot.json",lambda d:d.update(
            source_sha="0"*40)))

    def test_reject_modified_decision_or_false_promotion(self):
        self.check_fail(self.edited_json("decision.json",lambda d:d.update(
            verdict="PASS",genuine_scheduled_count=1)))

    def test_reject_missing_member(self):
        mutated=dict(self.members)
        del mutated["39123993228/decision.json"]
        self.check_fail(mutated)

    def test_reject_changed_parent(self):
        path="39119993456/decision.json"
        self.check_fail(self.edited_json(path,lambda d:d.update(
            controller_run_id=39121294863)))

    def test_reject_duplicate_windows_nonce(self):
        path="39123993228/decision.json"
        self.check_fail(self.edited_json(path,lambda d:d.update(
            wake_nonce="945cdca24cfb47959d49630666a946f0")))

    def test_reject_child_origin_masquerading_as_schedule(self):
        path="39120007064/ubuntu-latest/f138-lineage.json"
        self.check_fail(self.edited_json(path,lambda d:d.update(
            genuine_integrated_schedule=True,origin="schedule")))

    def test_reject_cross_platform_receipt_tamper(self):
        mutated=dict(self.members)
        name="39124007071/windows-latest/f138-lineage.sha256"
        mutated[name]=b"0"*64+b"  f138-lineage.json\n"
        self.check_fail(mutated)

    def test_reject_cross_platform_lineage_drift(self):
        path="39121310943/windows-latest/f138-lineage.json"
        self.check_fail(self.edited_json(path,lambda d:d.update(
            optimizer_promotions=1)))

    def test_reject_science_authority_forgery(self):
        path="39122657120/ubuntu-latest/f138-lineage.json"
        self.check_fail(self.edited_json(path,lambda d:d.update(
            scientific_first_use_authorized=True)))

    def test_unpack_reject_wrong_magic_and_truncation(self):
        with self.assertRaises(c.InvalidCustody):
            c.unpack(b"FORGED!!!")
        with self.assertRaises(c.InvalidCustody):
            c.unpack(c.MAGIC+b"\x00\x00\x00\x18")

    def test_original_zip_digest_is_not_a_signature(self):
        self.assertRegex(c.ORIGINAL_ZIP_SHA256,r"^[a-f0-9]{64}$")
        self.assertEqual(c.PROVIDER_ARTIFACT,12135755671)
        self.assertFalse(c.verify(self.members)["permanent_main_custody_qualified"])

    def test_retained_snapshot_contains_skip_and_no_false_cron(self):
        s=json.loads(self.members["snapshot.json"])
        self.assertTrue(any(row["conclusion"]=="skipped" for row in
                            s["controller_index"]["workflow_runs"]))
        d=json.loads(self.members["decision.json"])
        self.assertEqual(d["genuine_scheduled_count"],0)

    def test_no_network_dispatch_git_mutation_or_codex_execution(self):
        src=(Path(__file__).resolve().parent/"f138_archive_c2.py").read_text()
        for forbidden in ("subprocess.", "requests.", "gh api",
                          "workflow_dispatch(", "os.system(",
                          "github-token.dpapi"):
            self.assertNotIn(forbidden,src)
        self.assertIn("scientific_first_use_authorized",src)

if __name__=="__main__":
    unittest.main()
