"""G103 exact adaptive state sharing with conventional controls."""
import unittest
from research.cpu_g97.g103_block_sharing import (
    BlockError, costs, pack, split_adaptive, split_fixed, unpack)


class G103Blocks(unittest.TestCase):
    def test_exact_reconstruction_and_accounting_for_both_modes(self):
        states=[bytes(range(256))*10, bytes(range(256))*10,
                bytes(reversed(range(256)))*10]
        for mode in ("fixed","adaptive"):
            b=pack(states,mode=mode)
            self.assertEqual([unpack(b,i) for i in range(3)],states)
            c=costs(b,states)
            self.assertEqual(c["shared_total_modeled_bytes"],
                             c["physical_payload_bytes"]+c["metadata_modeled_bytes"])
            self.assertEqual(c["raw_bytes"],sum(len(s) for s in states))
            self.assertTrue(c["unique_blocks"]<=c["references"])

    def test_distinct_data_must_not_alias_and_hash_collision_fails(self):
        with self.assertRaisesRegex(BlockError,"DIGEST_COLLISION"):
            pack([b"a"*120,b"b"*120],digest_fn=lambda _: b"0"*32)
        b=pack([b"a"*120,b"b"*120])
        self.assertEqual(unpack(b,1),b"b"*120)

    def test_pool_mutation_or_missing_block_rejected(self):
        b=pack([b"x"*1000,b"x"*1000])
        first=next(iter(b["pool"]))
        b["pool"][first]=b"z"*len(b["pool"][first])
        with self.assertRaisesRegex(BlockError,"POOL_IDENTITY"):
            unpack(b,0)
        b=pack([b"x"*1000,b"x"*1000])
        del b["pool"][next(iter(b["pool"]))]
        with self.assertRaisesRegex(BlockError,"POOL_IDENTITY"):
            unpack(b,1)

    def test_manifest_identity_guard(self):
        b=pack([b"a"*500,b"b"*500])
        manifests=list(b["manifests"])
        manifests[0]=manifests[1]
        b["manifests"]=tuple(manifests)
        with self.assertRaisesRegex(BlockError,"RECONSTRUCTION_IDENTITY"):
            unpack(b,0)

    def test_no_false_win_on_incompressible_content(self):
        states=[bytes(((x*73 + i*111) % 256) for x in range(4096))
                for i in range(4)]
        for mode in ("fixed","adaptive"):
            b=pack(states,mode=mode)
            c=costs(b,states)
            self.assertEqual(c["beats_both_controls"],
                             c["shared_total_modeled_bytes"] <
                             min(c["raw_bytes"],c["independent_zlib_bytes"]))

    def test_malformed_states_and_configs(self):
        for state in (b"", "not bytes", bytearray(b"x")):
            with self.assertRaisesRegex(BlockError,"INVALID_STATE"):
                pack([b"x",state])
        with self.assertRaisesRegex(BlockError,"STATES_REQUIRED"):
            pack([b"x"])
        with self.assertRaisesRegex(BlockError,"INVALID_MODE"):
            pack([b"a",b"b"],mode="unknown")
        with self.assertRaisesRegex(BlockError,"CHUNK_CONFIG"):
            split_adaptive(b"a"*200,average=255)
        with self.assertRaisesRegex(BlockError,"FIXED_SIZE"):
            split_fixed(b"abc",size=0)

    def test_deterministic_chunking_and_roundtrip(self):
        raw=bytes(range(256))*10
        self.assertEqual(split_adaptive(raw),split_adaptive(raw))
        self.assertEqual(b"".join(split_adaptive(raw)),raw)
        self.assertEqual(b"".join(split_fixed(raw)),raw)


if __name__=="__main__":
    unittest.main()
