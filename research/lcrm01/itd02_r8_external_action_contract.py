"""Fail-closed admission for externally selected actions.

The original Wingless R8/R5 native policy exposes no supported external
action-custody operation. Never represent a statistical override as native R5.
"""
def require_external_action_custody(bridge, action, before):
    if type(action) is not int or action not in (0,1,2):
        raise ValueError("R8_EXTERNAL_ACTION_ILLEGAL")
    if bridge is None or before is None:
        raise ValueError("R8_EXTERNAL_ACTION_MISSING_SOURCE")
    raise RuntimeError("R8_NATIVE_EXTERNAL_ACTION_CUSTODY_NOT_IMPLEMENTED")
