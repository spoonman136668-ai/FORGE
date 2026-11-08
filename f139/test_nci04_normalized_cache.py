"""G133 exact-byte AST normalization replay/negative/memory-fence controls.

No test or historical negative is suppressed. Only successful immutable raw
source bytes can be reused in an in-process, entry-limited cache.
"""
import unittest

from f139 import nci04_model_free_search as search


class ExactByteASTCacheTests(unittest.TestCase):
    def setUp(self):
        search._normalized_exact_bytes.cache_clear()
        self.addCleanup(search._normalized_exact_bytes.cache_clear)

    def test_original_digest_is_identical_and_true_reuse_avoids_parse(self):
        raw = b"answer = 1 + 2\n"
        expected = search._normalized_uncached(raw)
        self.assertEqual(search.normalized(raw), expected)
        first = search._normalized_exact_bytes.cache_info()
        self.assertEqual((first.hits, first.misses, first.currsize), (0, 1, 1))
        self.assertEqual(search.normalized(bytes(bytearray(raw))), expected)
        second = search._normalized_exact_bytes.cache_info()
        self.assertEqual((second.hits, second.misses, second.currsize), (1, 1, 1))

    def test_source_byte_change_not_confused_with_ast_equivalence(self):
        original = b"choice = (1 + 2)\n"
        alias = b"choice=(1+2) # historical comment\n"
        distinct = b"choice = (1 + 3)\n"
        baseline = search._normalized_uncached
        self.assertEqual(search.normalized(original), baseline(original))
        self.assertEqual(search.normalized(alias), baseline(alias))
        self.assertEqual(search.normalized(original), search.normalized(alias))
        self.assertNotEqual(search.normalized(distinct), baseline(original))
        info = search._normalized_exact_bytes.cache_info()
        self.assertEqual((info.misses, info.currsize), (3, 3))
        # Independent original source identities remain distinct even if ASTs agree.
        self.assertNotEqual(original, alias)

    def test_invalid_syntax_and_unicode_remain_rejected_without_retained_negatives(self):
        for invalid in (b"def (\n", bytes((255, 10)), b"x = 1\n  y=2\n"):
            with self.subTest(invalid=invalid):
                for _ in range(2):
                    with self.assertRaisesRegex(
                            ValueError, "F139_MODEL_FREE_SEARCH_SOURCE_NOT_PARSEABLE"):
                        search.normalized(invalid)
                self.assertEqual(search._normalized_exact_bytes.cache_info().currsize, 0)

    def test_mutable_sources_use_original_uncached_path_and_reflect_changes(self):
        raw = bytearray(b"state=1\n")
        first = search.normalized(raw)
        self.assertEqual(first, search._normalized_uncached(raw))
        raw[:] = b"state=2\n"
        self.assertEqual(search.normalized(raw), search._normalized_uncached(raw))
        self.assertNotEqual(first, search.normalized(raw))
        self.assertEqual(search._normalized_exact_bytes.cache_info().currsize, 0)

    def test_oversized_input_falls_back_to_original_parser_without_occupying_cache(self):
        large = b"value=1\n#" + b"x"*256_000 + b"\n"
        self.assertGreater(len(large), 256_000)
        self.assertEqual(search.normalized(large), search._normalized_uncached(large))
        self.assertEqual(search._normalized_exact_bytes.cache_info().currsize, 0)

    def test_capacity_is_fixed_and_old_entries_are_evicted(self):
        originals = [f"count={i}\n".encode() for i in range(80)]
        for source in originals:
            self.assertEqual(search.normalized(source), search._normalized_uncached(source))
        info = search._normalized_exact_bytes.cache_info()
        self.assertEqual(info.maxsize, 64)
        self.assertEqual(info.currsize, 64)
        self.assertEqual(info.misses, 80)
        # A previously evicted raw source must be reparsed, never guessed.
        search.normalized(originals[0])
        self.assertEqual(search._normalized_exact_bytes.cache_info().misses, 81)

    def test_same_bytes_cache_hit_has_no_external_authority_or_persistence(self):
        source = b"counter=123\n"
        before = search.normalized(source)
        self.assertEqual(search._normalized_exact_bytes.cache_info().currsize, 1)
        search._normalized_exact_bytes.cache_clear()
        self.assertEqual(search._normalized_exact_bytes.cache_info().currsize, 0)
        self.assertEqual(search.normalized(source), before)
        self.assertEqual(search._normalized_exact_bytes.cache_info().misses, 1)


if __name__ == "__main__":
    unittest.main()
