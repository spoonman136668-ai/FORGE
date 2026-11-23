"""Regression for original Windows V20 cutover's __main__/canonical lock split."""
import pathlib
import runpy
import tempfile
import unittest

from f139.local_controller import SingleOwner as CanonicalSingleOwner
from f139.nci04_owner_lock_state import HELD_PATHS


class OriginalOwnerSharedLockTests(unittest.TestCase):
    def test_separate_controller_module_instances_share_only_actual_held_lock(self):
        # python -B -m f139.local_controller loads one copy as __main__, but
        # V20's verifier imports f139.local_controller as another module.
        shadow = runpy.run_module(
            "f139.local_controller", run_name="f139_original_cli_shadow"
        )
        ShadowSingleOwner = shadow["SingleOwner"]
        self.assertIsNot(ShadowSingleOwner, CanonicalSingleOwner)
        self.assertIs(ShadowSingleOwner._held_paths, HELD_PATHS)
        self.assertIs(CanonicalSingleOwner._held_paths, HELD_PATHS)
        with tempfile.TemporaryDirectory(prefix="f139-v20-lock-") as root:
            path = pathlib.Path(root) / "original-owner.lock"
            self.assertFalse(ShadowSingleOwner.held(path))
            self.assertFalse(CanonicalSingleOwner.held(path))
            with ShadowSingleOwner(path):
                # This previously failed: the canonical preflight could never
                # observe the live kernel lock from __main__.
                self.assertTrue(ShadowSingleOwner.held(path))
                self.assertTrue(CanonicalSingleOwner.held(path))
            self.assertFalse(ShadowSingleOwner.held(path))
            self.assertFalse(CanonicalSingleOwner.held(path))
            with CanonicalSingleOwner(path):
                self.assertTrue(ShadowSingleOwner.held(path))
            self.assertFalse(CanonicalSingleOwner.held(path))

    def test_registry_is_not_prepopulated_by_import(self):
        shadow = runpy.run_module(
            "f139.local_controller", run_name="f139_original_cli_shadow2"
        )
        with tempfile.TemporaryDirectory(prefix="f139-v20-unheld-") as root:
            path = pathlib.Path(root) / "unacquired.lock"
            self.assertFalse(shadow["SingleOwner"].held(path))
            self.assertFalse(CanonicalSingleOwner.held(path))
            self.assertNotIn(str(path.resolve()), HELD_PATHS)


if __name__ == "__main__":
    unittest.main()
