"""F114-O strict source custody checks, synthetic-only witness never science."""
from pathlib import Path
import hashlib
import os
import tempfile
import unittest

import f114o_archive_custody_intake as f

class ArchiveCustodyTests(unittest.TestCase):
    def setUp(self):
        self.dir=tempfile.TemporaryDirectory(prefix="f114o-test-")
        self.addCleanup(self.dir.cleanup)
        self.source=Path(self.dir.name)/"synthetic.bin"
        self.source.write_bytes(f.FIXTURE)
        self.manifest=f.witness_manifest(f.FIXTURE)

    def test_valid_exact_synthetic_receipt_never_qualifies_original(self):
        x=f.verify_synthetic_fixture(self.source,self.manifest)
        self.assertEqual(x["status"],f.SYNTH_STATUS)
        self.assertEqual(x["fixture_archive_bytes_checked"],len(f.FIXTURE))
        self.assertFalse(x["genuine_external_source_witness"])
        self.assertFalse(x["publisher_original_archive_authenticated"])
        self.assertFalse(x["original_freebase_graph_admitted"])

    def test_any_mismatched_source_or_checksum_denied(self):
        import copy
        for key,new in [
            ("precommitted_archive_sha256","0"*64),
            ("precommitted_archive_bytes",len(f.FIXTURE)+1),
            ("publisher_git_commit","0"*40),
            ("publisher_readme_git_blob","0"*40),
            ("publisher_graph_url","https://example.com/freebase.zip"),
            ("publisher_repository","random/FreebaseQA"),
            ("source_type","original_freebaseqa_graph"),
            ("source_authority","ORIGINAL_FREEBASEQA"),
            ("witness_principal","synthetic_executor_B"),
            ("executor_principal","synthetic_witness_A"),
        ]:
            m=copy.deepcopy(self.manifest)
            m[key]=new
            if key=="executor_principal":
                m["witness_principal"]="synthetic_witness_A"
                m["executor_principal"]="synthetic_witness_A"
            if key=="witness_principal":
                m["witness_principal"]="synthetic_executor_B"
            with self.assertRaises(f.Denied,key):
                f.verify_synthetic_fixture(self.source,m)

    def test_missing_truncated_modified_and_overlong_file_denied(self):
        m=f.witness_manifest(f.FIXTURE)
        self.source.write_bytes(f.FIXTURE[:-1])
        with self.assertRaises(f.Denied):f.verify_synthetic_fixture(self.source,m)
        self.source.write_bytes(f.FIXTURE+b"x")
        with self.assertRaises(f.Denied):f.verify_synthetic_fixture(self.source,m)
        self.source.write_bytes(b"X"*len(f.FIXTURE))
        with self.assertRaises(f.Denied):f.verify_synthetic_fixture(self.source,m)
        self.source.unlink()
        with self.assertRaises(f.Denied):f.verify_synthetic_fixture(self.source,m)
        self.source.write_bytes(b"x"*(f.MAX_SYNTHETIC_BYTES+1))
        m=f.witness_manifest(self.source.read_bytes())
        with self.assertRaises(f.Denied):f.verify_synthetic_fixture(self.source,m)

    def test_nonregular_and_symlink_inputs_refused(self):
        with self.assertRaises(f.Denied):
            f.verify_synthetic_fixture(Path(self.dir.name),self.manifest)
        target=Path(self.dir.name)/"link.bin"
        try:target.symlink_to(self.source)
        except (OSError,NotImplementedError):return
        with self.assertRaises(f.Denied):
            f.verify_synthetic_fixture(target,self.manifest)

    def test_original_freebase_never_qualified_by_forged_manifest(self):
        synthetic_valid=f.witness_manifest(f.FIXTURE)
        complete_looking={
            **synthetic_valid,
            "source_type":"original_freebaseqa_graph",
            "source_authority":"ORIGINAL_FREEBASEQA",
            "archive_sha256":"0"*64,
            "archive_size":2345678900,
            "independent_signer":"someone_else",
            "verified_edge_count":182000000,
        }
        for m in (None,{},synthetic_valid,complete_looking):
            with self.assertRaises(f.Denied):
                f.verify_original_archive(self.source,m)
        status=f.original_custody_status()
        self.assertEqual(status["status"],f.ORIGINAL_STATUS)
        self.assertFalse(status["independent_archive_witness_present"])
        self.assertFalse(status["original_edge_orientation_verified"])
        self.assertEqual(status["original_graph_query_count"],0)

    def test_deterministic_source_only_aggregate(self):
        a=f.audit()
        b=f.audit()
        self.assertEqual(a,b)
        self.assertFalse(a["original_freebase_archive_read_or_downloaded"])
        self.assertFalse(a["reserved_train_dev_eval_json_read"])
        self.assertFalse(a["independent_scientific_firstuse"])
        self.assertEqual(a["real_graph_queries"],0)
        self.assertEqual(a["real_qa_answers_compared"],0)

if __name__=="__main__":unittest.main()
