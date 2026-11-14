"""Public Hybrid CPU wheel lock and pre-execution guard negative controls."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from f139.public_hybrid_cpu_runtime import (
    PublicHybridRuntimeDenied, RECEIPT_SCHEMA, REQUIREMENTS,
    LOCK_NAME, command, read_lock, safe_env,
)


class PublicHybridCpuRuntimeTests(unittest.TestCase):
    def lock_path(self):
        return Path(__file__).with_name(LOCK_NAME)

    def test_exact_both_platform_frozen_locks_precede_install(self):
        for platform, expected_count, expected_hash in (
            ("linux", 14,
             "f991229a44ddff8d25d420ddeb5a279495014f8e11931bd179e9447e94cf7644"),
            ("windows", 15,
             "f933cb908072ee32aee1894e42f89f95d0b79353fa60542ddcb1496b5ab7ad86"),
        ):
            with self.subTest(platform=platform):
                row = read_lock(self.lock_path(), platform_name=platform)
                self.assertEqual(row["wheel_count"], expected_count)
                self.assertEqual(row["wheel_lock_sha256"], expected_hash)
                self.assertEqual([x["name"] for x in row["wheels"]],
                                 sorted(x["name"] for x in row["wheels"]))
                versions = {x["name"]: x["version"] for x in row["wheels"]}
                self.assertEqual(versions["torch"], "2.5.1+cpu")
                self.assertEqual(versions["pytest"], "8.3.4")
                self.assertEqual(versions["numpy"], "1.26.4")
                self.assertFalse(any(x.startswith("nvidia-") for x in versions))
                self.assertLessEqual(row["total_wheel_bytes"], 512*1024**2)
        self.assertEqual(REQUIREMENTS["python"], "3.11.11")
        self.assertEqual(REQUIREMENTS["uv"], "0.9.5")
        self.assertTrue(RECEIPT_SCHEMA.endswith("runtime-qualified.v1"))

    def test_lock_tamper_wrong_visibility_and_platform_fail_closed(self):
        self.assertRaisesRegex(PublicHybridRuntimeDenied, "PLATFORM_FORBIDDEN",
                               read_lock, self.lock_path(), platform_name="darwin")
        original = json.loads(self.lock_path().read_text(encoding="utf-8"))
        mutations = []
        doc = copy.deepcopy(original)
        doc["requirements"]["python"] = "3.11.18"
        mutations.append(("LOCK_IDENTITY", doc))
        doc = copy.deepcopy(original)
        doc["platforms"]["windows"]["wheels"][0]["sha256"] = "0"*64
        mutations.append(("LOCK_WHEEL_SET_OR_DIGEST", doc))
        doc = copy.deepcopy(original)
        doc["platforms"]["linux"]["wheel_count"] = 1
        mutations.append(("LOCK_PLATFORM_FIELDS", doc))
        doc = copy.deepcopy(original)
        doc["platforms"]["linux"]["wheels"][0]["name"] = "nvidia-driver"
        mutations.append(("LOCK_WHEEL_IDENTITY", doc))
        doc = copy.deepcopy(original)
        doc["platforms"]["linux"]["wheels"].append(
            copy.deepcopy(doc["platforms"]["linux"]["wheels"][0]))
        doc["platforms"]["linux"]["wheel_count"] += 1
        mutations.append(("LOCK_WHEEL_IDENTITY", doc))
        doc = copy.deepcopy(original)
        doc["platforms"]["linux"]["wheels"][0]["filename"] = "../bad.whl"
        mutations.append(("LOCK_WHEEL_IDENTITY", doc))
        for code, mutated in mutations:
            with self.subTest(code=code), tempfile.TemporaryDirectory() as td:
                path = Path(td) / "lock.json"
                path.write_text(json.dumps(mutated), encoding="utf-8")
                with self.assertRaisesRegex(PublicHybridRuntimeDenied, code):
                    read_lock(path, platform_name="linux")
        duplicate = self.lock_path().read_text().replace(
            '"schema": "forge.f139.hybrid.public-cpu-wheelhouse-lock.v1",',
            '"schema": "forge.f139.hybrid.public-cpu-wheelhouse-lock.v1",'
            '\n  "schema": "forge.f139.hybrid.public-cpu-wheelhouse-lock.v1",', 1)
        with tempfile.TemporaryDirectory() as td:
            path = Path(td)/"duplicate.json"
            path.write_text(duplicate, encoding="utf-8")
            with self.assertRaisesRegex(PublicHybridRuntimeDenied,
                                        "LOCK_DUPLICATE_KEY"):
                read_lock(path, platform_name="linux")

    def test_dependency_subprocess_excludes_all_worker_credentials(self):
        source = {
            "PATH": "/bin:/usr/bin", "HOME": "/tmp",
            "GH_TOKEN": "sensitive", "GITHUB_TOKEN": "sensitive",
            "F139_WORKER_HMAC_KEY": "sensitive",
            "OPENAI_API_KEY": "sensitive",
            "ACTIONS_RUNTIME_TOKEN": "sensitive",
            "F139_NATIVE_BUNDLE": "candidate-payload",
            "PYTHONPATH": "/untrusted",
        }
        env = safe_env(source)
        self.assertEqual(env["PATH"], source["PATH"])
        self.assertEqual(env["PYTHONDONTWRITEBYTECODE"], "1")
        self.assertEqual(env["PIP_NO_INPUT"], "1")
        for name in source:
            if name not in {"PATH", "HOME"}:
                self.assertNotIn(name, env)

    def test_argv_malformed_rejected_without_spawning_any_process(self):
        with tempfile.TemporaryDirectory() as td, patch(
            "f139.public_hybrid_cpu_runtime.subprocess.run") as run:
            for argv in ([], ["python", "\nunsafe"], ["python"]*33,
                         ["python", 33]):
                with self.subTest(argv=argv), self.assertRaisesRegex(
                    PublicHybridRuntimeDenied, "TRUSTED_ARGV"):
                    command(argv, directory=Path(td), timeout=10, env={})
            run.assert_not_called()

    def test_worker_retains_original_hmac_and_fixed_full_test_gate(self):
        worker = Path(__file__).resolve().parents[1] / (
            ".github/workflows/forge-f139-development-worker.yml")
        source = worker.read_text(encoding="utf-8")
        native = source[source.index("  native-execute:\n"):
                        source.index("  native-authorize-v2:\n")]
        self.assertIn("native-authorize", native)
        self.assertIn("F139_NATIVE_AUTHENTICATION_PASSED: 'true'", native)
        self.assertIn("python -B -m f139.nci04_worker_entry execute", native)
        self.assertIn("F139_NCI04_SOURCE_BOUND_NATIVE_QUALIFICATION=PASS", native)
        self.assertIn("f139.public_hybrid_cpu_runtime", native)
        self.assertIn("astral-sh/setup-uv@a02a550bdd3185dba2ebb6aa98d77047ce54ad21",
                      native)
        self.assertIn("version: '0.9.5'", native)
        self.assertIn("--source-sha $env:F139_SOURCE_SHA", native)
        self.assertIn("F139_HYBRID_CPU_RUNTIME=", native)


if __name__ == "__main__":
    unittest.main()
