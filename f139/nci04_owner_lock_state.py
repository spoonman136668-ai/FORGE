"""Canonical in-process original F139 owner lock registry.

The original controller can execute as both __main__ (python -m) and
f139.local_controller (imported by the preflight/receipt verifier). Both
identities MUST observe one registry, but membership is still granted only
by SingleOwner.__enter__ AFTER a successful kernel file lock.
This module does not create or acquire another lock or controller.
"""
HELD_PATHS: set[str] = set()
