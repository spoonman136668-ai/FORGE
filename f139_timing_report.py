"""Time the existing F139 unittest discovery without caching or changing tests.

Diagnostic-only: all discovered tests execute normally on every qualification.
"""
import time
import unittest
import sys


class TimingResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.durations = []
        self._began = None

    def startTest(self, test):
        self._began = time.perf_counter()
        super().startTest(test)

    def stopTest(self, test):
        if self._began is not None:
            self.durations.append((time.perf_counter() - self._began, test.id()))
            self._began = None
        super().stopTest(test)


def main():
    suite = unittest.defaultTestLoader.discover(start_dir="f139", pattern="test_*.py")
    discovered = suite.countTestCases()
    result = unittest.TextTestRunner(resultclass=TimingResult).run(suite)
    durations = sorted(result.durations, reverse=True)
    measured = sum(seconds for seconds, _ in durations)
    print(f"F139_TIMING_DISCOVERED={discovered}", file=sys.stderr)
    print(f"F139_TIMING_EXECUTED={result.testsRun}", file=sys.stderr)
    print(f"F139_TIMING_MEASURED_TEST_SECONDS={measured:.3f}", file=sys.stderr)
    for rank, (seconds, test_id) in enumerate(durations[:20], 1):
        print(f"F139_TIMING_TOP_{rank:02d}={seconds:.3f}s {test_id}", file=sys.stderr)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
