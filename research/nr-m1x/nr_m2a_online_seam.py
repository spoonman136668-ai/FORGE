"""NR-M2A engineering-only, source-neutral selected-feedback adaptation seam.

No source/original world interaction. Uses exact pinned R7 merely as an
immutable historic reference. The online layer is a conventional public-state
categorical count learner, not a novel native causal architecture.
"""
from collections import Counter
import hashlib
import json

from nr_m1z_pinned_r7 import NonlinearLocalLearner

SCHEMA = "forge.nr-m2a.source-selected-online-overlay.dev.v1"
R7_SOURCE_BLOB = "204ecd993b954b23e66d6d1e8b3568e7c93183c5"
MAX_CONTEXTS = 64
WINDOW = 8
MAX_EVENTS = 4096
MAX_STEPS = 8
MAX_CHECKPOINT = 25000

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("utf-8")

def checksum(value):
    return hashlib.sha256(value).hexdigest()

def legal_public(value):
    return type(value) is int and 0 <= value < 256

def legal_action(value):
    return type(value) is int and 0 <= value <= 2

class SelectedOnlineSeam:
    """Explicit source-action custody. No future outcome or external world ID."""
    def __init__(self, base):
        if type(base) is not NonlinearLocalLearner or not base.models or base.source:
            raise ValueError("NRM2A_REQUIRES_FROZEN_AUTHENTIC_R7_BASE")
        self._base_blob = base.checkpoint()
        self._base_sha = checksum(self._base_blob)
        self.rows = {}
        self.episode = False
        self.pending = None
        self.events = 0

    def begin_episode(self):
        if self.pending is not None:
            raise ValueError("NRM2A_UNCOMMITTED_SELECTED_ACTION")
        # The new episode may have unfamiliar dynamics. Never carry over
        # confidence based on old context; immutable R7 is retained.
        self.rows = {}
        self.episode = True

    def commit(self, public_before, selected_action):
        if not self.episode or self.pending is not None:
            raise ValueError("NRM2A_SOURCE_SELECTION_SEQUENCE_REJECTED")
        if not legal_public(public_before) or not legal_action(selected_action):
            raise ValueError("NRM2A_BAD_PUBLIC_ACTION")
        self.pending = (public_before, selected_action)

    def feedback(self, public_before, selected_action, public_after):
        if not (legal_public(public_before) and legal_action(selected_action)
                and legal_public(public_after)):
            raise ValueError("NRM2A_INVALID_SOURCE_FEEDBACK")
        if self.pending != (public_before, selected_action):
            raise ValueError("NRM2A_UNMATCHED_SELECTED_FEEDBACK")
        key = (public_before, selected_action)
        if self.events >= MAX_EVENTS or (key not in self.rows
                                         and len(self.rows) >= MAX_CONTEXTS):
            raise ValueError("NRM2A_SOURCE_MEMORY_CAP_FAIL_CLOSED")
        values = self.rows.setdefault(key, [])
        values.append(public_after)
        if len(values) > WINDOW:
            del values[0]
        self.events += 1
        self.pending = None

    def step(self, public_before, action):
        if not legal_public(public_before) or not legal_action(action):
            raise ValueError("NRM2A_BAD_FORECAST_QUERY")
        # Beta(1,1) posterior on the most frequently observed exact AFTER.
        # This is a conservative observation cache, NOT a causal world model.
        obs = self.rows.get((public_before, action), ())
        if not self.episode or len(obs) < 3:
            return None, False
        counts = Counter(obs)
        top = counts.most_common()
        if len(top) > 1 and top[0][1] == top[1][1]:
            return None, False
        winner, k = top[0]
        if 4 * (k + 1) < 3 * (len(obs) + 2):
            return None, False
        return winner, True

    def forecast(self, public_before, actions):
        if not legal_public(public_before) or type(actions) not in (tuple, list) or not 1 <= len(actions) <= MAX_STEPS:
            raise ValueError("NRM2A_BAD_FORECAST_SEQUENCE")
        state = public_before
        for action in actions:
            new, known = self.step(state, action)
            if not known:
                return None, False
            state = new
        return state, True

    def checkpoint(self):
        if self.pending is not None:
            raise ValueError("NRM2A_PENDING_ACTION_CANNOT_CHECKPOINT")
        body = {
            "schema": SCHEMA,
            "r7_git_blob": R7_SOURCE_BLOB,
            "base_snapshot": json.loads(self._base_blob),
            "base_sha256": self._base_sha,
            "episode": self.episode,
            "events": self.events,
            "rows": [[s, a, self.rows[(s, a)]] for s, a in sorted(self.rows)]
        }
        raw = canonical(body)
        wrapped = canonical({"body": body, "sha256": checksum(raw)})
        if len(wrapped) > MAX_CHECKPOINT:
            raise ValueError("NRM2A_SNAPSHOT_EXCEEDS_BUDGET")
        return wrapped

    @classmethod
    def restore(cls, raw, trusted_base_sha):
        if type(raw) is not bytes or not 0 < len(raw) <= MAX_CHECKPOINT:
            raise ValueError("NRM2A_UNTRUSTED_SNAPSHOT")
        try:
            obj = json.loads(raw)
            if set(obj) != {"body", "sha256"} or raw != canonical(obj):
                raise ValueError("NRM2A_NONCANONICAL_OR_MALFORMED")
            body = obj["body"]
            if set(body) != {"schema", "r7_git_blob", "base_snapshot",
                             "base_sha256", "episode", "events", "rows"}:
                raise ValueError("NRM2A_BAD_SCHEMA_FIELDS")
            if checksum(canonical(body)) != obj["sha256"] or body["schema"] != SCHEMA or body["r7_git_blob"] != R7_SOURCE_BLOB:
                raise ValueError("NRM2A_SNAPSHOT_AUTHENTICATION_FAILED")
            base_raw = canonical(body["base_snapshot"])
            if type(trusted_base_sha) is not str or checksum(base_raw) != trusted_base_sha or body["base_sha256"] != trusted_base_sha:
                raise ValueError("NRM2A_FOREIGN_OR_MUTATED_BASE")
            base = NonlinearLocalLearner.restore(base_raw)
            model = cls(base)
            if type(body["episode"]) is not bool or type(body["events"]) is not int or not 0 <= body["events"] <= MAX_EVENTS:
                raise ValueError("NRM2A_INVALID_SESSION_COUNTER")
            values = body["rows"]
            if type(values) is not list or len(values) > MAX_CONTEXTS:
                raise ValueError("NRM2A_CONTEXT_BUDGET")
            for row in values:
                if (type(row) is not list or len(row) != 3 or
                    not legal_public(row[0]) or not legal_action(row[1]) or
                    type(row[2]) is not list or not 1 <= len(row[2]) <= WINDOW or
                    not all(legal_public(v) for v in row[2])):
                    raise ValueError("NRM2A_INVALID_SELECTED_COUNTS")
                key = (row[0], row[1])
                if key in model.rows:
                    raise ValueError("NRM2A_DUPLICATE_CONTEXT")
                model.rows[key] = list(row[2])
            if (not body["episode"] and model.rows) or sum(len(v) for v in model.rows.values()) > body["events"]:
                raise ValueError("NRM2A_INCONSISTENT_SOURCE")
            model.episode = body["episode"]
            model.events = body["events"]
            if model.checkpoint() != raw:
                raise ValueError("NRM2A_RESTORED_IDENTITY_DRIFT")
            return model
        except (ValueError, TypeError, KeyError, OverflowError, UnicodeError) as e:
            raise ValueError("NRM2A_RESTORE_REJECTED") from e
