"""Offline negative enforcement for physical D1 original byte restore."""
import hashlib
import sqlite3
import unittest

from restore import IndependentPin, UnqualifiedArchive, verify_original
import test_schema as _schema

class RestoreTest(unittest.TestCase):
    def setUp(self):
        self.fixture=_schema.D1RetentionTests()
        self.fixture.setUp()
        self.db=self.fixture.db
        self.payload=b"THIS_IS_NOT_REAL_SCIENCE" * 21
        self.sha=self.fixture.store(payload=self.payload)
        self.pin=IndependentPin(
            lane="Wingless",experiment="W-ARCH-001",
            repository="spoonman136668-ai/Wingless",run_id=111,artifact_id=333,
            source_sha="a"*40,frozen_manifest_sha256="b"*64,archive_sha256=self.sha
        )

    def tearDown(self):
        self.fixture.tearDown()

    def seal(self):
        self.fixture.seal(self.sha,len(self.payload))

    def test_exact_restore_is_still_not_scientific_custody(self):
        self.fixture.fill(self.sha,self.payload)
        self.seal()
        r=verify_original(self.db,self.pin)
        self.assertEqual(r.original_length,len(self.payload))
        self.assertTrue(r.chunk_digests_verified and r.assembled_original_digest_verified)
        self.assertFalse(r.independent_source_custody_verified)
        self.assertFalse(r.first_use_reconciled)
        self.assertFalse(r.scientific_accepted)
        self.assertFalse(r.dispatch_authorized)

    def test_no_seal_cannot_be_restored(self):
        self.fixture.fill(self.sha,self.payload)
        with self.assertRaises(UnqualifiedArchive):verify_original(self.db,self.pin)

    def test_forged_chunk_digest_rejected_despite_structural_seal(self):
        half=(len(self.payload)+1)//2
        for i,b in enumerate((self.payload[:half],self.payload[half:])):
            self.db.execute(
                "INSERT INTO forge_research_chunks "
                "(archive_sha256,chunk_index,chunk_sha256,chunk_bytes) VALUES (?,?,?,?)",
                (self.sha,i,"f"*64,b)
            )
        self.seal()
        with self.assertRaisesRegex(UnqualifiedArchive,"CHUNK_CORRUPTION"):
            verify_original(self.db,self.pin)

    def test_forged_full_original_rejected_despite_self_consistent_chunk_hash(self):
        corrupt=bytearray(self.payload)
        corrupt[0]^=1
        self.fixture.fill(self.sha,bytes(corrupt))
        self.seal()
        with self.assertRaisesRegex(UnqualifiedArchive,"ORIGINAL_DIGEST_MISMATCH"):
            verify_original(self.db,self.pin)

    def test_wrong_experiment_and_source_pins_rejected(self):
        self.fixture.fill(self.sha,self.payload)
        self.seal()
        for wrong in (
            IndependentPin("Wingless","W-SWAPPED",self.pin.repository,111,333,
                "a"*40,"b"*64,self.sha),
            IndependentPin("Wingless","W-ARCH-001",self.pin.repository,111,333,
                "f"*40,"b"*64,self.sha),
            IndependentPin("Yggdrasil","W-ARCH-001","spoonman136668-ai/Yggdrasil",
                111,333,"a"*40,"b"*64,self.sha),
        ):
            with self.assertRaises(UnqualifiedArchive):verify_original(self.db,wrong)

    def test_seal_cannot_pretend_independent_signature(self):
        self.fixture.fill(self.sha,self.payload)
        self.seal()
        review=verify_original(self.db,self.pin)
        self.assertFalse(review.independent_source_custody_verified)

if __name__=="__main__":
    unittest.main()
