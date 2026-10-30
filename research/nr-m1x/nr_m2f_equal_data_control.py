"""NR-M2F independent full-public categorical count comparator.
Source-only benchmark baseline; receives only committed selected feedback.
This is intentionally not a recurrent/model-based scientific control.
"""
import json
from collections import defaultdict, deque

class EqualDataCategorical:
    def __init__(self, admission, max_events=896):
        if max_events != 896:
            raise ValueError("FROZEN_EVENT_CAP")
        self.admission = admission
        self.events = deque(maxlen=max_events)
        self.seen = 0

    @staticmethod
    def key(state):
        return json.dumps(state, sort_keys=True, separators=(",", ":"), allow_nan=False)

    def observe_selected(self, before, action, returned):
        observed_before = self.admission(before)
        observed_after = self.admission(returned)
        if type(action) is not int or action not in range(7):
            raise ValueError("INVALID_SELECTED_ACTION")
        if observed_before["mission"] != observed_after["mission"]:
            raise ValueError("MISSION_DRIFT")
        self.events.append((self.key(observed_before), action, self.key(observed_after)))
        self.seen += 1

    def predict(self, before, action):
        observed_before = self.admission(before)
        if type(action) is not int or action not in range(7):
            raise ValueError("INVALID_ORIGINAL_ACTION")
        key = self.key(observed_before)
        counts = defaultdict(int)
        n = 0
        for b, a, after in self.events:
            if b == key and a == action:
                counts[after] += 1
                n += 1
        if n < 2:
            return None, {"supported": False, "reason": "INSUFFICIENT_SELECTED_EVIDENCE", "n": n}
        if len(counts) != 1:
            return None, {"supported": False, "reason": "CONTRADICTORY_SELECTED_EFFECTS", "n": n}
        after = json.loads(next(iter(counts)))
        return after, {"supported": True, "n": n, "no_effect": self.key(after) == key}
