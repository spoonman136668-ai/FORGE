"""RAR-G113B deterministic non-executing OS admission and negative controls."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

from f139.rar_g113b_scope_admission import (
    current_host_admission_hint, linux_admission_hint, windows_admission_hint,
)


class RARG113BScopeAdmissionTests(unittest.TestCase):
    def test_actual_host_never_claims_exclusive_scope_or_spawns(self):
        result = current_host_admission_hint()
        for key in (
            "scope_creation_tested",
            "exclusive_experiment_membership_verified",
            "short_lived_descendants_accounted_for_exclusively",
            "full_native_training_cpu_rss_qualified",
            "scientific_first_use_authorized",
            "process_created", "scope_created",
            "original_controller_changed",
        ):
            self.assertIs(result[key], False, key)
        self.assertEqual(result["probe"], "RAR_G113B_READ_ONLY_SCOPE_ADMISSION")
        print("RAR_G113B_READ_ONLY_ADMISSION=" + json.dumps(result, sort_keys=True))

    def test_fixture_with_writable_cpu_memory_hints_still_denies_isolation(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            (root / "cgroup.controllers").write_text("cpu memory io")
            group = root / "tenant"
            group.mkdir()
            (group / "cgroup.procs").write_text("100\n200\n")
            (group / "cgroup.controllers").write_text("cpu memory\n")
            (group / "cgroup.subtree_control").write_text("cpu memory\n")
            membership = root / "membership"
            membership.write_text("0::/tenant\n")
            out = linux_admission_hint(root, membership, pid=100)
            self.assertTrue(out["current_scope_resolved"])
            self.assertTrue(out["current_process_direct_member"])
            self.assertTrue(out["cpu_memory_controllers_available"])
            self.assertTrue(out["cpu_memory_subtree_enabled"])
            self.assertFalse(out["scope_creation_tested"])
            self.assertFalse(out["exclusive_experiment_membership_verified"])
            self.assertFalse(out["full_native_training_cpu_rss_qualified"])

    def test_missing_controls_duplicate_membership_and_path_escape_fail_closed(self):
        with tempfile.TemporaryDirectory() as t, tempfile.TemporaryDirectory() as outside:
            root = Path(t)
            (root / "cgroup.controllers").write_text("cpu memory")
            group = root / "tenant"
            group.mkdir()
            (group / "cgroup.procs").write_text("100\n")
            (group / "cgroup.controllers").write_text("cpu\n")
            (group / "cgroup.subtree_control").write_text("cpu\n")
            membership = root / "membership"
            membership.write_text("0::/tenant\n")
            out = linux_admission_hint(root, membership, pid=100)
            self.assertFalse(out["cpu_memory_controllers_available"])
            self.assertFalse(out["cpu_memory_subtree_enabled"])
            membership.write_text("0::/tenant\n0::/tenant\n")
            out = linux_admission_hint(root, membership, pid=100)
            self.assertFalse(out["current_scope_resolved"])
            membership.write_text("0::/../outside\n")
            out = linux_admission_hint(root, membership, pid=100)
            self.assertFalse(out["current_scope_resolved"])
            (root / "escaped").symlink_to(Path(outside), target_is_directory=True)
            membership.write_text("0::/escaped\n")
            out = linux_admission_hint(root, membership, pid=100)
            self.assertFalse(out["current_scope_resolved"])

    def test_windows_exports_never_prove_nested_job_admission(self):
        out = windows_admission_hint()
        self.assertEqual(out["platform"], "win32")
        self.assertFalse(out["scope_creation_tested"])
        self.assertFalse(out["exclusive_experiment_membership_verified"])
        self.assertFalse(out["scientific_first_use_authorized"])
        self.assertFalse(out["process_created"])
        if sys.platform == "win32":
            self.assertIsInstance(out["windows_api_exports_present"], bool)
        else:
            self.assertFalse(out["windows_api_exports_present"])


if __name__ == "__main__":
    unittest.main()
