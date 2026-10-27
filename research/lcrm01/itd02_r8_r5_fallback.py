"""Shared R5 fallback: native R5 is authoritative for all unmatched turns.

A fallback call must come from a live R5 bridge with pending feedback custody.
The statistical control can override only eligible turns; the bridge must
support externally chosen actions before it can be used in that mode.
"""
class NativeR5Fallback:
    def __init__(self,bridge):
        self.bridge=bridge
        self.pending=None

    def begin_episode(self):
        self.bridge.request("episode_start")
        self.pending=None

    def choose(self,state,wire):
        if self.pending is not None:
            raise ValueError("R5_FALLBACK_UNSETTLED_ACTION")
        action=self.bridge.request("choose",before=wire)["action"]
        if type(action) is not int or action not in (0,1,2):
            raise ValueError("R5_FALLBACK_ILLEGAL_ACTION")
        self.pending=(wire,action)
        return action

    def feedback(self,wire,action,after):
        if self.pending!=(wire,action):
            raise ValueError("R5_FALLBACK_CUSTODY_MISMATCH")
        result=self.bridge.request("feedback",before=wire,action=action,after=after)
        self.pending=None
        return result

    def assert_override_supported(self):
        raise RuntimeError("R5_EXTERNAL_ACTION_OVERRIDE_NOT_QUALIFIED")
