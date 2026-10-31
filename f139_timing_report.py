"""Full F139 unittest discovery with diagnostic timing, never cached or skipped."""
import sys
import time
import unittest
from collections import defaultdict
from contextlib import ExitStack, contextmanager
from functools import wraps
from unittest.mock import patch

from f139.local_controller import Database


class TimingResult(unittest.TextTestResult):
    current_test_id = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.durations = []
        self.setup_durations = []
        self._began = None
        self._original_setup = None

    def startTest(self, test):
        TimingResult.current_test_id = test.id()
        self._began = time.perf_counter()
        # Instrument only this unittest instance; preserve fixture ownership,
        # call count, exceptions, cleanup and the original test ordering.
        original = test.setUp
        self._original_setup = original

        def timed_setup():
            begin = time.perf_counter()
            try:
                return original()
            finally:
                self.setup_durations.append((time.perf_counter() - begin, test.id()))

        test.setUp = timed_setup
        super().startTest(test)

    def stopTest(self, test):
        try:
            if self._began is not None:
                self.durations.append((time.perf_counter() - self._began, test.id()))
                self._began = None
        finally:
            TimingResult.current_test_id = None
            if self._original_setup is not None:
                test.setUp = self._original_setup
                self._original_setup = None
            super().stopTest(test)


def percentile(sorted_values, fraction):
    if not sorted_values:
        return 0.0
    # Nearest-rank percentile. No interpolation or numpy dependency.
    rank = max(1, (len(sorted_values) * fraction).__ceil__())
    return sorted_values[min(rank - 1, len(sorted_values) - 1)]


class DatabasePhaseTiming:
    """Observe isolated F139 Database operations; never change their outcomes."""
    def __init__(self):
        self.samples = defaultdict(list)

    def enter(self, stack):
        initialize = Database.initialize
        verify = Database.verify
        transaction = Database.transaction
        event = Database.event

        @wraps(initialize)
        def measured_initialize(cls, *args, **kwargs):
            start = time.perf_counter()
            try:
                return initialize(*args, **kwargs)
            finally:
                self.samples["initialize"].append(time.perf_counter() - start)

        @wraps(verify)
        def measured_verify(db, *args, **kwargs):
            start = time.perf_counter()
            try:
                return verify(db, *args, **kwargs)
            finally:
                self.samples["verify"].append(time.perf_counter() - start)

        @contextmanager
        @wraps(transaction)
        def measured_transaction(db, *args, **kwargs):
            # Mirrors Database.transaction exactly: BEGIN IMMEDIATE is outside
            # the protected body; COMMIT is inside it; any body/commit exception
            # triggers ROLLBACK and is re-raised. Only timing is added.
            begin_started = time.perf_counter()
            try:
                db.conn.execute("BEGIN IMMEDIATE")
            finally:
                self.samples["begin"].append(
                    (time.perf_counter() - begin_started, TimingResult.current_test_id))
            try:
                body_started = time.perf_counter()
                try:
                    yield db.conn
                finally:
                    self.samples["body"].append(
                        (time.perf_counter() - body_started, TimingResult.current_test_id))
                commit_started = time.perf_counter()
                try:
                    db.conn.execute("COMMIT")
                finally:
                    self.samples["commit"].append(
                        (time.perf_counter() - commit_started, TimingResult.current_test_id))
            except BaseException:
                rollback_started = time.perf_counter()
                try:
                    db.conn.execute("ROLLBACK")
                finally:
                    self.samples["rollback"].append(
                        (time.perf_counter() - rollback_started, TimingResult.current_test_id))
                raise

        @wraps(event)
        def measured_event(db, *args, **kwargs):
            start = time.perf_counter()
            try:
                return event(db, *args, **kwargs)
            finally:
                self.samples["event"].append(
                    (time.perf_counter() - start, TimingResult.current_test_id))

        stack.enter_context(patch.object(Database, "initialize", classmethod(measured_initialize)))
        stack.enter_context(patch.object(Database, "verify", measured_verify))
        stack.enter_context(patch.object(Database, "transaction", measured_transaction))
        stack.enter_context(patch.object(Database, "event", measured_event))


def main():
    suite = unittest.defaultTestLoader.discover(start_dir="f139", pattern="test_*.py")
    discovered = suite.countTestCases()
    phases = DatabasePhaseTiming()
    with ExitStack() as stack:
        phases.enter(stack)
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
    setup_by_module = defaultdict(list)
    for seconds, test_id in result.setup_durations:
        setup_by_module[test_id.rsplit(".", 2)[0]].append(seconds)
    print(f"F139_TIMING_SETUP_RECORDED={len(result.setup_durations)}", file=sys.stderr)
    for name in ("initialize", "verify"):
        samples = phases.samples[name]
        print(
            f"F139_TIMING_DB_{name.upper()}=count={len(samples)} "
            f"total={sum(samples):.3f}s", file=sys.stderr,
        )
    for name in ("begin", "body", "commit", "rollback", "transaction", "event"):
        samples = phases.samples[name]
        valid = [(seconds, test_id) for seconds, test_id in samples if test_id]
        by_module_phase = defaultdict(list)
        for seconds, test_id in valid:
            by_module_phase[test_id.rsplit(".", 2)[0]].append(seconds)
        print(
            f"F139_TIMING_DB_{name.upper()}_COUNT={len(samples)} "
            f"TOTAL={sum(seconds for seconds, _ in samples):.3f}s",
            file=sys.stderr,
        )
        for rank, (module, values) in enumerate(
            sorted(by_module_phase.items(), key=lambda item: (-sum(item[1]), item[0]))[:15], 1
        ):
            print(
                f"F139_TIMING_DB_{name.upper()}_MODULE_{rank:02d}="
                f"count={len(values)} total={sum(values):.3f}s module={module}",
                file=sys.stderr,
            )
    # Initialize may internally verify; phase totals are not additive.
    for rank, (module, samples) in enumerate(
        sorted(setup_by_module.items(), key=lambda item: (-sum(item[1]), item[0])), 1
    ):
        if rank > 30:
            break
        print(
            f"F139_TIMING_SETUP_MODULE_{rank:03d}="
            f"count={len(samples)} total={sum(samples):.3f}s module={module}",
            file=sys.stderr,
        )
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
