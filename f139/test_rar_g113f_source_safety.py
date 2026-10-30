"""RAR-G113F source-only safety regression: NEVER run a Windows native child.

These tests inspect the dormant C# one-shot probe. They do not compile or
execute the native fixture and cannot establish that nested-job admission,
the Windows ABI, or CPU/commit accounting works on a real runner.
"""
from pathlib import Path
import unittest


SOURCE = Path(__file__).with_name("RARG113FOneShotWindowsJob.cs")


class RARG113FSourceSafety(unittest.TestCase):
    def setUp(self):
        self.source = SOURCE.read_text(encoding="utf-8")

    def test_manual_only_fixed_noop_and_no_arbitrary_model_input(self):
        self.assertIn('args.Length != 1 || args[0] != "--run-one-shot-offline"', self.source)
        self.assertIn("RAR_G113F_NOT_EXECUTED_EXPLICIT_ONE_SHOT_FLAG_REQUIRED", self.source)
        self.assertIn('Path.Combine(systemDirectory, "cmd.exe")', self.source)
        self.assertIn(' /d /q /c exit 0', self.source)
        self.assertNotIn('Process.Start(', self.source)
        self.assertNotIn('args[1]', self.source)
        self.assertNotIn('ProcessStartInfo', self.source)
        self.assertNotIn("http://", self.source)
        self.assertNotIn("https://", self.source)

    def test_native_job_assign_happens_before_child_resume(self):
        src = self.source
        creation = src.index("CreateJobObject(IntPtr.Zero, null)")
        policy = src.index("SetInformationJobObject(job, JobObjectExtendedLimitInformation,")
        child = src.index("Require(CreateProcess(executable,")
        assignment = src.index("Require(AssignProcessToJobObject(job, child.hProcess),")
        resumed = src.index("ResumeThread(child.hThread)")
        waited = src.index("WaitForSingleObject(child.hProcess, TimeoutMilliseconds)")
        read = src.index("Query<BASIC_ACCOUNTING>(job, JobObjectBasicAccountingInformation)")
        self.assertLess(creation, policy)
        self.assertLess(policy, child)
        self.assertLess(child, assignment)
        self.assertLess(assignment, resumed)
        self.assertLess(resumed, waited)
        self.assertLess(waited, read)
        self.assertIn("if (created && !assigned) TerminateProcess(child.hProcess, 1)", src)
        self.assertIn("Close(ref job);", src)
        self.assertIn("JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE", src)
        self.assertIn("JOB_OBJECT_LIMIT_BREAKAWAY_OK", src)
        self.assertIn("JOB_OBJECT_LIMIT_SILENT_BREAKAWAY_OK", src)
        self.assertIn("TimeoutMilliseconds = 10000", src)

    def test_diagnostic_output_never_promotes_resource_or_science(self):
        src = self.source
        for string in (
            r'\"classification\":\"NATIVE_FIXED_NOOP_UNWITNESSED_NOT_TRAINING_COST\"',
            r'\"memory_semantics\":\"JOB_PEAK_COMMIT_NOT_PHYSICAL_TREE_RSS\"',
            r'\"experiment_scope_authenticated_externally\":false',
            r'\"all_descendant_lifetimes_independently_witnessed\":false',
            r'\"native_training_cost_qualified\":false',
            r'\"scientific_first_use_authorized\":false',
            r'\"model_or_training_executed\":false',
            r'\"original_controller_changed\":false',
        ):
            with self.subTest(string=string):
                self.assertIn(string, src)


if __name__ == "__main__":
    unittest.main()
