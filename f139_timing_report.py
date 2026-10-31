"""Full F139 unittest discovery with diagnostic timing, never cached or skipped."""
import sys
import time
import unittest
from collections import defaultdict


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


def percentile(sorted_values, fraction):
    if not sorted_values:
        return 0.0
    # Nearest-rank percentile. No interpolation or numpy dependency.
    rank = max(1, (len(sorted_values) * fraction).__ceil__())
    return sorted_values[min(rank - 1, len(sorted_values) - 1)]


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

    by_module = defaultdict(list)
    for seconds, test_id in durations:
        # unittest's stable qualified test id: module.Class.method
        by_module[test_id.rsplit(".", 2)[0]].append(seconds)
    print(f"F139_TIMING_MODULE_COUNT={len(by_module)}", file=sys.stderr)
    print(f"F139_TIMING_MODULE_TEST_COUNT={sum(map(len, by_module.values()))}", file=sys.stderr)
    for rank, (module, samples) in enumerate(
        sorted(by_module.items(), key=lambda item: (-sum(item[1]), item[0])), 1
    ):
        ordered = sorted(samples)
        print(
            f"F139_TIMING_MODULE_{rank:03d}="
            f"count={len(ordered)} total={sum(ordered):.3f}s "
            f"p50={percentile(ordered, 0.50):.3f}s "
            f"p95={percentile(ordered, 0.95):.3f}s max={ordered[-1]:.3f}s "
            f"module={module}",
            file=sys.stderr,
        )
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
