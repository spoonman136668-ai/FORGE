"""NR-M2D source-only full public source-selection transport.

Wraps the literal original pinned R10 DoorKey public adapter. No MiniGrid
environment, policy, world model, action remapping, reward inference, or
compressed source representation. This is NOT MG19 multi-mission admission.
"""
import hashlib
from nr_m2d_pinned_original_public import (
    DoorKeyPublicAdapter, ACTION_NAMES, canonical, digest, public_observation,
)

R10_ORIGINAL_GIT_BLOB = "3917d36ce9f86a2c1b998a0a2f93fb27674a9205"

class ExactPublicSevenActionBridge:
    def __init__(self):
        self._native = DoorKeyPublicAdapter()
        self._pending_before = None
        self._pending_action = None

    def begin_episode(self, full_public):
        if self._pending_action is not None:
            raise ValueError("NRM2D_OUTSTANDING_ORIGINAL_SELECTED_ACTION")
        self._native.reset_public(full_public)

    def commit(self, before, selected_action):
        frame=public_observation(before)
        if self._native.current is None or digest(frame)!=digest(self._native.current):
            raise ValueError("NRM2D_UNMATCHED_FULL_PUBLIC_BEFORE")
        if self._pending_action is not None:
            raise ValueError("NRM2D_DUPLICATE_SELECTION")
        # The original R10 source adapter owns native 0..6 action identity.
        selected=self._native.submit(selected_action)
        if selected is not selected_action and selected != selected_action:
            raise ValueError("NRM2D_INVALID_SOURCE_ACTION_REMAP")
        self._pending_before=frame
        self._pending_action=selected

    def feedback(self, before, selected_action, returned_full_public,
                 reward=0.0, terminated=False, truncated=False):
        frame=public_observation(before)
        after=public_observation(returned_full_public)
        if (self._pending_action is None or selected_action!=self._pending_action
            or self._pending_before is None
            or digest(frame)!=digest(self._pending_before)):
            raise ValueError("NRM2D_UNCHOSEN_OR_UNMATCHED_ORIGINAL_FEEDBACK")
        prior=self._pending_before
        original_event=self._native.complete(after,reward,terminated,truncated)
        self._pending_before=None
        self._pending_action=None
        if (original_event["action"]!=selected_action
            or original_event["before_public_sha256"]!=digest(prior)
            or original_event["after_public_sha256"]!=digest(after)):
            raise ValueError("NRM2D_SOURCE_LEDGER_INTEGRITY")
        return {
            "schema":"nr-m2d.exact-public-completed-selected-v1",
            "selected_action":selected_action,
            "selected_action_name":ACTION_NAMES[selected_action],
            "public_before":canonical(prior),
            "public_after":canonical(after),
            "public_before_sha256":original_event["before_public_sha256"],
            "public_after_sha256":original_event["after_public_sha256"],
            "original_event":original_event,
        }

    def checkpoint(self):
        if self._pending_action is not None:
            raise ValueError("NRM2D_PENDING_SELECTED_ACTION")
        return self._native.checkpoint()

    @classmethod
    def restore(cls, raw, trusted_sha256):
        if (type(raw) is not bytes or type(trusted_sha256) is not str
            or hashlib.sha256(raw).hexdigest()!=trusted_sha256):
            raise ValueError("NRM2D_EXTERNAL_SOURCE_IDENTITY_FAILURE")
        result=cls()
        result._native=DoorKeyPublicAdapter.restore(raw)
        return result
