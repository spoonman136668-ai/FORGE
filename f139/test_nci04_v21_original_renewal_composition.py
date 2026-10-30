"""Source-only V21 integration boundaries; never access the real owner or provider."""
from __future__ import annotations

from pathlib import Path
from unittest import TestCase
from unittest.mock import Mock, patch
import inspect

from f139 import nci04_v21_original_renewal_composition as route
from f139.local_controller import run_once


class DummyOriginal:
    filename = Path("fake-original.sqlite")

    def __init__(self):
        self.meta_value = {"enabled": 1, "legacy_suspended": 1,
                           "source_sha": "a" * 40, "head_seq": 332,
                           "head_hash": "b" * 64}
        self.verifications = 0

    def verify(self):
        self.verifications += 1

    def meta(self):
        return dict(self.meta_value)

    def ready(self):
        return None

    def actives(self):
        return []


class OriginalRenewalCompositionTests(TestCase):
    def setUp(self):
        self.db = DummyOriginal()
        self.patches = []

        def replace(name, **kwargs):
            patcher = patch.object(route, name, **kwargs)
            result = patcher.start()
            self.addCleanup(patcher.stop)
            return result

        replace("Database", new=DummyOriginal)
        locked = patch.object(route.SingleOwner, "held", return_value=True)
        locked.start()
        self.addCleanup(locked.stop)
        self.packet = {"lane": "Yggdrasil"}
        self.packet_fn = Mock(return_value=self.packet)
        self.public_reader = Mock()
        self.original_get = Mock()
        self.original_write = Mock()
        self.witness = Mock(return_value=True)
        self.transport = Mock()
        self.attempts = replace("original_attempts", return_value=[])
        self.native = replace(
            "project_original_native_terminal",
            return_value={"disposition": "AUTHENTIC_FRESH_TERMINAL_SHADOW_ONLY_NOT_AUTHORIZED",
                          "shadow": {"disposition": "ELIGIBLE_SHADOW_ONLY_NOT_AUTHORIZED"},
                          "terminal_event_seq": 333},
        )
        self.budget = replace("combined_budget", return_value=True)
        self.reserve = replace(
            "reserve_original_intent_without_post",
            return_value={"disposition": "ORIGINAL_ATOMIC_INTENT_COMMITTED_NO_POST",
                          "original_request_attempt_event_seq": 334,
                          "original_request_attempt_event_sha256": "c" * 64},
        )
        self.handoff = replace(
            "custody_original_post_handoff_without_post",
            return_value={"disposition": "ORIGINAL_POST_HANDOFF_SPENT_NO_POST",
                          "original_post_handoff_event_seq": 335,
                          "original_post_handoff_event_sha256": "d" * 64},
        )
        self.send = replace(
            "one_original_free_send_source_only",
            return_value={"disposition": "ONE_MODEL_RESPONSE_UNTRUSTED_NO_PUBLICATION",
                          "provider_calls_in_this_invocation": 1},
        )
        self.validate = replace(
            "validate_original_response_without_publication",
            return_value={"disposition": "ORIGINAL_PROPOSAL_VALIDATED_DATA_ONLY",
                          "validation_event_seq": 337,
                          "validation_event_sha256": "e" * 64,
                          "candidate": {"candidate_source": b"safe public source"}},
        )
        self.publish = replace(
            "publish_original_v19_candidate_once",
            return_value={"disposition": "MODEL_DRAFT_AUTHENTICATED", "pr_number": 9999},
        )

    def cycle(self, **changes):
        opts = {
            "utc_day": "2026-10-30",
            "packet_for_terminal": self.packet_fn,
            "public_reader": self.public_reader,
            "original_get": self.original_get,
            "original_write": self.original_write,
            "owner_witness": self.witness,
            "token": "offline-fixture-not-real",
            "transport": self.transport,
        }
        opts.update(changes)
        return route.run_original_renewal_source_only(self.db, **opts)

    def test_composes_existing_custody_exactly_once_and_does_not_dispatch(self):
        response = self.cycle()
        self.assertEqual(response["disposition"], "MODEL_DRAFT_AUTHENTICATED")
        self.assertEqual(response["draft_pr_number"], 9999)
        self.assertEqual(response["provider_calls_this_invocation"], 1)
        self.assertFalse(response["runtime_activated"])
        self.assertFalse(response["worker_dispatched"])
        self.assertFalse(response["scientific_first_use"])
        self.assertEqual(response["paid_model_calls"], 0)
        self.assertEqual(self.native.call_count, 1)
        for method in (self.reserve, self.handoff, self.send,
                       self.validate, self.publish):
            self.assertEqual(method.call_count, 1)
        self.assertEqual(self.handoff.call_args.kwargs["reservation_seq"], 334)
        self.assertEqual(self.send.call_args.kwargs["handoff_seq"], 335)
        self.assertEqual(self.validate.call_args.kwargs["send_receipt"],
                         self.send.return_value)
        self.assertEqual(self.publish.call_args.kwargs["validation_seq"], 337)
        self.assertIs(self.publish.call_args.kwargs["original_write"],
                      self.original_write)

    def test_exhausted_legacy_and_no_new_native_terminal_never_reserve(self):
        self.native.return_value = {
            "disposition": "BLOCKED_NO_NEW_TERMINAL_AFTER_ORIGINAL_ATTEMPT",
            "shadow": None,
        }
        response = self.cycle()
        self.assertEqual(response["disposition"],
                         "BLOCKED_NO_FRESH_ELIGIBLE_NATIVE_TERMINAL")
        self.assertEqual(self.native.call_count, 2)
        self.packet_fn.assert_not_called()
        self.reserve.assert_not_called()
        self.send.assert_not_called()
        self.publish.assert_not_called()

    def test_spent_combined_rolling_budget_never_fetches_or_reserves(self):
        self.budget.return_value = False
        response = self.cycle()
        self.assertEqual(response["disposition"],
                         "BLOCKED_ORIGINAL_PLUS_RENEWAL_ROLLING_BUDGET")
        self.packet_fn.assert_not_called()
        self.reserve.assert_not_called()
        self.send.assert_not_called()

    def test_packet_wrong_lane_refused_before_any_original_append(self):
        self.packet_fn.return_value = {"lane": "Wingless"}
        with self.assertRaisesRegex(route.RenewalCycleDenied,
                                    "PUBLIC_PACKET_LANE_INVALID"):
            self.cycle()
        self.reserve.assert_not_called()
        self.send.assert_not_called()

    def test_owner_revoked_before_reservation_refuses_mutation(self):
        self.witness.side_effect = [True, False]
        response = self.cycle()
        self.assertEqual(response["disposition"],
                         "BLOCKED_OWNER_ORIGINAL_STATE_MOVED")
        self.reserve.assert_not_called()
        self.send.assert_not_called()

    def test_ambiguous_post_does_not_validate_or_publish(self):
        self.send.return_value = {
            "disposition": "MODEL_SEND_FAILED_OR_AMBIGUOUS_NO_RETRY",
            "provider_calls_in_this_invocation": 1,
        }
        response = self.cycle()
        self.assertEqual(response["disposition"],
                         "MODEL_SEND_FAILED_OR_AMBIGUOUS_NO_RETRY")
        self.assertEqual(response["provider_calls_this_invocation"], 1)
        self.validate.assert_not_called()
        self.publish.assert_not_called()

    def test_no_credentials_or_missing_original_lock_fails_before_read(self):
        with self.assertRaises(route.RenewalCycleDenied):
            self.cycle(token="")
        self.assertEqual(self.db.verifications, 0)
        self.native.assert_not_called()
        self.reserve.assert_not_called()

    def test_v20_original_run_once_has_no_v21_runtime_activation(self):
        source = inspect.getsource(run_once)
        self.assertNotIn("nci04_v21_original_renewal_composition", source)
        self.assertNotIn("run_original_renewal_source_only(", source)
        own = inspect.getsource(route.run_original_renewal_source_only)
        self.assertNotIn("os.environ", own)
        self.assertNotIn("OPENROUTER_API_KEY", own)
        self.assertNotIn("requests.post", own)
        self.assertNotIn("subprocess", own)
