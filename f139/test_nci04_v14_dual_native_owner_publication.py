"""No-network integration: existing F139 owner handles BOTH native research lanes.

Source-only test of the previously merged V14 code. The Yggdrasil proposal is
authenticated first; on the next UTC day the same SQLite owner, publisher and
shared budget authenticate an isolated Wingless native Go draft. No live owner,
provider, runner dispatch, source mutation or scientific first-use.
"""
from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from f139 import test_nci04_candidate_publisher as fake_publisher
from f139.nci04_native_contract import WINGLESS_R8_TRAINING, canonical
from f139.nci04_owner_free_reasoner_proposal import (
    ATTEMPT, WINGLESS_R8_PARENT, select_bounded_free_lane, _attempts,
)
from f139.nci04_model_owner_publication import (
    ATTEMPT as DRAFT_ATTEMPT, SUCCESS as DRAFT_SUCCESS,
)
from f139.test_nci04_owner_free_reasoner_proposal import (
    NativeFreeReasonerCustodyTests,
)


GO_SOURCE = b"""package outcome

// TrainingSession mirrors an isolated native development example. Actual
// production target bytes are independently rechecked at the pinned Git SHA.
type TrainingSession struct {
    MaximumEpisodeSteps uint32
}
"""


class DualModelOwnerPublicationRehearsal(unittest.TestCase):
    def setUp(self):
        h = NativeFreeReasonerCustodyTests(
            "test_one_external_free_model_proposal_with_authenticated_draft")
        h.setUp()
        self.addCleanup(h.doCleanups)
        self.h = h

    def wingless_target(self):
        h = self.h
        self.assertEqual(select_bounded_free_lane(_attempts(h.db)), "Wingless")
        h.provider.repo = "spoonman136668-ai/Wingless"
        h.provider.path = WINGLESS_R8_TRAINING
        h.provider.parent = WINGLESS_R8_PARENT
        h.provider.parent_data = GO_SOURCE
        h.provider.head_data = None
        h.provider.head_sha = None
        h.provider.pr = None
        h.provider.reference = None
        patch_source = patch.object(fake_publisher, "SOURCE", GO_SOURCE)
        patch_source.start()
        self.addCleanup(patch_source.stop)

    def wingless_model(self, body: bytes, token: str) -> bytes:
        self.assertEqual(token, "fixture-unprinted")
        body_doc = json.loads(body)
        prompt = body_doc["messages"][1]["content"]
        packet = json.loads(prompt.split("\nProduce one bounded", 1)[0])
        self.assertEqual(packet["lane"], "Wingless")
        self.assertEqual(packet["target_commit"], WINGLESS_R8_PARENT)
        self.assertEqual(packet["path"], WINGLESS_R8_TRAINING)
        self.assertEqual(packet["public_source"], GO_SOURCE.decode())
        self.assertEqual(packet["retained_outcome_counts"], {"QUARANTINED": 1})
        self.assertNotIn(self.h.fixture.native.ticket, prompt)
        self.assertNotIn("QUALIFIED_NEGATIVE", prompt)
        return canonical({
            "choices": [{
                "finish_reason": "stop",
                "message": {"role": "assistant", "content": canonical({
                    "schema": "forge.f139.model-proposal.v1",
                    "lane": "Wingless",
                    "target_commit": WINGLESS_R8_PARENT,
                    "path": WINGLESS_R8_TRAINING,
                    "history_sha256": packet["history_sha256"],
                    "question": "Can native action evidence guide exploration?",
                    "hypothesis": "Trial counts retain useful uncertainty.",
                    "control": "Matched action budget and no private-world oracle.",
                    "candidate_source": GO_SOURCE.decode() +
                        "\n// Development-only source proposal\n",
                }).decode("ascii")},
            }],
            "usage": {"cost": 0},
        })

    def test_original_owner_authenticates_both_lanes_across_two_utc_days(self):
        h = self.h
        first = h.attempt()
        self.assertEqual(first["disposition"], "MODEL_DRAFT_AUTHENTICATED")
        self.assertEqual(_attempts(h.db)[0]["lane"], "Yggdrasil")
        self.wingless_target()
        second = h.attempt(
            lane="Wingless", target_commit=WINGLESS_R8_PARENT,
            path=WINGLESS_R8_TRAINING, transport=self.wingless_model,
            utc_day="2026-10-28")
        self.assertEqual(second["disposition"], "MODEL_DRAFT_AUTHENTICATED")
        self.assertEqual(second["paid_model_calls"], 0)
        self.assertFalse(second["scientific_first_use"])
        self.assertEqual([v["lane"] for v in _attempts(h.db)],
                         ["Yggdrasil", "Wingless"])
        self.assertEqual(len(h.rows(DRAFT_ATTEMPT)), 2)
        self.assertEqual(len(h.rows(DRAFT_SUCCESS)), 2)
        self.assertEqual(h.provider.pr["draft"], True)
        self.assertTrue(h.provider.pr["head"]["ref"].startswith(
            "f139/auto-model-w-"))
        self.assertEqual(h.provider.pr["head"]["repo"]["full_name"],
                         "spoonman136668-ai/Wingless")
        self.assertEqual(h.provider.head_data,
                         GO_SOURCE + b"\n// Development-only source proposal\n")
        self.assertEqual(select_bounded_free_lane(_attempts(h.db)),
                         "Yggdrasil")
        h.db.verify()

        # Release SHA changes are not new source outcomes. No third attempt.
        third = h.attempt(lane="Wingless", target_commit=WINGLESS_R8_PARENT,
                          path=WINGLESS_R8_TRAINING, transport=self.wingless_model,
                          utc_day="2026-10-29")
        self.assertEqual(third["disposition"],
                         "FREE_REASONER_SCOPE_ALREADY_ATTEMPTED_NO_REPLAY")
        self.assertEqual(len(h.rows(ATTEMPT)), 2)

    def test_shared_same_day_limit_blocks_wingless_before_any_second_write(self):
        h = self.h
        self.assertEqual(h.attempt()["disposition"], "MODEL_DRAFT_AUTHENTICATED")
        self.wingless_target()
        calls_before = len(h.calls)
        writes_before = len(h.provider.write_calls)
        old_head = h.db.meta()["head_hash"]
        second = h.attempt(
            lane="Wingless", target_commit=WINGLESS_R8_PARENT,
            path=WINGLESS_R8_TRAINING, transport=self.wingless_model,
            utc_day="2026-10-27")
        self.assertEqual(second["disposition"],
                         "FREE_REASONER_BOUNDED_BUDGET_EXHAUSTED")
        self.assertEqual(h.db.meta()["head_hash"], old_head)
        self.assertEqual(len(h.calls), calls_before)
        self.assertEqual(len(h.provider.write_calls), writes_before)
        self.assertEqual(len(h.rows(ATTEMPT)), 1)
        h.db.verify()


if __name__ == "__main__":
    unittest.main()
