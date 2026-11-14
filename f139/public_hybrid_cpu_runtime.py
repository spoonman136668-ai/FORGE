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


def wheel_lock_bytes(rows: list[dict], platform_name: str) -> bytes:
    """Freeze observed platform-specific pip lock *bytes* exactly.

    Windows Path.write_text in the original qualification emitted CRLF;
    Linux emitted LF. Both observed hashes remain immutable.
    """
    raw = lock_text(rows).encode("utf-8")
    return raw.replace(b"\n", b"\r\n") if platform_name == "windows" else raw


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
         and sha(wheel_lock_bytes(p["wheels"], platform_name)) ==
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
    req.write_bytes(wheel_lock_bytes(manifest["wheels"], platform_name))
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


# Official uv 0.9.5 release assets, pinned by the provider's SHA-256
# digest before the original native worker executes any downloaded executable.
UV_RELEASE = {
    "linux": {
        "asset": "uv-x86_64-unknown-linux-gnu.tar.gz",
        "size": 21370871,
        "sha256": "2cf10babba653310606f8b49876cfb679928669e7ddaa1fb41fb00ce73e64f66",
    },
    "windows": {
        "asset": "uv-x86_64-pc-windows-msvc.zip",
        "size": 20760405,
        "sha256": "515dc53d7553f1357d0abc1f70acd921fbb9e30230b1d9a08737236daa6ee920",
    },
}


def _extract_exact_uv(archive: Path, platform_name: str, output: Path) -> None:
    """Extract only the one fixed uv executable, never arbitrary archive paths."""
    import tarfile
    import zipfile
    need(platform_name in UV_RELEASE and output.parent.is_dir()
         and not output.exists() and not output.is_symlink(),
         "UV_EXTRACTION_TARGET")
    wanted = "uv.exe" if platform_name == "windows" else "uv"
    max_executable = 75 * 1024 * 1024
    if platform_name == "windows":
        with zipfile.ZipFile(archive, "r") as z:
            members = z.infolist()
            need(0 < len(members) <= 64, "UV_ARCHIVE_MEMBER_BUDGET")
            # The release archive can include uvx and documentation; only uv.exe
            # is ever read, and no archive pathname is used as an output path.
            selected = [m for m in members if
                        m.filename.replace("\\", "/").split("/")[-1] == wanted]
            need(len(selected) == 1 and not selected[0].is_dir()
                 and 0 < selected[0].file_size <= max_executable,
                 "UV_EXACT_EXECUTABLE_NOT_FOUND")
            mode = selected[0].external_attr >> 16
            need(not (mode & 0o170000 == 0o120000),
                 "UV_ARCHIVE_SYMLINK")
            data = z.read(selected[0], pwd=None)
            need(len(data) == selected[0].file_size, "UV_EXTRACTED_SIZE")
    else:
        with tarfile.open(archive, mode="r:gz") as t:
            members = t.getmembers()
            need(0 < len(members) <= 64
                 and all(m.isfile() or m.isdir() for m in members),
                 "UV_ARCHIVE_UNSAFE_MEMBER")
            selected = [m for m in members if
                        m.name.split("/")[-1] == wanted and m.isfile()]
            need(len(selected) == 1
                 and 0 < selected[0].size <= max_executable
                 and selected[0].mode & 0o6000 == 0,
                 "UV_EXACT_EXECUTABLE_NOT_FOUND")
            stream = t.extractfile(selected[0])
            need(stream is not None, "UV_EXTRACT_STREAM")
            with stream:
                data = stream.read(max_executable + 1)
            need(len(data) == selected[0].size, "UV_EXTRACTED_SIZE")
    need(len(data) <= max_executable and data, "UV_EXTRACT_BYTES")
    with output.open("xb") as target:
        target.write(data)
    if platform_name == "linux":
        output.chmod(0o700)


def pinned_managed_python(*, root: Path) -> Path:
    """One fresh runner-temp source-bound official Python 3.11.11 runtime.

    The original GitHub worker ticket is already signed before calling this.
    uv is downloaded from GitHub's immutable release URL, verified against a
    frozen SHA256 digest and extracted without archive-supplied paths.
    """
    import urllib.parse
    import urllib.request
    platform_name = "windows" if sys.platform == "win32" else (
        "linux" if sys.platform.startswith("linux") else "")
    need(platform_name in UV_RELEASE and
         platform.machine().lower() in ("x86_64", "amd64"),
         "UV_PLATFORM_UNSUPPORTED")
    root = Path(root)
    temp_raw = os.environ.get("RUNNER_TEMP", "")
    need(temp_raw and root.is_absolute() and not root.exists(),
         "UV_FRESH_ROOT_REQUIRED")
    temp = Path(temp_raw).resolve(strict=True)
    need(root.parent.resolve(strict=True) == temp
         and not root.is_symlink(), "UV_RUNNER_TEMP_BOUNDARY")
    release = UV_RELEASE[platform_name]
    root.mkdir(mode=0o700)
    archive = root / release["asset"]
    url = ("https://github.com/astral-sh/uv/releases/download/0.9.5/"
           + release["asset"])
    # Never read inherited proxy credentials, .netrc, or ambient API tokens.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    request = urllib.request.Request(url, headers={"User-Agent": "F139-CPU-qualifier"})
    digest = hashlib.sha256()
    count = 0
    with opener.open(request, timeout=60) as incoming:
        endpoint = urllib.parse.urlsplit(incoming.geturl())
        need(endpoint.scheme == "https" and endpoint.hostname in (
            "github.com", "release-assets.githubusercontent.com",
            "objects.githubusercontent.com"),
            "UV_ARCHIVE_ORIGIN")
        with archive.open("xb") as f:
            while True:
                data = incoming.read(1024 * 1024)
                if not data:
                    break
                count += len(data)
                need(count <= release["size"], "UV_ARCHIVE_SIZE_BUDGET")
                digest.update(data)
                f.write(data)
    need(count == release["size"]
         and digest.hexdigest() == release["sha256"],
         "UV_ARCHIVE_PINNED_SHA256_MISMATCH")
    uv = root / ("uv.exe" if platform_name == "windows" else "uv")
    _extract_exact_uv(archive, platform_name, uv)
    env = safe_env()
    managed = root / "managed-python"
    env.update({
        "UV_PYTHON_INSTALL_DIR": str(managed),
        "UV_CACHE_DIR": str(root / "uv-cache"),
        "UV_PYTHON_PREFERENCE": "only-managed",
        "UV_NO_PROGRESS": "1",
    })
    version = command([str(uv), "--version"], directory=root,
                      timeout=30, env=env)
    need(re.fullmatch(r"uv\s+0\.9\.5(?:\s+.*)?", version) is not None,
         "UV_EXECUTABLE_VERSION")
    command([str(uv), "python", "install", REQUIREMENTS["python"]],
            directory=root, timeout=240, env=env)
    found = command([str(uv), "python", "find", REQUIREMENTS["python"]],
                    directory=root, timeout=40, env=env)
    python = Path(found).resolve(strict=True)
    need(python.is_file()
         and python.is_relative_to(managed.resolve(strict=True)),
         "UV_MANAGED_INTERPRETER_SCOPE")
    actual = command([str(python), "-B", "-c",
                      "import platform; print(platform.python_version())"],
                     directory=root, timeout=30, env=safe_env())
    need(actual == REQUIREMENTS["python"], "UV_MANAGED_PYTHON_DRIFT")
    return python


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
