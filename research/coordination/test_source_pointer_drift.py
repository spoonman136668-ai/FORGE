"""H6: strictly offline, non-authorizing PR-head drift screen.

This module is test-discoverable in FORGE's *existing* Python qualification.
No network, API calls, controller, queue, file writes, merge or scientific decision.
An input observation is caller-supplied, NOT an authenticated GitHub witness.
"""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

from validate_registry import Invalid, _unique_object_pairs
from validate_handoff import validate_handoff

HERE = Path(__file__).resolve().parent
HANDOFF = (HERE / "handoff.v1.json").read_bytes()
SCHEMA = "forge.research-pointer-readback.v1"
SHA = re.compile(r"^[0-9a-f]{40}$")


def compare_readback(handoff_raw: bytes, observations_raw: bytes) -> dict:
    """Report stale, absent and matching PR pointers; never authorize anything."""
    validate_handoff(handoff_raw)
    if not isinstance(observations_raw, bytes) or not 0 < len(observations_raw) <= 65536:
        raise Invalid("H6_BAD_INPUT_SIZE")
    try:
        index = json.loads(handoff_raw, object_pairs_hook=_unique_object_pairs)
        obs = json.loads(observations_raw, object_pairs_hook=_unique_object_pairs)
    except (ValueError, UnicodeDecodeError) as exc:
        raise Invalid("H6_INVALID_JSON") from exc
    if not isinstance(obs, dict) or set(obs) != {"schema", "observations"} or obs["schema"] != SCHEMA:
        raise Invalid("H6_UNRECOGNIZED_SCHEMA")
    entries = obs["observations"]
    if not isinstance(entries, list) or len(entries) > 80:
        raise Invalid("H6_BOUNDED_OBSERVATIONS_REQUIRED")
    known = {p["url"] for w in index["workstreams"] for p in w["source_pointers"]}
    readback = {}
    for e in entries:
        if not isinstance(e, dict) or set(e) != {"url", "head_sha", "state", "merged"}:
            raise Invalid("H6_BAD_OBSERVATION_KEYS")
        url, sha = e["url"], e["head_sha"]
        if (not isinstance(url, str) or url not in known or url in readback or
            not isinstance(sha, str) or not SHA.fullmatch(sha) or
            e["state"] not in ("open", "closed") or type(e["merged"]) is not bool or
            (e["merged"] and e["state"] != "closed")):
            raise Invalid("H6_UNTRUSTED_OR_DUPLICATE_OBSERVATION")
        readback[url] = e
    counts = {"PIN_MATCHED": 0, "DRIFT": 0, "UNOBSERVED": 0}
    details = []
    for w in index["workstreams"]:
        for p in w["source_pointers"]:
            seen = readback.get(p["url"])
            status = ("UNOBSERVED" if seen is None else
                      "PIN_MATCHED" if seen["head_sha"] == p["sha"] else "DRIFT")
            counts[status] += 1
            details.append({"workstream": w["id"], "url": p["url"],
                            "pinned_sha": p["sha"],
                            "observed_sha": seen["head_sha"] if seen else None,
                            "status": status})
    # Even complete exact equality is only comparison against *supplied* metadata,
    # not authenticated ownership transfer, original-byte custody or live autonomy.
    return {
        "schema": "forge.research-pointer-drift-preview.v1",
        "advisory_only": True,
        "observations_authenticated": False,
        "live_runtime_verified": False,
        "retirement_ready": False,
        "counts": counts,
        "details": details,
    }


class SourcePointerDriftTests(unittest.TestCase):
    @staticmethod
    def observations(items):
        return json.dumps({"schema": SCHEMA, "observations": items}).encode()

    @staticmethod
    def sources():
        x = json.loads(HANDOFF)
        return [p for w in x["workstreams"] for p in w["source_pointers"]]

    def test_empty_observation_cannot_mark_retirement_ready(self):
        r = compare_readback(HANDOFF, self.observations([]))
        self.assertFalse(r["retirement_ready"])
        self.assertFalse(r["observations_authenticated"])
        self.assertGreater(r["counts"]["UNOBSERVED"], 0)

    def test_matching_sha_still_advisory(self):
        p = self.sources()[0]
        observation = dict(url=p["url"], head_sha=p["sha"], state="open", merged=False)
        r = compare_readback(HANDOFF, self.observations([observation]))
        self.assertEqual(r["counts"]["PIN_MATCHED"], 1)
        self.assertFalse(r["live_runtime_verified"])
        self.assertFalse(r["retirement_ready"])

    def test_actual_stale_e_research_pointer_is_detected(self):
        p = next(p for p in self.sources() if p["url"].endswith("/FORGE/pull/1194"))
        # Source readback observation from 2026-10-30; this test is a frozen
        # diagnostic fixture, NOT a network read or present-day head claim.
        observation = dict(url=p["url"],
                           head_sha="e0898db178f8582361ddd6765f92fa1695480dc9",
                           state="open", merged=False)
        r = compare_readback(HANDOFF, self.observations([observation]))
        self.assertEqual(r["counts"]["DRIFT"], 1)
        self.assertIn("1194", next(x["url"] for x in r["details"] if x["status"] == "DRIFT"))
        self.assertFalse(r["retirement_ready"])

    def test_missing_native_source_is_unobserved_not_pass(self):
        p = next(p for p in self.sources() if "/Wingless/" in p["url"])
        other = next(x for x in self.sources() if x["url"] != p["url"])
        r = compare_readback(HANDOFF, self.observations([
            dict(url=other["url"], head_sha=other["sha"], state="open", merged=False)
        ]))
        self.assertIn(p["url"], {x["url"] for x in r["details"] if x["status"] == "UNOBSERVED"})

    def test_denies_duplicate_observation(self):
        p = self.sources()[0]
        observation = dict(url=p["url"], head_sha=p["sha"], state="open", merged=False)
        with self.assertRaises(Invalid):
            compare_readback(HANDOFF, self.observations([observation, observation]))

    def test_denies_new_unverified_repo_and_sha(self):
        p = self.sources()[0]
        for change in ({"url": "https://github.com/other/repo/pull/1"},
                       {"head_sha": "not-a-sha"}):
            with self.subTest(change=change), self.assertRaises(Invalid):
                compare_readback(HANDOFF, self.observations([
                    {**dict(url=p["url"], head_sha=p["sha"], state="open", merged=False), **change}
                ]))

    def test_denies_forged_authority_fields(self):
        p = self.sources()[0]
        record = dict(url=p["url"], head_sha=p["sha"], state="open", merged=False)
        with self.assertRaises(Invalid):
            compare_readback(HANDOFF, json.dumps({
                "schema": SCHEMA, "observations": [record], "retirement_ready": True
            }).encode())

    def test_denies_invalid_merge_and_nonboolean_types(self):
        p = self.sources()[0]
        for change in ({"state": "open", "merged": True},
                       {"state": "closed", "merged": "true"},
                       {"state": "approved"}):
            with self.subTest(change=change), self.assertRaises(Invalid):
                compare_readback(HANDOFF, self.observations([
                    {**dict(url=p["url"], head_sha=p["sha"], state="open", merged=False), **change}
                ]))

    def test_denies_case_fold_duplicate_json_keys(self):
        with self.assertRaises(Invalid):
            compare_readback(HANDOFF,
                b'{"schema":"forge.research-pointer-readback.v1",'
                b'"observations":[],"Observations":[]}')

    def test_denies_unbounded_payload(self):
        with self.assertRaises(Invalid):
            compare_readback(HANDOFF, b" " * 65537)


if __name__ == "__main__":
    unittest.main()
