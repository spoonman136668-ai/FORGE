"""Offline intake/SQLite qualification; no real provider or scientific episodes."""
import base64
import json
import unittest

from f139.nci04_autonomy_feed import prepare_feed
from f139.nci04_native_contract import REPOS, canonical
from f139.nci04_research_steering import fair_lane_order, rank_eligible, SteeringDenied
from f139.test_nci04_autonomy_feed import FakeProvider


class ThreeLaneProvider:
    def __init__(self):
        self.providers = {}
        for lane, (repo, _, _) in REPOS.items():
            p = FakeProvider()
            p.pr["head"]["repo"]["full_name"] = repo
            if lane != "Wingless":
                p.path = ("yggdrasil/native_policy.py" if lane == "Yggdrasil"
                          else "scripts/native_policy.py")
                p.before, p.after = b"x = 1\n", b"x = 2\n"
            self.providers[lane] = p
        self.policy = self.providers["Wingless"]
        self.policy.policy["lanes"] = list(REPOS)

    def get(self, route):
        if route.endswith("/FORGE/issues/807"):
            return self.policy.issue()
        for lane, (repo, _, _) in REPOS.items():
            prefix = "repos/" + repo + "/"
            if route.startswith(prefix):
                # Reuse exact original Git commit/tree/blob fixtures per repo.
                return self.providers[lane].get(route.replace(
                    prefix, "repos/spoonman136668-ai/Wingless/", 1))
        raise AssertionError(route)


class ThreeLaneFairnessTests(unittest.TestCase):
    def test_authenticated_feeder_reaches_hybrid_after_two_admissions(self):
        p = ThreeLaneProvider()
        known = set()
        first = prepare_feed(p.get, source_sha=p.policy.source,
                             existing_candidate_identities=known)
        self.assertEqual([c["lane"] for c in first["candidates"]],
                         ["Wingless", "Yggdrasil"])
        # The actual owner rebuilds known identities from admissions, not from
        # discarded feeder drafts. Use that exact admitted set on restart.
        admitted = {c["candidate_identity"] for c in first["candidates"]}
        second = prepare_feed(p.get, source_sha=p.policy.source,
                              existing_candidate_identities=admitted.copy(),
                              admitted_lanes=("Wingless", "Yggdrasil"))
        self.assertEqual([c["lane"] for c in second["candidates"]], ["TTT-Hybrid"])
        intent = json.loads(base64.b64decode(second["candidates"][0]["intent_base64"]))
        self.assertEqual(intent["target_repository"], REPOS["TTT-Hybrid"][0])
        self.assertEqual(intent["path"], "scripts/native_policy.py")
        self.assertFalse(intent["scientific_first_use"])

    def test_continuous_high_scoring_backlog_cannot_starve_third_lane(self):
        candidates = [{"lane": lane, "advisory_handoff": {
            "advisory_only": True, "expected_information_microbits": 10**12,
            "estimated_compute_units": 1}} for lane in REPOS for _ in range(3)]
        history = ()
        services = []
        for _ in range(12):
            selected = rank_eligible(candidates, admitted_lanes=history)
            lanes = [c["lane"] for c in selected]
            self.assertEqual(len(set(lanes)), 2)
            services.extend(lanes)
            history += tuple(lanes)
        for i in range(len(services) - 2):
            self.assertEqual(set(services[i:i+3]), set(REPOS))
        self.assertEqual([services.count(lane) for lane in REPOS], [8, 8, 8])

    def test_bad_history_denied_and_unavailable_lane_never_reserves_slot(self):
        for history in (["Wingless"], ("FORGE-self",), ("KTRADE",), (1,)):
            with self.assertRaises(SteeringDenied):
                fair_lane_order(history)
        candidates = [{"lane": "Wingless"}, {"lane": "Wingless"}]
        self.assertEqual(rank_eligible(candidates), candidates)

    def test_old_policy_does_not_fetch_or_admit_hybrid(self):
        p = ThreeLaneProvider()
        p.policy.policy["lanes"] = ["Wingless", "Yggdrasil"]
        def get(route):
            self.assertNotIn("TTT-Hybrid-Lab", route)
            return p.get(route)
        report = prepare_feed(get, source_sha=p.policy.source,
                              existing_candidate_identities=set(),
                              admitted_lanes=("Wingless", "Yggdrasil"))
        self.assertEqual({c["lane"] for c in report["candidates"]},
                         {"Wingless", "Yggdrasil"})

    def test_original_tick_uses_admission_history_after_cold_restart(self):
        # Real existing Database/event chain and real run_once; provider writes
        # are a fixture. This does not claim live worker execution or receipts.
        from f139.test_nci04_two_inflight import NativeDualInFlightTests
        from f139.test_nci04_owner_issue import issue, MAIN, TARGET, TREE, HMAC
        from f139.test_hybrid_native_admission import hybrid_intent
        from f139.nci04_owner_issue import inspect_owner_issue
        from f139.hybrid_owner_admission import migrate_hybrid_lane
        from f139.local_controller import Database, run_once
        fixture = NativeDualInFlightTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        migrate_hybrid_lane(fixture.db)
        work = []
        for n, lane in enumerate(REPOS, 900):
            raw = issue(lane if lane != "TTT-Hybrid" else "Wingless")
            raw.update(number=n, id=5952000000+n)
            if lane == "TTT-Hybrid":
                body = json.loads(raw["body"])
                body["lane"] = lane
                body["intent_base64"] = base64.b64encode(canonical(hybrid_intent())).decode()
                raw["body"] = json.dumps(body, sort_keys=True)
            work.append(inspect_owner_issue(raw, protected_main=MAIN,
                authenticated_target_commit=TARGET, authenticated_target_tree=TREE))
        # Two Wingless issues have smaller numbers; Yggdrasil still gets slot 2.
        extra = fixture.work(899)
        api = fixture.Provider([extra, *work])
        run_once(fixture.db, api, fixture.original.path, HMAC, now="2026-10-22T10:00:00Z")
        run_once(fixture.db, api, fixture.original.path, HMAC, now="2026-10-22T10:01:00Z")
        self.assertEqual(api.dispatches, [extra.ticket, work[1].ticket])
        self.assertEqual(len(fixture.db.actives()), 2)
        fixture.db.close()
        db = Database(fixture.original.path)
        self.addCleanup(db.close)
        run_once(db, api, fixture.original.path, HMAC, now="2026-10-22T10:02:00Z")
        self.assertEqual(len(api.dispatches), 2)  # Ambiguous startup never replayed.
        # Legitimate fixture failure custody releases capacity; no invented PASS.
        for row in db.actives():
            db.quarantine(row["ticket"], "QUALIFICATION_PROVIDER_FAILED")
        run_once(db, api, fixture.original.path, HMAC, now="2026-10-22T10:12:00Z")
        self.assertEqual(api.dispatches[-1], work[2].ticket)
        db.verify()
