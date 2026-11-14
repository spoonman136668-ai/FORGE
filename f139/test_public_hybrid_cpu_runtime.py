"""Public Hybrid CPU wheel lock and pre-execution guard negative controls."""
from __future__ import annotations

import copy
import hashlib
import io
import json
import os
import stat
import tarfile
import zipfile
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from f139.public_hybrid_cpu_runtime import (
    PublicHybridRuntimeDenied, RECEIPT_SCHEMA, REQUIREMENTS,
    LOCK_NAME, UV_RELEASE, _extract_exact_uv, pinned_managed_python,
    command, read_lock, safe_env,
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
        doc["platforms"]["linux"]["wheels"][0]["sha256"] = "0"*64
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

    def test_official_uv_release_digest_and_platform_pins(self):
        self.assertEqual(set(UV_RELEASE), {"linux", "windows"})
        for platform_name, expected_digest, expected_size in (
            ("linux", "2cf10babba653310606f8b49876cfb679928669e7ddaa1fb41fb00ce73e64f66",
             21370871),
            ("windows", "515dc53d7553f1357d0abc1f70acd921fbb9e30230b1d9a08737236daa6ee920",
             20760405),
        ):
            with self.subTest(platform_name=platform_name):
                meta = UV_RELEASE[platform_name]
                self.assertEqual(meta["sha256"], expected_digest)
                self.assertEqual(meta["size"], expected_size)
                self.assertLess(meta["size"], 32*1024*1024)

    def test_archive_extraction_only_fixed_uv_regular_member(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            win = root/"release.zip"
            with zipfile.ZipFile(win,"w") as z:
                z.writestr("uv-x86_64/uv.exe",b"safe-demo")
                z.writestr("uv-x86_64/uvx.exe",b"other")
            dest = root/"uv.exe"
            _extract_exact_uv(win,"windows",dest)
            self.assertEqual(dest.read_bytes(),b"safe-demo")
            symlink = root/"unsafe.zip"
            with zipfile.ZipFile(symlink,"w") as z:
                bad = zipfile.ZipInfo("uv.exe")
                bad.create_system = 3
                bad.external_attr = (stat.S_IFLNK | 0o777) << 16
                z.writestr(bad,b"target")
            with self.assertRaisesRegex(PublicHybridRuntimeDenied,"SYMLINK"):
                _extract_exact_uv(symlink,"windows",root/"untrusted.exe")
            tar = root/"release.tar.gz"
            with tarfile.open(tar,"w:gz") as t:
                raw=b"linux-demo"
                member=tarfile.TarInfo("uv-linux/uv")
                member.size=len(raw)
                member.mode=0o755
                t.addfile(member,io.BytesIO(raw))
            _extract_exact_uv(tar,"linux",root/"uv")
            self.assertEqual((root/"uv").read_bytes(),b"linux-demo")
            unsafe=root/"evil.tar.gz"
            with tarfile.open(unsafe,"w:gz") as t:
                member=tarfile.TarInfo("uv-linux/uv")
                member.type=tarfile.SYMTYPE
                member.linkname="/etc/shadow"
                t.addfile(member)
            with self.assertRaisesRegex(PublicHybridRuntimeDenied,"UNSAFE_MEMBER"):
                _extract_exact_uv(unsafe,"linux",root/"unsafe-uv")

    def test_uv_archive_must_match_frozen_hash_before_executable_creation(self):
        import urllib.request
        class FakeResponse(io.BytesIO):
            def geturl(self):
                return ("https://release-assets.githubusercontent.com/"
                        "fake-fixture-no-real-network")
        class FakeOpener:
            def __init__(self,data):
                self.data=data
            def open(self,*args,**kwargs):
                return FakeResponse(self.data)
        platform_name = "windows" if os.name == "nt" else "linux"
        wrong=b"not a qualified uv release asset"
        with tempfile.TemporaryDirectory() as td:
            with patch.dict(os.environ,{"RUNNER_TEMP":td}),patch(
                    "urllib.request.build_opener",
                    return_value=FakeOpener(wrong)):
                # Synthetic fixture has a valid *size* but incorrect digest.
                fixed=dict(UV_RELEASE[platform_name])
                fixed["size"]=len(wrong)
                with patch.dict(UV_RELEASE,{platform_name:fixed}):
                    with self.assertRaisesRegex(
                            PublicHybridRuntimeDenied,"PINNED_SHA256_MISMATCH"):
                        pinned_managed_python(root=Path(td)/"managed")
                self.assertFalse((Path(td)/"managed"/(
                    "uv.exe" if platform_name == "windows" else "uv")).exists())

    def test_original_signed_worker_admission_before_any_hybrid_download(self):
        from f139.nci04_signed_native import NativeAdmission
        from f139.nci04_native_contract import Candidate
        from f139.nci04_worker_entry import bound_public_hybrid_cpu_test_path
        c = Candidate(intent_sha256="1"*64,qualification_key="2"*64,
                      target_commit="a"*40,target_tree_sha="b"*40,
                      path="native_p64k_probe.py",before_sha256="3"*64,
                      after_sha256="4"*64,after_bytes=b"new",
                      lane="TTT-Hybrid")
        source="5"*40
        auth="6"*64
        oslabel="windows-latest" if os.name=="nt" else "ubuntu-latest"
        admission=NativeAdmission(ticket="f139-nci04-i1-"+source[:12]+"-11111111",
                    lane="TTT-Hybrid",source_sha=source,run_id=7,
                    runner_os=oslabel,issue_number=1,issue_id=1,
                    intent=c,authorization_sha256=auth)
        with tempfile.TemporaryDirectory() as td:
            env={"RUNNER_TEMP":td,"F139_SOURCE_SHA":source,
                 "F139_NATIVE_AUTHORIZATION_SHA256":auth,
                 "F139_NATIVE_AUTHENTICATION_PASSED":"false"}
            with patch.dict(os.environ,env),patch(
                    "f139.public_hybrid_cpu_runtime.pinned_managed_python") as start:
                with self.assertRaisesRegex(
                        Exception,"HYBRID_CPU_SIGNED_OWNER_BOUNDARY"):
                    bound_public_hybrid_cpu_test_path(admission)
                start.assert_not_called()
            env["F139_NATIVE_AUTHENTICATION_PASSED"]="true"
            env["F139_WORKER_HMAC_KEY"]="must-not-inherit"
            with patch.dict(os.environ,env),patch(
                    "f139.public_hybrid_cpu_runtime.pinned_managed_python") as start:
                with self.assertRaisesRegex(Exception,"HYBRID_CPU_CREDENTIAL"):
                    bound_public_hybrid_cpu_test_path(admission)
                start.assert_not_called()
            env.pop("F139_WORKER_HMAC_KEY")
            runtime=Path(td)/"f139-hybrid-public-locked-wheelhouse"
            binpath=runtime/"venv"/("Scripts" if os.name=="nt" else "bin")
            binpath.mkdir(parents=True)
            python=Path(td)/"managed-python-demo"
            python.touch()
            expected={
                "schema":RECEIPT_SCHEMA,"owner_source_sha":source,
                "platform":"windows" if os.name=="nt" else "linux",
                "python_version":"3.11.11",
                "versions":{"torch":"2.5.1+cpu","pytest":"8.3.4","numpy":"1.26.4"},
                "fully_locked_offline_install":True,"pip_check":True,
                "candidate_executed":False,"worker_ticket_signed":False,
                "original_owner_mutated":False,"scientific_first_use":False,
                "venv_bin_directory":str(binpath),
            }
            with patch.dict(os.environ,env),patch(
                    "f139.public_hybrid_cpu_runtime.pinned_managed_python",
                    return_value=python) as start,patch(
                    "f139.public_hybrid_cpu_runtime.provision",
                    return_value=expected) as provision:
                result=bound_public_hybrid_cpu_test_path(admission)
                self.assertEqual(Path(result).resolve(),binpath.resolve())
                self.assertEqual(start.call_count,1)
                self.assertEqual(provision.call_count,1)


    def test_staged_runtime_does_not_silently_modify_signed_worker(self):
        worker = Path(__file__).resolve().parents[1] / (
            ".github/workflows/forge-f139-development-worker.yml")
        source = worker.read_text(encoding="utf-8")
        native = source[source.index("  native-execute:\n"):
                        source.index("  native-authorize-v2:\n")]
        self.assertIn("native-authorize", native)
        self.assertIn("F139_NATIVE_AUTHENTICATION_PASSED: 'true'", native)
        self.assertIn("python -B -m f139.nci04_worker_entry execute", native)
        self.assertIn("F139_NCI04_SOURCE_BOUND_NATIVE_QUALIFICATION=PASS", native)
        # This is a staging/source-only PR. The original signed worker
        # requires its own explicit release governance and MUST remain unchanged.
        self.assertNotIn("f139.public_hybrid_cpu_runtime", native)
        self.assertNotIn("astral-sh/setup-uv@", native)
        self.assertNotIn("F139_HYBRID_CPU_RUNTIME=", native)


if __name__ == "__main__":
    unittest.main()
