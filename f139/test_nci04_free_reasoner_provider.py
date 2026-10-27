"""Source-only zero-credit Nemotron transport tests; no real HTTP or secrets."""
from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from f139.nci04_native_contract import canonical, digest
from f139.nci04_free_reasoner_provider import (
    ENDPOINT, MODEL, SCHEMA, FreeReasonerDenied, FreeReasonerUnavailable,
    infer_free_once, make_body, public_packet,
)


class FreeReasonerSourceOnlyTests(unittest.TestCase):
    def setUp(self):
        self.source = ("class PublicCausalCells:\n"
                       "    def choose(self, address: int) -> int:\n"
                       "        return 0\n")
        self.request = {
            "schema": "forge.f139.model-request.v1",
            "lane": "Yggdrasil",
            "controller_source_sha": "a" * 40,
            "target_commit": "b" * 40,
            "target_tree_sha": "c" * 40,
            "path": "yggdrasil/public_causal_cells.py",
            "before_sha256": digest(self.source.encode()),
            "source": self.source,
            "history_sha256": "d" * 64,
            "history": [
                {"candidate_identity": "e" * 64,
                 "outcome": "QUARANTINED",
                 "summary": "Original owner ticket #989; NEVER SEND THIS"},
                {"candidate_identity": "f" * 64,
                 "outcome": "VERIFIED",
                 "summary": "Original owner ticket #1009; NEVER SEND THIS"},
            ],
            "steering_source_commit": "1" * 40,
            "steering_manifest_sha256": "2" * 64,
            "steering_documents": {
                "PRIVATE": "private Mind-Palace notes NEVER SEND THIS"},
            "scientific_first_use": False,
            "model_execution_authorized": False,
            "publication_authorized": False,
        }

    def test_no_raw_original_owner_ticket_or_private_steering_escapes(self):
        p = public_packet(self.request, public_source_verified=True)
        self.assertEqual(p["schema"], SCHEMA)
        text = canonical(p).decode("utf-8")
        self.assertNotIn("NEVER SEND", text)
        self.assertNotIn("Mind-Palace", text)
        self.assertNotIn("#989", text)
        self.assertNotIn("#1009", text)
        self.assertEqual(p["retained_outcome_counts"],
                         {"QUARANTINED": 1, "VERIFIED": 1})
        self.assertEqual(p["history_sha256"], "d" * 64)
        self.assertEqual(p["public_source"], self.source)

    def test_never_send_without_independent_publicness(self):
        with self.assertRaisesRegex(FreeReasonerDenied, "SOURCE_PUBLICNESS"):
            public_packet(self.request, public_source_verified=False)
        with self.assertRaisesRegex(FreeReasonerDenied, "SOURCE_PUBLICNESS"):
            public_packet({**self.request, "publication_authorized": True},
                          public_source_verified=True)
        with self.assertRaisesRegex(FreeReasonerDenied, "SOURCE_OR_HISTORY_HASH"):
            public_packet({**self.request, "source": "non-original"},
                          public_source_verified=True)

    def test_exact_free_model_and_bounded_prompt(self):
        p = public_packet(self.request, public_source_verified=True)
        body = json.loads(make_body(p))
        self.assertEqual(MODEL, "nvidia/nemotron-3-ultra-550b-a55b:free")
        self.assertEqual(ENDPOINT,
                         "https://openrouter.ai/api/v1/chat/completions")
        self.assertEqual(body["model"], MODEL)
        self.assertTrue(body["model"].endswith(":free"))
        self.assertEqual(body["temperature"], 0)
        self.assertNotIn("response_format", body)
        self.assertNotIn("tools", body)
        self.assertEqual(len(body["messages"]), 2)
        self.assertNotIn("NEVER SEND", json.dumps(body))

    def test_one_response_is_data_not_authority(self):
        p = public_packet(self.request, public_source_verified=True)
        response = {
            "id": "test-only", "choices": [{
                "finish_reason": "stop",
                "message": {
                    "role": "assistant",
                    "content": canonical({
                        "schema": "forge.f139.model-proposal.v1",
                        "lane": p["lane"],
                        "target_commit": p["target_commit"],
                        "path": p["path"],
                        "history_sha256": p["history_sha256"],
                        "question": "Does a learned cell retain uncertainty?",
                        "hypothesis": "Local entropy reduces poor choices",
                        "control": "equal-step random and greedy",
                        "candidate_source": self.source + "\n# local development\n",
                    }).decode("utf-8")
                },
            }],
            "usage": {"cost": 0},
        }
        called = []
        def send(body, token):
            called.append((json.loads(body)["model"], token))
            return canonical(response)
        got = infer_free_once(p, token="test-secret-never-printed",
                              transport=send)
        self.assertEqual(len(called), 1)
        self.assertEqual(called[0][0], MODEL)
        self.assertEqual(got["paid_model_calls"], 0)
        self.assertFalse(got["remote_response_trusted"])
        self.assertFalse(got["scientific_first_use"])
        self.assertFalse(got["publication_authorized"])
        self.assertEqual(json.loads(got["proposal_bytes"])["path"], p["path"])

    def test_empty_key_does_not_touch_network(self):
        p = public_packet(self.request, public_source_verified=True)
        calls=[]
        def send(body, token):
            calls.append(1)
            return b"{}"
        with patch.dict("os.environ", {"OPENROUTER_API_KEY": ""}):
            with self.assertRaisesRegex(FreeReasonerUnavailable, "NO_KEY_NO_REQUEST"):
                infer_free_once(p, transport=send)
        self.assertEqual(calls, [])

    def test_unavailable_and_transient_errors_do_not_retry(self):
        p = public_packet(self.request, public_source_verified=True)
        calls=[]
        def bad(body, token):
            calls.append(1)
            raise ConnectionError("remote provider unavailable")
        with self.assertRaisesRegex(FreeReasonerUnavailable, "NO_RETRY"):
            infer_free_once(p, token="dummy", transport=bad)
        self.assertEqual(len(calls), 1)

    def test_nonzero_cost_malformed_tool_or_truncated_reply_denied(self):
        p = public_packet(self.request, public_source_verified=True)
        good = {"choices": [{"finish_reason": "stop",
                             "message": {"role": "assistant", "content": "{}"}}],
                "usage": {"cost": 0}}
        for val, error in [
            ({**good, "usage": {"cost": 0.01}}, "NONZERO_PROVIDER_COST"),
            ({**good, "choices": [{
                "finish_reason": "length",
                "message": {"role": "assistant", "content": "{}"}}]},
             "INCOMPLETE_OR_TOOL"),
            ({**good, "choices": [{
                "finish_reason": "stop",
                "message": {"role": "assistant", "content": "{}",
                            "tool_calls": [{"function": "gh api"}]}}]},
             "INCOMPLETE_OR_TOOL"),
        ]:
            with self.subTest(error=error):
                with self.assertRaisesRegex(FreeReasonerDenied, error):
                    infer_free_once(
                        p, token="dummy",
                        transport=lambda body, token: canonical(val))

    def test_no_file_upload_owner_sqlite_or_background_work(self):
        from f139 import nci04_free_reasoner_provider as module
        import inspect
        code=inspect.getsource(module)
        for forbidden in ("sqlite3.connect", "subprocess.run", "git push",
                          "threading.Timer", "taskschd", "write_model_draft"):
            self.assertNotIn(forbidden, code)
        self.assertIn("_NoRedirect", code)


if __name__ == "__main__":
    unittest.main()
