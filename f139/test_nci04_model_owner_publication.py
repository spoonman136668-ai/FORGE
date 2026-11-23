"""Mock original-owner model publication: no real GitHub, runner or local owner."""
from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from f139.local_controller import GitHub
from f139.nci04_model_owner_publication import (
    ATTEMPT, SUCCESS, ModelDraftDenied, publish_model_once, _unique_branch)
from f139.nci04_model_owner_bridge import owner_request
from f139.nci04_model_proposal import SCHEMA as MODEL_SCHEMA
from f139.nci04_owner_ledger import activate_native, admit_native_issue
from f139 import nci04_research_steering as steering
from f139.test_nci04_candidate_producer import SOURCE
from f139.test_nci04_candidate_publisher import FakeOriginalOwner
from f139.test_nci04_research_steering import SteeringProvider
import test_nci04_owner_ledger as fixture_owner_ledger
from test_nci04_owner_ledger import MAIN


class OwnerModelPublicationTests(unittest.TestCase):
    def setUp(self):
        fixture = fixture_owner_ledger.LedgerTests("test_admit_exactly_once_and_verify_original_ledger")
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.fixture = fixture
        self.db = fixture.db
        self.assertTrue(activate_native(self.db, fixture.approval()))
        self.provider = FakeOriginalOwner()
        self.provider.source = MAIN
        self.steering = SteeringProvider()
        steering_patch = patch.object(steering, "DOCUMENTS", self.steering.documents)
        steering_patch.start()
        self.addCleanup(steering_patch.stop)

    def snapshot(self, witness=lambda: True):
        return owner_request(
            self.db, self.provider.get, self.steering.get, source_sha=MAIN,
            lane="Yggdrasil", target_commit=self.provider.parent,
            path=self.provider.path, owner_witness=witness)

    def response(self, snapshot, *, source=None, lane="Yggdrasil"):
        changed = source if source is not None else (
            SOURCE.decode("utf-8") +
            "\n# prospective bounded retained-state comparison\n")
        return json.dumps({
            "schema": MODEL_SCHEMA, "lane": lane,
            "target_commit": self.provider.parent, "path": self.provider.path,
            "history_sha256": snapshot["session"]["history_sha256"],
            "question": "Can local memories reduce exploration errors?",
            "hypothesis": "Local count-memory improves decisions.",
            "control": "Matched conventional local-count policy.",
            "candidate_source": changed,
        }).encode("utf-8")

    def publish(self, snapshot=None, *, witness=lambda: True,
                source=None, writer=None):
        session = snapshot or self.snapshot()
        return publish_model_once(
            self.db, self.provider.get, self.steering.get,
            writer if writer is not None else self.provider.write,
            session=session["session"],
            raw_response=self.response(session, source=source),
            owner_witness=witness)

    def rows(self, kind):
        return [json.loads(r["payload"]) for r in self.db.conn.execute(
            "SELECT payload FROM events WHERE kind=? ORDER BY seq", (kind,))]

    def test_original_owner_single_model_draft_publication_and_no_dispatch(self):
        prepared = self.snapshot()
        old = self.db.meta()["head_seq"]
        result = self.publish(prepared)
        self.assertEqual(result["disposition"], "MODEL_DRAFT_AUTHENTICATED")
        self.assertEqual(result["pr_number"], 488)
        self.assertFalse(result["scientific_first_use"])
        self.assertFalse(result["worker_dispatched"])
        self.assertEqual(self.db.meta()["head_seq"], old + 2)
        self.assertEqual(len(self.rows(ATTEMPT)), 1)
        self.assertEqual(len(self.rows(SUCCESS)), 1)
        self.assertFalse(self.rows(ATTEMPT)[0]["retry_allowed"])
        self.assertEqual([m for m, _ in self.provider.write_calls],
                         ["POST", "PUT", "POST"])
        self.assertEqual(self.provider.head_data, (
            SOURCE.decode("utf-8") +
            "\n# prospective bounded retained-state comparison\n").encode())
        self.assertTrue(self.provider.pr["draft"])
        self.assertEqual(json.loads(self.provider.pr["body"])["schema"],
                         "forge.f139.owner-model-draft-note.v1")
        self.db.verify()

    def test_missing_original_owner_witness_forbids_any_write(self):
        with self.assertRaisesRegex(ModelDraftDenied, "ORIGINAL_WINDOWS_OWNER"):
            self.publish(witness=lambda: False)
        self.assertEqual(self.provider.write_calls, [])
        self.assertEqual(self.rows(ATTEMPT), [])

    def test_moved_source_and_historical_head_forbid_any_write(self):
        snapshot = self.snapshot()
        self.provider.parent_data += b"\n# tampered upstream\n"
        with self.assertRaises(ValueError):
            self.publish(snapshot)
        self.assertFalse(self.provider.write_calls)
        self.assertFalse(self.rows(ATTEMPT))
        self.provider.parent_data = SOURCE
        snapshot = self.snapshot()
        with self.db.transaction():
            self.db.event("FIXTURE_UNTRUSTED", {"sequence": 234})
        with self.assertRaises(ValueError):
            self.publish(snapshot)
        self.assertFalse(self.provider.write_calls)

    def test_failed_git_write_is_at_most_once_and_suppresses_replays(self):
        original = self.snapshot()
        self.provider.fail_after_reference = True
        first = self.publish(original)
        self.assertEqual(first["disposition"],
                         "MODEL_DRAFT_REMOTE_AMBIGUOUS_NO_RETRY")
        self.assertEqual(len(self.rows(ATTEMPT)), 1)
        self.assertEqual(len(self.rows(SUCCESS)), 0)
        self.db.verify()
        self.provider.fail_after_reference = False
        with self.assertRaises(ValueError):
            self.publish(original)
        self.assertEqual(len(self.provider.write_calls), 2)
        with self.assertRaisesRegex(ModelDraftDenied, "UNRESOLVED_REMOTE"):
            self.publish(self.snapshot(), source=SOURCE.decode()+"\n# new one\n")
        self.assertEqual(len(self.provider.write_calls), 2)

    def test_repeated_published_source_is_never_republished(self):
        first = self.snapshot()
        self.assertEqual(self.publish(first)["disposition"],
                         "MODEL_DRAFT_AUTHENTICATED")
        self.provider.pr = None
        self.provider.reference = None
        self.provider.head_sha = None
        with self.assertRaisesRegex(ModelDraftDenied, "PREVIOUSLY_ATTEMPTED"):
            self.publish(self.snapshot())
        self.assertEqual(len(self.provider.write_calls), 3)

    def test_wrong_model_lane_rejected_without_remote_write(self):
        prepared = self.snapshot()
        with self.assertRaises(ValueError):
            publish_model_once(
                self.db, self.provider.get, self.steering.get,
                self.provider.write, session=prepared["session"],
                raw_response=self.response(prepared, lane="Wingless"),
                owner_witness=lambda: True)
        self.assertEqual(self.provider.write_calls, [])
        self.assertEqual(self.rows(ATTEMPT), [])

    def test_negative_original_custody_is_not_erased(self):
        self.assertTrue(admit_native_issue(
            self.db, self.fixture.native, "2026-10-27T09:00:00Z"))
        t = self.fixture.native.ticket
        self.db.claim(t, "2026-10-27T09:01:00Z")
        self.db.quarantine(t, "PROSPECTIVE_NEGATIVE")
        snap = self.snapshot()
        self.assertEqual(snap["request"]["history"][0]["outcome"],
                         "QUARANTINED")
        result = self.publish(snap)
        self.assertEqual(result["disposition"], "MODEL_DRAFT_AUTHENTICATED")
        self.assertEqual(snap["request"]["history"][0]["outcome"],
                         "QUARANTINED")
        self.db.verify()

    def test_unauthorized_write_endpoints_rejected_before_network(self):
        api = GitHub(runner=lambda args: (_ for _ in ()).throw(
            AssertionError("network forbidden")))
        with self.assertRaisesRegex(Exception, "MODEL_WRITE_TARGET"):
            api.owner_model_write("POST", "repos/spoonman136668-ai/FORGE/issues",
                                  {"title": "bypass"})
        with self.assertRaisesRegex(Exception, "MODEL_SOURCE_WRITE"):
            api.owner_model_write(
                "PUT", "repos/spoonman136668-ai/Yggdrasil/contents/scripts/../secrets.py",
                {"message": "F139 MODEL DEV: owner-validated isolated source candidate",
                 "content": "YQ==", "sha": "a"*40,
                 "branch": "f139/auto-model-y-" + "a"*20 + "-" + "b"*12})



class HistoricalPrHistoryWindowTests(unittest.TestCase):
    """No-network proof of the original G2 1200-ref replay scan boundary."""

    repo = "spoonman136668-ai/Yggdrasil"
    branch = "f139/auto-model-y-" + "a" * 20 + "-" + "9" * 12

    @staticmethod
    def entries(n):
        # Monotone GitHub numbers and immutable local heads, all observed.
        return [{"number": 1500 - i,
                 "head": {"ref": "past-model-" + str(1500 - i)}}
                for i in range(n)]

    def reader(self, entries, *, moved_first=False):
        requests = []
        refroute = ("repos/" + self.repo +
                    "/git/matching-refs/heads/" + self.branch)
        prefix = "repos/" + self.repo + "/pulls?state=all&per_page=50&page="
        def get(route):
            requests.append(route)
            if route == refroute:
                return []
            if not route.startswith(prefix):
                raise AssertionError("UNBOUNDED_OR_WRONG_CATALOG_REQUEST: " + route)
            suffix = route[len(prefix):]
            if not suffix.isdigit() or suffix.startswith("0"):
                raise AssertionError("INVALID_PAGE")
            page = int(suffix)
            if not 1 <= page <= 24:
                raise AssertionError("PAGE_BOUNDARY_BYPASS")
            result = entries[(page - 1) * 50:page * 50]
            if moved_first and page == 1 and requests.count(route) > 1:
                return [{**result[0], "number": 999999}, *result[1:]]
            return result
        return get, requests

    def test_same_1200_ref_coverage_across_24_bounded_pages(self):
        # 1182 historical PRs (real repository has >1100), including closed.
        get, calls = self.reader(self.entries(1182))
        self.assertIsNone(_unique_branch(get, self.repo, self.branch))
        self.assertEqual(len(calls), 26)  # ref + 24 pages + first-page recheck
        self.assertTrue(all("per_page=50" in route
                            for route in calls[1:]))
        self.assertEqual(calls[-1], calls[1])

    def test_full_1200_historical_window_is_not_silent_exhaustion(self):
        get, calls = self.reader(self.entries(1200))
        with self.assertRaisesRegex(ModelDraftDenied, "PR_HISTORY_UNBOUNDED"):
            _unique_branch(get, self.repo, self.branch)
        self.assertEqual(len(calls), 25)  # ref + exactly 24 full pages
        self.assertTrue(all("per_page=50" in route for route in calls[1:]))

    def test_existing_remote_ref_or_historical_branch_blocks_publication(self):
        entries = self.entries(1182)
        entries[1129] = {
            **entries[1129],
            "head": {"ref": self.branch},
        }
        get, calls = self.reader(entries)
        with self.assertRaisesRegex(ModelDraftDenied, "PR_ALREADY_PUBLISHED"):
            _unique_branch(get, self.repo, self.branch)
        self.assertGreater(len(calls), 20)
        # The branch scan never supplies any writer or mutates owner history.

    def test_concurrent_page_shift_and_first_page_change_fail_closed(self):
        rows = self.entries(91)
        rows[50] = rows[0]  # Duplicate PR spanning two offset pages.
        get, _ = self.reader(rows)
        with self.assertRaisesRegex(ModelDraftDenied, "PR_HISTORY_CHANGED"):
            _unique_branch(get, self.repo, self.branch)

        get, _ = self.reader(self.entries(51), moved_first=True)
        with self.assertRaisesRegex(ModelDraftDenied, "PR_HISTORY_MOVED"):
            _unique_branch(get, self.repo, self.branch)

    def test_wrong_shape_ref_existing_and_oversized_page_fail_closed(self):
        prefix = "repos/" + self.repo + "/pulls?state=all&per_page=50&page="
        ref = "repos/" + self.repo + "/git/matching-refs/heads/" + self.branch
        def existing(route):
            if route == ref:
                return [{"ref": "refs/heads/" + self.branch,
                         "object": {"sha": "9" * 40}}]
            raise AssertionError("MUST_NOT_READ_PR_HISTORY")
        with self.assertRaisesRegex(ModelDraftDenied, "REF_ALREADY_EXISTS"):
            _unique_branch(existing, self.repo, self.branch)

        def too_many(route):
            if route == ref:
                return []
            if route == prefix + "1":
                return self.entries(51)
            raise AssertionError("UNEXPECTED_REQUEST")
        with self.assertRaisesRegex(ModelDraftDenied, "PR_HISTORY_INVALID"):
            _unique_branch(too_many, self.repo, self.branch)

if __name__ == "__main__":
    unittest.main()
