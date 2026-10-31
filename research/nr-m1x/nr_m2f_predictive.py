"""NR-M2F source-only selected-feedback predictive state; not native MG19 science.
Full public observations are validated by the pinned NR-M2E admission function.
Exact-public conditional empirical predictor; abstains on missing or contradictory evidence.
"""
import hashlib
import json
from collections import Counter

SCHEMA = "nr-m2f.selected-public-conditional.v1"
MAX_EVENTS = 896
MAX_BYTES = 700000

def canonical(x):
    return json.dumps(x, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

class SelectedPublicPredictor:
    def __init__(self, admission):
        self.admission = admission
        self.events = []
        self.pending = None
        self.last = None
        self.episodes = 0
        self.selected_total = 0
        self.evicted = 0

    def begin(self, public):
        if self.pending is not None:
            raise ValueError("PENDING_SELECTED_ACTION")
        self.last = self.admission(public)
        self.episodes += 1

    def select(self, before, action):
        before = self.admission(before)
        if self.last is None or self.pending is not None or canonical(before) != canonical(self.last):
            raise ValueError("OUT_OF_ORDER_SELECTED_ACTION")
        if type(action) is not int or action not in range(7):
            raise ValueError("INVALID_ORIGINAL_ACTION")
        self.pending = (before, action)

    def feedback(self, before, action, returned):
        before = self.admission(before)
        returned = self.admission(returned)
        if self.pending is None or self.pending[1] != action or canonical(self.pending[0]) != canonical(before):
            raise ValueError("NOT_SELECTED_FEEDBACK")
        if before["mission"] != returned["mission"]:
            raise ValueError("MISSION_DRIFT")
        self.events.append([before, action, returned])
        if len(self.events) > MAX_EVENTS:
            self.events.pop(0)
            self.evicted += 1
        self.selected_total += 1
        self.pending = None
        self.last = returned

    def predict(self, before, action):
        before = self.admission(before)
        if type(action) is not int or action not in range(7):
            raise ValueError("INVALID_ORIGINAL_ACTION")
        samples = [after for b, a, after in self.events if a == action and canonical(b) == canonical(before)]
        if len(samples) < 2:
            return None, {"supported": False, "reason": "INSUFFICIENT_SELECTED_EVIDENCE", "n": len(samples)}
        counts = Counter(canonical(after) for after in samples)
        if len(counts) != 1:
            return None, {"supported": False, "reason": "CONTRADICTORY_SELECTED_EFFECTS", "n": len(samples)}
        after = json.loads(next(iter(counts)))
        return after, {"supported": True, "n": len(samples),
                       "no_effect": canonical(after) == canonical(before)}

    def forecast(self, before, actions):
        if type(actions) not in (list, tuple) or not 1 <= len(actions) <= 5:
            raise ValueError("INVALID_FORECAST_LENGTH")
        current = self.admission(before)
        for action in actions:
            current, evidence = self.predict(current, action)
            if not evidence["supported"]:
                return None, evidence
        return current, {"supported": True, "steps": len(actions)}

    def checkpoint(self):
        if self.pending is not None:
            raise ValueError("PENDING_CHECKPOINT")
        body = {"schema": SCHEMA, "events": self.events, "last": self.last,
                "episodes": self.episodes, "selected_total": self.selected_total, "evicted": self.evicted}
        raw = canonical(body)
        if len(raw) > MAX_BYTES:
            raise ValueError("CHECKPOINT_CAP")
        return raw

    @classmethod
    def restore(cls, admission, raw, trusted_sha):
        if type(raw) is not bytes or len(raw) > MAX_BYTES or sha(raw) != trusted_sha:
            raise ValueError("UNTRUSTED_CHECKPOINT")
        try:
            obj = json.loads(raw)
            if canonical(obj) != raw or set(obj) != {"schema", "events", "last", "episodes", "selected_total", "evicted"} or obj["schema"] != SCHEMA:
                raise ValueError("INVALID_CHECKPOINT_SCHEMA")
            state = cls(admission)
            state.events = obj["events"]
            state.last = obj["last"]
            state.episodes = obj["episodes"]
            state.selected_total = obj["selected_total"]
            state.evicted = obj["evicted"]
            if (type(state.episodes) is not int or state.episodes < 0 or
                type(state.selected_total) is not int or type(state.evicted) is not int or
                not 0 <= state.evicted <= state.selected_total or
                state.selected_total != state.evicted + len(state.events) or
                len(state.events) > MAX_EVENTS):
                raise ValueError("BAD_CUSTODY_COUNTERS")
            if state.last is not None:
                state.last = admission(state.last)
            for event in state.events:
                if type(event) is not list or len(event) != 3 or type(event[1]) is not int or event[1] not in range(7):
                    raise ValueError("BAD_SELECTED_EVENT")
                event[0] = admission(event[0]); event[2] = admission(event[2])
                if event[0]["mission"] != event[2]["mission"]:
                    raise ValueError("MISSION_DRIFT")
            if state.checkpoint() != raw:
                raise ValueError("RESTORE_NOT_EXACT")
            return state
        except (ValueError, TypeError, KeyError, OverflowError, UnicodeError) as exc:
            raise ValueError("CHECKPOINT_REJECTED") from exc
