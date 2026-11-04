"""G102 model-free exact-state reconstruction and negative controls."""
import os
import unittest
import zlib
from research.cpu_g97.g102_xor_state import (
    ReconstructionError, accounting, decode, encode, MAX_BYTES)


class G102Tests(unittest.TestCase):
    def test_byte_exact_round_trip_with_shared_reference(self):
        base = bytes(range(256)) * 12
        target = bytearray(base)
        target[1] ^= 17
        target[2049] ^= 99
        pkt = encode(base, bytes(target))
        restored = decode(base, pkt)
        self.assertEqual(restored, bytes(target))
        self.assertIsNot(restored, target)
        stats = accounting(base, [bytes(target), base], [pkt, encode(base, base)])
        self.assertEqual(stats["targets"], 2)
        self.assertEqual(stats["raw_bytes"], 2 * len(base))
        self.assertEqual(stats["residual_with_base_bytes"],
                         len(base) + len(pkt["payload"]) +
                         len(encode(base, base)["payload"]))

    def test_random_and_independent_compression_controls_not_assumed_wins(self):
        base = bytes(range(256)) * 8
        independent = bytes((i * 37 + 11) % 256 for i in range(len(base)))
        packets = [encode(base, independent), encode(base, base)]
        stats = accounting(base, [independent, base], packets)
        self.assertEqual(stats["standalone_zlib_bytes"],
                         len(zlib.compress(independent, 6)) +
                         len(zlib.compress(base, 6)))
        self.assertEqual(stats["wins_both_storage_controls"],
                         stats["residual_with_base_bytes"] <
                         min(stats["raw_bytes"], stats["standalone_zlib_bytes"]))

    def test_wrong_base_is_rejected_without_fallback(self):
        base = b"a" * 2000
        packet = encode(base, b"a" * 1999 + b"b")
        with self.assertRaisesRegex(ReconstructionError, "BASE_IDENTITY"):
            decode(b"b" * 2000, packet)

    def test_target_integrity_corruption_is_fatal(self):
        base = b"x" * 1000
        pkt = encode(base, b"y" * 1000)
        pkt["target_sha256"] = "0" * 64
        with self.assertRaisesRegex(ReconstructionError, "TARGET_INTEGRITY"):
            decode(base, pkt)

    def test_truncated_and_trailing_payload_rejected(self):
        base = b"r" * 1000
        pkt = encode(base, b"s" * 1000)
        pkt["payload"] += b"garbage"
        with self.assertRaisesRegex(ReconstructionError, "TRAILING"):
            decode(base, pkt)
        pkt = encode(base, b"s" * 1000)
        pkt["payload"] = pkt["payload"][:-2]
        with self.assertRaises(ReconstructionError):
            decode(base, pkt)

    def test_oversize_decompress_is_rejected(self):
        base = b"a" * 100
        pkt = encode(base, b"b" * 100)
        pkt["payload"] = zlib.compress(b"z" * 10000)
        with self.assertRaisesRegex(ReconstructionError, "DELTA_LENGTH"):
            decode(base, pkt)

    def test_invalid_and_oversized_inputs_fail_closed(self):
        for a,b in ((b"", b""), (b"123", b"12"), ("abc", b"abc")):
            with self.assertRaises(ReconstructionError):
                encode(a,b)
        with self.assertRaisesRegex(ReconstructionError, "BUDGET"):
            encode(b"ab",b"cd",max_bytes=1)
        pkt=encode(b"ab",b"cd")
        with self.assertRaisesRegex(ReconstructionError, "PACKET_CONTRACT"):
            decode(b"ab",pkt,max_bytes=1)


if __name__ == "__main__":
    unittest.main()
