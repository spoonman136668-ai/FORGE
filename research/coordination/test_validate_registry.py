"""Standard-library structural and authority fail-closed tests."""
import json
import unittest
from pathlib import Path

from validate_registry import Invalid, validate


HERE = Path(__file__).resolve().parent
RAW = (HERE / "registry.v1.json").read_bytes()


class RegistryTests(unittest.TestCase):
    def test_baseline_valid_but_never_automatic_retirement(self):
        result = validate(RAW)
        self.assertTrue(result["registry_valid"])
        self.assertFalse(result["retirement_ready"])
        self.assertGreaterEqual(result["tracks"], 6)

    def altered(self, mutation):
        obj = json.loads(RAW)
        mutation(obj)
        return json.dumps(obj).encode()


    def test_three_research_chats_do_not_collapse_scientific_oversight(self):
        # The two organizational roles and three distinct science conversations
        # are independent dimensions; neither grants a runtime permission.
        registry = json.loads(RAW)
        self.assertEqual(registry["targets"]["research_chat_count"], 3)
        self.assertEqual({x["id"] for x in registry["oversight"]},
                         {"forge-operations", "unified-research"})
        self.assertTrue(registry["advisory_only"])
        self.assertTrue(all(x is False for x in registry["authority"].values()))
        self.assertTrue(all(x["status"] == "UNVERIFIED" and x["evidence"] == []
                            for x in registry["readiness_gates"]))
        for wrong in (2, 4, True, "3"):
            with self.subTest(wrong=wrong), self.assertRaises(Invalid):
                validate(self.altered(
                    lambda x: x["targets"].__setitem__("research_chat_count", wrong)))
        self.assertFalse(validate(RAW)["retirement_ready"])

    def test_denied_dispatch_and_promotion(self):
        for flag in ("dispatch", "promote", "modify_controller", "first_use"):
            with self.subTest(flag=flag), self.assertRaises(Invalid):
                validate(self.altered(lambda x: x["authority"].__setitem__(flag, True)))

    def test_reject_fake_readiness(self):
        with self.assertRaises(Invalid):
            validate(self.altered(lambda x: x["readiness_gates"][0].__setitem__("status", "PASS")))

    def test_reject_duplicate_track(self):
        with self.assertRaises(Invalid):
            validate(self.altered(lambda x: x["tracks"].append(x["tracks"][0].copy())))

    def test_reject_six_lane_route_for_new_track(self):
        with self.assertRaises(Invalid):
            validate(self.altered(lambda x: x["tracks"][-1].__setitem__("evidence_route", "EXISTING_SIX_LANE")))

    def test_reject_missing_original_lane(self):
        with self.assertRaises(Invalid):
            validate(self.altered(lambda x: x["tracks"].pop(0)))

    def test_reject_untrusted_repo_and_url(self):
        for mutation in (
            lambda x: x["tracks"][0].__setitem__("custodian_repo", "untrusted/private-repo"),
            lambda x: x["tracks"][0].__setitem__("source_pointer", "file:///tmp/secret"),
        ):
            with self.assertRaises(Invalid):
                validate(self.altered(mutation))

    def test_reject_noncanonical_blob_source_paths(self):
        # The existing GitHub URL allowlist alone permits ambiguous dot,
        # traversal and duplicate-separator paths. None can be trusted as
        # an immutable source pointer, even in an advisory-only inventory.
        original = json.loads(RAW)["tracks"][2]["source_pointer"]
        prefix = original.rsplit("/", 1)[0] + "/"
        for relative in ("../different.md", "./same.md", "child/../other.md",
                         "child//other.md"):
            with self.subTest(relative=relative), self.assertRaises(Invalid):
                validate(self.altered(lambda obj: obj["tracks"][2].__setitem__(
                    "source_pointer", prefix + relative)))
        self.assertTrue(validate(RAW)["registry_valid"])

    def test_reject_duplicate_casefold_keys(self):
        with self.assertRaises(Invalid):
            validate(RAW[:-2] + b', "Authority": {} }')

    def test_reject_trailing_json(self):
        with self.assertRaises(Invalid):
            validate(RAW + b'{}')


if __name__ == "__main__":
    unittest.main()
