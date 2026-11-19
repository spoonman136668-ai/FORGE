"""No-network, read-only manual-phase request contract negatives."""
from __future__ import annotations

import json
import unittest

from f139.nci04_phase_manual_intent import (
    ManualPhaseDenied, PREFIX, SCHEMA, ISSUE_URL, OWNER_ID, inspect_comment,
)

SOURCE = "c06403c8b6035c6c7013866a7ea08cef1244b507"
EPOCH = 41


def intent(*, mode="AUTO", lane=None, source=SOURCE, epoch=EPOCH):
    return {"schema": SCHEMA, "owner_source_sha": source,
            "owner_epoch": epoch, "mode": mode, "lane": lane}


def comment(payload=None):
    if payload is None:
        payload = intent()
    return {"id": 987654321, "issue_url": ISSUE_URL,
            "user": {"login": "spoonman136668-ai", "id": OWNER_ID},
            "author_association": "OWNER",
            "created_at": "2026-11-18T23:59:00Z",
            "updated_at": "2026-11-18T23:59:00Z",
            "body": PREFIX + json.dumps(payload, sort_keys=True,
                                        separators=(",", ":"))}


def inspect(raw, *, source=SOURCE, protected=SOURCE, epoch=EPOCH,
            consumed=frozenset()):
    return inspect_comment(comment=raw, installed_source_sha=source,
                           protected_main_sha=protected, owner_epoch=epoch,
                           consumed_comment_ids=consumed)


class ManualPhaseIntentTests(unittest.TestCase):
    def test_all_five_modes_can_be_described_without_authority(self):
        for mode in ("AUTO", "RESEARCH", "TRAIN", "SELF_IMPROVE", "HOLD"):
            with self.subTest(mode=mode):
                r = inspect(comment(intent(mode=mode)))
                self.assertEqual(r["mode"], mode)
                self.assertFalse(r["owner_admitted"])
                self.assertFalse(r["dispatch_authorized"])
                self.assertFalse(r["scientific_first_use"])
                self.assertFalse(r["self_source_mutation"])
                self.assertFalse(r["checkpoint_mutation"])
                self.assertFalse(r["accepted_ref_mutation"])

    def test_lane_specific_mode_is_only_advisory(self):
        r = inspect(comment(intent(mode="TRAIN", lane="Yggdrasil")))
        self.assertEqual((r["mode"], r["lane"]), ("TRAIN", "Yggdrasil"))
        self.assertFalse(r["dispatch_authorized"])

    def test_wrong_operator_or_user_id_denied(self):
        for key, value in (("login", "untrusted"), ("id", OWNER_ID + 1)):
            with self.subTest(key=key):
                raw = comment()
                raw["user"][key] = value
                with self.assertRaises(ManualPhaseDenied):
                    inspect(raw)

    def test_wrong_author_association_denied(self):
        raw = comment()
        raw["author_association"] = "CONTRIBUTOR"
        with self.assertRaises(ManualPhaseDenied):
            inspect(raw)

    def test_comment_on_other_issue_denied(self):
        raw = comment()
        raw["issue_url"] = ISSUE_URL.replace("/807", "/808")
        with self.assertRaises(ManualPhaseDenied):
            inspect(raw)

    def test_comment_edit_and_malformed_timestamp_denied(self):
        for value in ("2026-11-19T00:00:00Z", "not-a-time"):
            with self.subTest(value=value):
                raw = comment()
                raw["updated_at"] = value
                with self.assertRaises(ManualPhaseDenied):
                    inspect(raw)

    def test_original_source_and_protected_main_must_agree(self):
        bad = "b" * 40
        for opts in ({"source": bad}, {"protected": bad}):
            with self.subTest(opts=opts):
                with self.assertRaises(ManualPhaseDenied):
                    inspect(comment(), **opts)

    def test_old_source_and_epoch_in_payload_denied(self):
        for payload in (intent(source="b" * 40), intent(epoch=42)):
            with self.subTest(payload=payload):
                with self.assertRaises(ManualPhaseDenied):
                    inspect(comment(payload))

    def test_replay_consume_set_must_be_verified_upstream(self):
        raw = comment()
        with self.assertRaises(ManualPhaseDenied):
            inspect(raw, consumed=frozenset({raw["id"]}))
        with self.assertRaises(ManualPhaseDenied):
            inspect(raw, consumed={raw["id"]})

    def test_higher_privilege_fields_denied(self):
        payload = intent(mode="TRAIN")
        payload["scientific_first_use"] = True
        with self.assertRaises(ManualPhaseDenied):
            inspect(comment(payload))

    def test_hold_cannot_target_one_lane(self):
        with self.assertRaises(ManualPhaseDenied):
            inspect(comment(intent(mode="HOLD", lane="Wingless")))

    def test_self_improvement_cannot_be_relabelled_as_native_lane(self):
        with self.assertRaises(ManualPhaseDenied):
            inspect(comment(intent(mode="SELF_IMPROVE", lane="TTT-Hybrid")))

    def test_unknown_mode_and_lane_denied(self):
        for payload in (intent(mode="DEPLOY"), intent(mode="train"),
                        intent(lane="FORGE")):
            with self.subTest(payload=payload):
                with self.assertRaises(ManualPhaseDenied):
                    inspect(comment(payload))

    def test_duplicate_json_key_denied(self):
        raw = comment()
        raw["body"] = PREFIX + '{"schema":"' + SCHEMA + '",' \
            '"schema":"' + SCHEMA + '","owner_source_sha":"' + SOURCE + \
            '","owner_epoch":41,"mode":"AUTO","lane":null}'
        with self.assertRaises(ManualPhaseDenied):
            inspect(raw)

    def test_oversize_and_prefix_typos_denied(self):
        for body in ("F139-STEER-V2 " + json.dumps(intent()),
                     PREFIX + "X" * 600):
            with self.subTest(body=body[:30]):
                raw = comment()
                raw["body"] = body
                with self.assertRaises(ManualPhaseDenied):
                    inspect(raw)

    def test_malformed_epoch_and_consumed_ids_denied(self):
        raw = comment()
        for args in ({"epoch": True}, {"consumed": frozenset({True})},
                     {"consumed": frozenset({0})}):
            with self.subTest(args=args):
                with self.assertRaises(ManualPhaseDenied):
                    inspect(raw, **args)


if __name__ == "__main__":
    unittest.main()
