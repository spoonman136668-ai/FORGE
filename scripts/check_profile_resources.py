"""Focused diagnostics controls outside the original F139 test inventory."""
import io
import ctypes
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from f139.profile_resources import (
    ResourceSampler, resource_delta, telemetry_identity, IO_KEYS,
)
from f139.check_test_discovery_inventory import profile_suite, case_ids


def sample(cpu=100, io_value=10, idle=10, kernel=100, user=50):
    return dict(self_cpu_ns=cpu, process_io={k: io_value for k in IO_KEYS},
                host_cpu_100ns=dict(idle=idle, kernel_including_idle=kernel, user=user))


class ResourceControls(unittest.TestCase):
    def test_units_and_kernel_idle_overlap(self):
        result=resource_delta(sample(), sample(cpu=250, io_value=30, idle=20, kernel=120, user=70))
        self.assertEqual(result['self_cpu']['delta']['ns'], 150)
        self.assertEqual(result['process_io']['delta']['write_bytes'], 20)
        self.assertEqual(result['host_cpu_100ns']['delta']['busy'], 30)

    def test_missing_counters_are_not_zero_measurements(self):
        value=resource_delta(dict(self_cpu_ns=1), dict(self_cpu_ns=2))
        self.assertEqual(value['self_cpu']['status'], 'VERIFIED')
        for group in ('process_io', 'host_cpu_100ns'):
            self.assertEqual(value[group]['status'], 'UNVERIFIED')
            self.assertNotIn('delta', value[group])

    def test_regression_float_boolean_and_negative_rejected(self):
        for invalid in (-1, 99, 101.0, True, None):
            with self.subTest(value=invalid):
                self.assertEqual(resource_delta(sample(),sample(cpu=invalid))['self_cpu']['status'], 'UNVERIFIED')

    def test_io_schema_drift_rejected(self):
        a=sample(); b=sample(); b['process_io']['invented']=1
        self.assertEqual(resource_delta(a,b)['process_io']['status'], 'UNVERIFIED')

    def test_host_idle_inconsistent_rejected(self):
        for b in (sample(idle=200,kernel=120), sample(idle=40,kernel=120)):
            self.assertEqual(resource_delta(sample(),b)['host_cpu_100ns']['status'], 'UNVERIFIED')

    def test_failed_native_reads_keep_cpu_and_missing_dimensions(self):
        sampler=ResourceSampler()
        class Failing:
            def GetCurrentProcess(self): raise OSError('injected')
        sampler.api=Failing(); sampler.io_type=lambda: None
        a=sampler.sample(); b=sampler.sample()
        delta=resource_delta(a,b)
        self.assertEqual(delta['self_cpu']['status'],'VERIFIED')
        self.assertEqual(delta['process_io']['status'],'UNVERIFIED')

    def test_real_process_cpu_and_windows_io(self):
        sampler=ResourceSampler()
        a=sampler.sample()
        deadline=time.process_time_ns()+2_000_000
        while time.process_time_ns()<deadline: pass
        with tempfile.TemporaryDirectory() as directory:
            with (Path(directory)/'private-probe.bin').open('wb') as stream:
                stream.write(b'x'*32768); stream.flush(); os.fsync(stream.fileno())
            with (Path(directory)/'private-probe.bin').open('rb') as stream:
                self.assertEqual(len(stream.read()),32768)
        result=resource_delta(a,sampler.sample())
        self.assertEqual(result['self_cpu']['status'],'VERIFIED')
        self.assertGreater(result['self_cpu']['delta']['ns'],0)
        for group in ('process_io','host_cpu_100ns'):
            self.assertEqual(result[group]['status'],'VERIFIED' if os.name=='nt' else 'UNVERIFIED')
        if os.name=='nt':
            self.assertEqual(ctypes.sizeof(sampler.io_type),48)
            self.assertEqual(ctypes.sizeof(sampler.filetime_type),8)
            self.assertGreaterEqual(result['process_io']['delta']['read_bytes'],32768)
            self.assertGreaterEqual(result['process_io']['delta']['write_bytes'],32768)
            self.assertGreater(result['process_io']['delta']['write_operations'],0)

    def test_enabled_and_disabled_preserve_outcomes_order_and_skips(self):
        class Cases(unittest.TestCase):
            def test_ok(self): self.assertEqual(1,1)
            @unittest.skip('existing platform skip')
            def test_skip(self): pass
        def run(sampler):
            suite=unittest.defaultTestLoader.loadTestsFromTestCase(Cases)
            return profile_suite(suite,case_ids(suite),stream=io.StringIO(),resource_sampler=sampler)
        plain=run(None); observed=run(ResourceSampler())
        for key in ('successful','tests_run','failures','errors','skipped_ids','complete_inventory_and_order'):
            self.assertEqual(plain[key], observed[key])
        self.assertEqual([x['id'] for x in plain['cases']],[x['id'] for x in observed['cases']])
        self.assertTrue(all('resources' not in x for x in plain['cases']))
        self.assertTrue(all('resources' in x for x in observed['cases']))

    def test_identity_scope_and_environment_redaction(self):
        with patch.dict(os.environ, {'GOFLAGS':'secret arbitrary value','UNRELATED_SECRET':'never retain'}):
            identity=telemetry_identity()
        self.assertFalse(identity['child_process_resources_complete'])
        self.assertFalse(identity['cause_attribution_proven'])
        self.assertEqual(identity['environment']['GOFLAGS'],'REDACTED_NONCANONICAL')
        self.assertNotIn('UNRELATED_SECRET',str(identity))
        self.assertNotIn('secret arbitrary value',str(identity))


if __name__=='__main__': unittest.main(verbosity=2)
