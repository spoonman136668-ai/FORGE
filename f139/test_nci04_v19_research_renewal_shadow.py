"""V19 shadow-only falsification: no SQLite/provider/runner work is performed."""
import unittest

from f139.nci04_v19_research_renewal_shadow import (
    ShadowDenied, shadow_decision, MAX_DAILY_TOTAL,
    MAX_ROLLING_30D_TOTAL,
)

SHA_A = "a" * 40
SHA_B = "b" * 40
SHA_C = "c" * 40
DAY = "2026-10-28"
PATH = "research/native/itd02/outcome/training_session.go"


def terminal(lane="Wingless", seq=100, ticket="new-terminal-100",
             source_sha=SHA_A, evidence_sha256="1"*64):
    return {
        "ticket": ticket, "lane": lane, "seq": seq,
        "source_sha": source_sha, "evidence_sha256": evidence_sha256,
        "stage": "VERIFIED", "chain_verified": True,
    }


def attempt(lane="Wingless", seq=99, ticket="old-terminal-99",
            day="2026-10-27", scope="2"*64):
    return {
        "day": day, "lane": lane, "ticket": ticket,
        "terminal_seq": seq, "scope_sha256": scope,
    }


def decision(*, lane="Wingless", target_commit=SHA_B, native_path=PATH,
             term=None, attempts=None, utc_day=DAY, owner_source_sha=SHA_C):
    if term is None:
        term = terminal(lane=lane)
    if attempts is None:
        attempts = []
    return shadow_decision(
        owner_source_sha=owner_source_sha, lane=lane,
        target_commit=target_commit, native_path=native_path,
        terminal=term, attempts=attempts, utc_day=utc_day,
    )


class V19ShadowTests(unittest.TestCase):
    def test_new_verified_terminal_only_shadows_without_dispatch(self):
        d = decision()
        self.assertEqual(d["disposition"], "ELIGIBLE_SHADOW_ONLY_NOT_AUTHORIZED")
        self.assertEqual(len(d["scope_sha256"]), 64)
        for k in ("original_owner_request_authorized", "worker_dispatched",
                  "scientific_first_use"):
            self.assertIs(d[k], False)
        for k in ("provider_requests", "paid_model_calls",
                  "accepted_ref_mutations", "controller_changes"):
            self.assertEqual(d[k], 0)

    def test_fresh_terminal_after_attempt_can_renew_without_replaying(self):
        rows = [attempt(seq=99)]
        self.assertEqual(decision(attempts=rows)["disposition"],
                         "ELIGIBLE_SHADOW_ONLY_NOT_AUTHORIZED")
        self.assertEqual(decision(attempts=rows, utc_day="2026-10-29")["disposition"],
                         "ELIGIBLE_SHADOW_ONLY_NOT_AUTHORIZED")

    def test_same_terminal_sticky_after_day_target_and_release_changes(self):
        rows = [attempt(seq=100, ticket="new-terminal-100")]
        self.assertEqual(decision(attempts=rows)["disposition"],
                         "BLOCKED_ALREADY_CONSUMED")
        self.assertEqual(decision(attempts=rows,
            owner_source_sha=SHA_A, target_commit=SHA_C,
            utc_day="2026-10-29")["disposition"], "BLOCKED_ALREADY_CONSUMED")

    def test_older_or_equal_lanes_cannot_redeem_unchanged_feedback(self):
        rows = [attempt(seq=105, ticket="other-terminal")]
        self.assertEqual(decision(attempts=rows)["disposition"],
                         "BLOCKED_NOT_NEW_LANE_EVIDENCE")
        self.assertEqual(decision(attempts=rows,
            term=terminal(seq=105,ticket="same-seq-different-ticket"))["disposition"],
            "BLOCKED_NOT_NEW_LANE_EVIDENCE")

    def test_one_each_lane_daily_and_global_budget(self):
        first = [attempt(day=DAY, lane="Wingless", seq=99)]
        self.assertEqual(decision(attempts=first)["disposition"],
                         "BLOCKED_BOUNDED_FREE_BUDGET")
        self.assertEqual(decision(lane="Yggdrasil",
            native_path="yggdrasil/public_causal_cells.py",
            term=terminal(lane="Yggdrasil",seq=9,ticket="fresh-y9"),
            attempts=first)["disposition"], "ELIGIBLE_SHADOW_ONLY_NOT_AUTHORIZED")
        both = first + [attempt(day=DAY, lane="Yggdrasil",
             seq=8,ticket="y-old-8",scope="3"*64)]
        self.assertEqual(len(both), MAX_DAILY_TOTAL)
        self.assertEqual(decision(lane="Yggdrasil",
            native_path="yggdrasil/public_causal_cells.py",
            term=terminal(lane="Yggdrasil",seq=9,ticket="fresh-y9"),
            attempts=both)["disposition"], "BLOCKED_BOUNDED_FREE_BUDGET")

    def test_rolling_30d_limit_and_30d_expiration_without_replay(self):
        rows = [
            attempt(day="2026-10-01", lane=("Wingless" if i%2==0 else "Yggdrasil"),
                    seq=i+1, ticket=f"terminal-{i}", scope=f"{i+10:064x}")
            for i in range(MAX_ROLLING_30D_TOTAL)
        ]
        self.assertEqual(decision(term=terminal(seq=1000),attempts=rows)["disposition"],
                         "BLOCKED_BOUNDED_FREE_BUDGET")
        expired = [attempt(day="2026-09-28",seq=99)]
        self.assertEqual(decision(attempts=expired)["disposition"],
                         "ELIGIBLE_SHADOW_ONLY_NOT_AUTHORIZED")
        consumed = [attempt(day="2026-09-28",seq=100,ticket="new-terminal-100")]
        self.assertEqual(decision(attempts=consumed)["disposition"],
                         "BLOCKED_ALREADY_CONSUMED")

    def test_bad_utc_dates_and_rollback_rejected(self):
        for day in ("2026-02-30", "2026-2-3", "2026-10-29junk"):
            with self.subTest(day=day), self.assertRaises(ShadowDenied):
                decision(utc_day=day)
        with self.assertRaisesRegex(ShadowDenied, "CHRONOLOGY"):
            decision(attempts=[attempt(day="2026-10-29")])
        with self.assertRaisesRegex(ShadowDenied, "CHRONOLOGY"):
            decision(attempts=[attempt(day="2026-10-27"),
                               attempt(day="2026-10-26",seq=98,
                                       ticket="older",scope="3"*64)])

    def test_forged_terminal_and_invalid_types_rejected(self):
        for name,value in (("stage","QUARANTINED"),
                           ("chain_verified",False),
                           ("chain_verified",1),
                           ("seq",True),
                           ("evidence_sha256","z"*64),
                           ("source_sha","short"),
                           ("lane","Other")):
            with self.subTest(name=name):
                t=terminal()
                t[name]=value
                with self.assertRaises(ShadowDenied):
                    decision(term=t)
        with self.assertRaises(ShadowDenied):
            decision(owner_source_sha="invalid")

    def test_duplicate_attempt_record_or_ticket_fails_closed(self):
        same=attempt()
        with self.assertRaisesRegex(ShadowDenied, "DUPLICATE"):
            decision(attempts=[same,same])
        with self.assertRaisesRegex(ShadowDenied, "DUPLICATE"):
            decision(attempts=[same,attempt(ticket=same["ticket"],scope="3"*64)])
        with self.assertRaises(ShadowDenied):
            decision(attempts=[attempt(scope="notsha")])

    def test_unsafe_paths_rejected(self):
        for value in ("../source.py","C:/private/file.go",
                      "/absolute/file.py","one//two.go",
                      "one/./two.go","one/back\\slash.py",
                      "one/$secret.py"):
            with self.subTest(value=value),self.assertRaises(ShadowDenied):
                decision(native_path=value)

    def test_shadow_cannot_authorize_with_false_science(self):
        d=decision(lane="Yggdrasil",
            native_path="yggdrasil/public_causal_cells.py",
            term=terminal(lane="Yggdrasil",seq=50,ticket="y-new-50"))
        self.assertIs(d["original_owner_request_authorized"],False)
        self.assertIs(d["scientific_first_use"],False)
        self.assertEqual(d["provider_requests"],0)


if __name__=="__main__":
    unittest.main()
