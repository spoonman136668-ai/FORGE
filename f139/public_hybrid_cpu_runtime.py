"""Frozen public Hybrid CPU runtime for the existing credential-free F139 worker.

Trusted provisioning only, before untrusted candidate execution. No HMAC, model
training, scientific first-use, original-owner changes, or source promotion.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys

from f139.private_cpu_runtime import freeze_wheels, lock_text

SCHEMA = "forge.f139.hybrid.public-cpu-wheelhouse-lock.v1"
RECEIPT_SCHEMA = "forge.f139.hybrid.public-cpu-runtime-qualified.v1"
LOCK_NAME = "public_hybrid_cpu_wheel_lock.json"
REQUIREMENTS = {
    "python": "3.11.11", "uv": "0.9.5", "torch": "2.5.1+cpu",
    "pytest": "8.3.4", "numpy": "1.26.4",
}
SHA40 = re.compile(r"[a-f0-9]{40}\Z")
SHA64 = re.compile(r"[a-f0-9]{64}\Z")
NAME = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
WHEEL = re.compile(r"[a-zA-Z0-9_.+\-]+\.whl\Z")


class PublicHybridRuntimeDenied(ValueError):
    pass


def need(ok: bool, code: str) -> None:
    if not ok:
        raise PublicHybridRuntimeDenied("F139_HYBRID_CPU_" + code)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_lock(path: Path, *, platform_name: str) -> dict:
    """Exact, platform-specific SHA256 wheel inventory; no dynamic lock."""
    need(platform_name in ("linux", "windows"), "PLATFORM_FORBIDDEN")
    raw = Path(path).read_bytes()
    need(0 < len(raw) <= 20000, "LOCK_SIZE")
    def unique(pairs):
        doc = {}
        for k, v in pairs:
            need(k not in doc, "LOCK_DUPLICATE_KEY")
            doc[k] = v
        return doc
    doc = json.loads(raw, object_pairs_hook=unique)
    need(type(doc) is dict and set(doc) ==
         {"schema", "source_run", "source_commit", "source_tree",
          "requirements", "platforms"} and doc["schema"] == SCHEMA
         and doc["source_run"] == 43543145243
         and doc["source_commit"] == "d2ede7bc2bc0f16aeeedc315681b21d7af6ec439"
         and doc["source_tree"] == "4535b435756edb005f078f9a6d5207fd0da7babb"
         and doc["requirements"] == REQUIREMENTS
         and type(doc["platforms"]) is dict
         and set(doc["platforms"]) == {"linux", "windows"},
         "LOCK_IDENTITY")
    p = doc["platforms"][platform_name]
    need(type(p) is dict and set(p) ==
         {"wheel_lock_sha256", "wheel_count", "total_wheel_bytes", "wheels"}
         and type(p["wheel_count"]) is int and 3 <= p["wheel_count"] <= 64
         and type(p["total_wheel_bytes"]) is int
         and 0 < p["total_wheel_bytes"] <= 512 * 1024 * 1024
         and type(p["wheels"]) is list
         and len(p["wheels"]) == p["wheel_count"]
         and type(p["wheel_lock_sha256"]) is str
         and SHA64.fullmatch(p["wheel_lock_sha256"]) is not None,
         "LOCK_PLATFORM_FIELDS")
    seen = set()
    for item in p["wheels"]:
        need(type(item) is dict
             and set(item) == {"name", "version", "filename", "sha256"}
             and all(type(v) is str for v in item.values())
             and NAME.fullmatch(item["name"]) is not None
             and WHEEL.fullmatch(item["filename"]) is not None
             and SHA64.fullmatch(item["sha256"]) is not None
             and len(item["version"]) < 50
             and not item["name"].startswith("nvidia-")
             and item["name"] not in seen,
             "LOCK_WHEEL_IDENTITY")
        seen.add(item["name"])
    need([x["name"] for x in p["wheels"]] == sorted(seen)
         and all(next((x["version"] for x in p["wheels"]
                       if x["name"] == name), None) == REQUIREMENTS[name]
                 for name in ("torch", "pytest", "numpy"))
         and sha(lock_text(p["wheels"]).encode("utf-8")) ==
         p["wheel_lock_sha256"],
         "LOCK_WHEEL_SET_OR_DIGEST")
    return p


def safe_env(source: dict[str, str] | None = None) -> dict[str, str]:
    """Explicit package-command environment; no hosted-worker credentials."""
    src = os.environ if source is None else source
    allow = {"PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "TMPDIR",
             "LANG", "LC_ALL", "HOME", "USERPROFILE", "APPDATA", "LOCALAPPDATA"}
    env = {k: v for k, v in src.items() if k.upper() in allow}
    env.update({
        "PYTHONDONTWRITEBYTECODE": "1",
        "PIP_DISABLE_PIP_VERSION_CHECK": "1",
        "PIP_NO_INPUT": "1",
        "PIP_NO_CACHE_DIR": "1",
        "PIP_CONFIG_FILE": os.devnull,
        "NETRC": os.devnull,
        "OMP_NUM_THREADS": "1",
        "OPENBLAS_NUM_THREADS": "1",
    })
    return env


def command(args, *, directory: Path, timeout: int, env: dict) -> str:
    need(type(args) is list and 1 <= len(args) <= 32
         and all(type(x) is str and x and "\n" not in x for x in args),
         "TRUSTED_ARGV")
    result = subprocess.run(args, cwd=directory, env=env,
                            stdin=subprocess.DEVNULL,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            check=False, timeout=timeout)
    need(result.returncode == 0, "TRUSTED_COMMAND_FAILED")
    return result.stdout.decode("utf-8", errors="strict").strip()


def provision(*, root: Path, owner_source_sha: str,
              managed_python: Path, source_root: Path) -> dict:
    """Build only a new ephemeral CPU runtime from SHA-pinned public wheels."""
    need(type(owner_source_sha) is str and
         SHA40.fullmatch(owner_source_sha) is not None, "SOURCE_SHA")
    platform_name = "windows" if sys.platform == "win32" else (
        "linux" if sys.platform.startswith("linux") else "")
    need(platform_name != "", "PLATFORM_UNSUPPORTED")
    source_root = Path(source_root).resolve(strict=True)
    need(source_root.is_dir(), "SOURCE_ROOT")
    actual = command(
        ["git", "-C", str(source_root), "rev-parse", "HEAD"],
        directory=source_root, timeout=15, env=safe_env())
    need(actual == owner_source_sha, "SOURCE_HEAD_DRIFT")
    need(command(["git", "-C", str(source_root), "status", "--porcelain",
                  "--untracked-files=all"],
                 directory=source_root, timeout=15, env=safe_env()) == "",
         "SOURCE_WORKTREE_DIRTY")
    manifest = read_lock(source_root / "f139" / LOCK_NAME,
                         platform_name=platform_name)
    root = Path(root)
    temp = Path(os.environ["RUNNER_TEMP"]).resolve(strict=True)
    need(root.is_absolute() and not root.exists()
         and root.parent.resolve(strict=True) == temp,
         "ROOT_NOT_FRESH_RUNNER_TEMP")
    managed_python = Path(managed_python).resolve(strict=True)
    need(managed_python.is_file(), "MANAGED_PYTHON_MISSING")
    env = safe_env()
    assert_version = command(
        [str(managed_python), "-B", "-c",
         "import platform; print(platform.python_version())"],
        directory=temp, timeout=30, env=env)
    need(assert_version == REQUIREMENTS["python"], "PYTHON_VERSION_DRIFT")
    root.mkdir(mode=0o700)
    wheelhouse = root / "wheelhouse"
    wheelhouse.mkdir()
    venv = root / "venv"
    command([str(managed_python), "-B", "-m", "venv", str(venv)],
            directory=root, timeout=180, env=env)
    python = venv / ("Scripts/python.exe" if platform_name == "windows"
                     else "bin/python")
    need(python.is_file(), "VENV_PYTHON_MISSING")
    req = root / "requirements.lock"
    req.write_text(lock_text(manifest["wheels"]), encoding="utf-8")
    need(sha(req.read_bytes()) == manifest["wheel_lock_sha256"],
         "LOCK_FILE_NOT_FROZEN")
    pip = [str(python), "-B", "-m", "pip", "--isolated"]
    # No dependency resolution drift: each transitive wheel is named,
    # version-pinned, and hash-pinned before any package is installed.
    command([*pip, "download", "--no-cache-dir", "--no-deps",
             "--only-binary=:all:", "--require-hashes",
             "--dest", str(wheelhouse),
             "--index-url", "https://download.pytorch.org/whl/cpu",
             "--extra-index-url", "https://pypi.org/simple",
             "-r", str(req)],
            directory=root, timeout=1100, env=env)
    actual_wheels = freeze_wheels(wheelhouse)
    actual_bytes = sum((wheelhouse / item["filename"]).stat().st_size
                       for item in actual_wheels)
    need(actual_wheels == manifest["wheels"]
         and actual_bytes == manifest["total_wheel_bytes"],
         "DOWNLOADED_WHEEL_HASH_OR_SIZE_DRIFT")
    command([*pip, "install", "--no-index", "--no-deps",
             "--no-compile", "--no-cache-dir", "--require-hashes",
             "--find-links", str(wheelhouse), "-r", str(req)],
            directory=root, timeout=900, env=env)
    command([*pip, "check"], directory=root, timeout=180, env=env)
    observed = json.loads(command(
        [str(python), "-B", "-c",
         "import json,importlib.metadata as m;"
         "print(json.dumps({p:m.version(p) for p in ('torch','pytest','numpy')}))"],
        directory=root, timeout=60, env=env))
    need(observed == {k: REQUIREMENTS[k] for k in
                      ("torch", "pytest", "numpy")}, "PACKAGE_VERSION_DRIFT")
    bindir = python.parent.resolve()
    need(bindir.is_dir() and bindir.is_relative_to(root.resolve()),
         "RUNTIME_BIN_DIRECTORY_ESCAPE")
    return {
        "schema": RECEIPT_SCHEMA,
        "owner_source_sha": owner_source_sha,
        "platform": platform_name,
        "python_version": REQUIREMENTS["python"],
        "versions": observed,
        "wheel_count": len(actual_wheels),
        "wheel_lock_sha256": manifest["wheel_lock_sha256"],
        "venv_bin_directory": str(bindir),
        "fully_locked_offline_install": True,
        "pip_check": True,
        "candidate_executed": False,
        "worker_ticket_signed": False,
        "original_owner_mutated": False,
        "scientific_first_use": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--managed-python", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    receipt = provision(root=args.root, owner_source_sha=args.source_sha,
                        managed_python=args.managed_python,
                        source_root=args.source_root)
    print("F139_HYBRID_PUBLIC_CPU_RUNTIME=" +
          json.dumps(receipt, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
