"""MP-AI23: bounded actual local-model memory-vs-control decision trial.

Development-only, NOT first-use, causal transfer or scientific acceptance.
Reads one committed private Mind-Palace SHA, never writes private source data
to the public FORGE workspace. No paid API, new authority, memory writer,
controller or general model promotion. Model and source pinned to exact hashes.
"""
from __future__ import annotations
import gc
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import socket
import sys
import time
import urllib.request

MP_SHA = "84ad556910c869afa2f171673d5a5b4041a4a9b4"
MP_RECORD_SHA = "3a377f825ad6da28d2c85534337ce831441295ee662e7f4b869f6c565d9e4f83"
MODEL_REV = "72da00985aa7cb57cd436a6172be99c3bd906d9c"
MODEL_SHA = "77665ea4815999596525c636fbeb56ba8b080b46ae85efef4f0d986a139834d7"
MODEL_BYTES = 1055609824
MODEL_NAME = "SmolLM2-1.7B-Instruct-Q4_K_M.gguf"
MODEL_URL = (
    "https://huggingface.co/bartowski/SmolLM2-1.7B-Instruct-GGUF/resolve/"
    + MODEL_REV + "/" + MODEL_NAME + "?download=true"
)
LESSONS = (
    "lesson/mpai05-p16-p17-memory-retriever-model-accuracy-no-gain-20261029",
    "lesson/mpai05-uq37-original-scheduled-inspection-repaired-but-idle-20261029",
)
CASES = (
    ("memory-accuracy", LESSONS[0],
     "Did the more compact retrieval approach improve the larger model's measured answer accuracy over the lexical approach?", "NO"),
    ("retrieval-efficiency", LESSONS[0],
     "Did the more compact retrieval approach reduce the measured context or processing budget relative to lexical retrieval?", "YES"),
    ("empty-queue", LESSONS[1],
     "Did the recovered periodic inspection ingest new authorized sources or demonstrate experience learning?", "NO"),
    ("inspection-recovery", LESSONS[1],
     "Did the source-pin repair restore successful guarded inspection, even though the source queue was empty?", "YES"),
)
ARMS = ("no_memory", "placebo", "accepted_memory")
MAX_OUTPUT = 72
MAX_CTX = 3072
SEED = 137
MAX_CALLS = len(CASES) * len(ARMS)
STATUS = "INIT"

def need(ok: bool, code: str):
    if not ok:
        raise RuntimeError("MPAI23_" + code)

def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def freeze_hash() -> str:
    return digest(json.dumps({
        "source": MP_SHA, "records": MP_RECORD_SHA, "model": MODEL_SHA,
        "cases": CASES, "arms": ARMS, "seed": SEED, "output_cap": MAX_OUTPUT
    }, sort_keys=True, separators=(",", ":")).encode())

def fetch_model(path: Path):
    need(not path.exists(), "MODEL_COLLISION")
    t0 = time.monotonic()
    req = urllib.request.Request(MODEL_URL, headers={"User-Agent": "MPAI23-source-pinned-development/1"})
    h = hashlib.sha256()
    n = 0
    with urllib.request.urlopen(req, timeout=50) as resp, path.open("xb") as out:
        for chunk in iter(lambda: resp.read(4 * 1024 * 1024), b""):
            n += len(chunk)
            need(n <= MODEL_BYTES and time.monotonic() - t0 <= 650, "MODEL_DOWNLOAD_BOUND")
            h.update(chunk)
            out.write(chunk)
    need(n == MODEL_BYTES and h.hexdigest() == MODEL_SHA, "MODEL_BYTES_SHA_DRIFT")
    with path.open("rb") as check:
        need(check.read(4) == b"GGUF", "MODEL_GGUF_HEADER")

def extract_decision(text: str):
    head = text.strip().splitlines()[0] if text.strip() else ""
    m = re.fullmatch(r"\s*DECISION\s*:\s*(YES|NO|UNKNOWN)\s*[.!]?\s*", head, re.I)
    return m.group(1).upper() if m else None

def prompt(context: str, question: str):
    return [
        {"role": "system", "content":
         "Answer the question using only supplied evidence. Do not invent facts. "
         "First line must be DECISION: YES, DECISION: NO or DECISION: UNKNOWN. "
         "Second line, EVIDENCE: brief explanation. "
         "When evidence is absent, choose UNKNOWN; do not invent facts. "
         "No other text."},
        {"role": "user", "content": "Evidence:\n" + context + "\nQuestion:\n" + question},
    ]

def placebo(length: int, unrelated_statement: str):
    # Same character budget, but a real unrelated existing record. Source
    # unavailable to these tasks; never fabricate a purported real observation.
    txt = "Unrelated historical record: " + unrelated_statement
    return (txt + "\n") * ((length // max(1, len(txt))) + 2)

def peak_working_set() -> int:
    import ctypes
    from ctypes import wintypes
    class Counters(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
          ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
          ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
          ("QuotaPagedPoolUsage", ctypes.c_size_t),
          ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
          ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
          ("PagefileUsage", ctypes.c_size_t),
          ("PeakPagefileUsage", ctypes.c_size_t)]
    c = Counters()
    c.cb = ctypes.sizeof(c)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE,
        ctypes.POINTER(Counters), wintypes.DWORD]
    psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
    need(bool(psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(),
               ctypes.byref(c), c.cb)), "WIN32_MEMORY_COUNTER")
    return int(c.PeakWorkingSetSize)

def main():
    global STATUS
    need(os.name == "nt" and os.environ.get("RUNNER_NAME") == "FORGE-CODEX-REMOTE"
         and os.environ.get("GITHUB_REPOSITORY") == "spoonman136668-ai/FORGE",
         "ORIGINAL_WINDOWS_IDENTITY")
    need(not os.environ.get("OPENAI_API_KEY"), "PAID_API_NOT_ALLOWED")
    root = Path(os.environ["MPAI23_PRIVATE_SCRATCH"])
    source = Path(os.environ["MPAI23_PRIVATE_SOURCE"])
    need(not root.exists() and source.is_dir(), "SOURCE_OR_SCRATCH_IDENTITY")
    need(shutil.disk_usage(root.parent).free > 2200000000, "DISK_LIMIT")
    root.mkdir()
    STATUS = "SOURCE"
    sys.path.insert(0, str(source / "tools"))
    from mindpalace_readonly import MemorySnapshot
    snapshot = MemorySnapshot(source, MP_SHA, ["Mind-Palace"])
    need(snapshot.records_sha256 == MP_RECORD_SHA, "RECORDS_DIGEST")
    records = {}
    for key in LESSONS:
        row = snapshot.get_record(MP_SHA, key, ["Mind-Palace"])
        need(row.get("found") and row["record"]["status"] == "observed"
             and row["record"]["source_refs"], "LESSON_NOT_AUTHENTIC")
        records[key] = row["record"]["statement"]
    unrelated_key = "lesson/mind-palace-one-command-real-ingestion-20260927"
    unrelated_row = snapshot.get_record(MP_SHA, unrelated_key, ["Mind-Palace"])
    need(unrelated_row.get("found"), "PLACEBO_SOURCE_UNAVAILABLE")
    unrelated = unrelated_row["record"]["statement"]
    source_statements = {
        "no_memory": lambda key: "",
        "placebo": lambda key: placebo(len(records[key]), unrelated)[:len(records[key])],
        "accepted_memory": lambda key: records[key],
    }
    for key in LESSONS:
        need(len(source_statements["accepted_memory"](key))
             == len(source_statements["placebo"](key)), "PLACEBO_LENGTH_PARITY")
    print("MPAI23_ACCEPTED_SOURCE_AND_RECORDS=PASS", flush=True)
    print("MPAI23_PREREGISTRATION_SHA256=" + freeze_hash(), flush=True)
    STATUS = "MODEL_DOWNLOAD"
    model_path = root / MODEL_NAME
    fetch_model(model_path)
    print("MPAI23_MODEL_EXACT_SHA256=PASS", flush=True)
    STATUS = "OFFLINE_MODEL"
    os.environ["HF_HUB_OFFLINE"] = "1"
    def denied(*a, **kw):
        raise RuntimeError("MPAI23_NETWORK_AFTER_SOURCE_FREEZE")
    socket.socket = denied
    from llama_cpp import Llama
    t0 = time.perf_counter()
    model = Llama(model_path=str(model_path), n_ctx=MAX_CTX, n_threads=4,
                  n_gpu_layers=0, n_batch=128, seed=SEED, verbose=False)
    load_ms = max(1, int(1000 * (time.perf_counter() - t0)))
    need(load_ms <= 120000, "MODEL_LOAD_CAP")
    results = []
    # Latin-square-ish rotation of arm sequence; each case sees all three.
    for i, (case_id, key, question, expected) in enumerate(CASES):
        order = ARMS[i % len(ARMS):] + ARMS[:i % len(ARMS)]
        for arm in order:
            context = source_statements[arm](key)
            t0 = time.perf_counter()
            raw = model.create_chat_completion(messages=prompt(context, question),
                   temperature=0, top_p=1, max_tokens=MAX_OUTPUT)
            ms = max(1, int(1000 * (time.perf_counter() - t0)))
            choices = raw.get("choices", [])
            need(len(choices) == 1, "MODEL_RESPONSE")
            answer = choices[0].get("message", {}).get("content", "")
            use = raw.get("usage", {})
            pt = int(use.get("prompt_tokens", 0))
            ct = int(use.get("completion_tokens", 0))
            need(type(answer) is str and 0 < pt <= 2600 and
                 0 < ct <= MAX_OUTPUT, "MODEL_TOKENS")
            decision = extract_decision(answer)
            results.append({
                "case": case_id, "arm": arm, "correct": decision == expected,
                "parseable": decision is not None, "abstained": decision == "UNKNOWN",
                "decision": decision, "expected": expected,
                "prompt_tokens": pt, "completion_tokens": ct,
                "wall_ms": ms, "context_chars": len(context),
                "context_sha256": digest(context.encode()),
                "output_sha256": digest(answer.encode()),
            })
    need(len(results) == MAX_CALLS, "INCOMPLETE_TRIALS")
    (root / "private_trials.json").write_text(json.dumps(
        {"freeze_sha256": freeze_hash(), "source_sha": MP_SHA,
         "model_sha256": MODEL_SHA, "development_only": True,
         "trials": results}, sort_keys=True), encoding="utf-8")
    for arm in ARMS:
        rows = [r for r in results if r["arm"] == arm]
        need(len(rows) == len(CASES), "ARM_DENOMINATOR")
        summary = {
            "calls": len(rows), "correct": sum(int(x["correct"]) for x in rows),
            "parseable": sum(int(x["parseable"]) for x in rows),
            "abstentions": sum(int(x["abstained"]) for x in rows),
            "total_tokens": sum(x["prompt_tokens"] + x["completion_tokens"] for x in rows),
            "wall_ms": sum(x["wall_ms"] for x in rows),
            "context_chars": sum(x["context_chars"] for x in rows),
        }
        print("MPAI23_ARM_" + arm.upper() + "=" +
              json.dumps(summary, sort_keys=True, separators=(",", ":")), flush=True)
    peak_bytes = peak_working_set()
    need(0 < peak_bytes <= 5000000000, "PEAK_MEMORY_CAP")
    print("MPAI23_PEAK_WORKING_SET_BYTES=" + str(peak_bytes), flush=True)
    print("MPAI23_MODEL_LOAD_MS=" + str(load_ms), flush=True)
    print("MPAI23_REAL_LOCAL_MODEL_CALLS=" + str(len(results)), flush=True)
    print("MPAI23_SAME_MODEL_AND_TASKS=PASS", flush=True)
    print("MPAI23_INDEPENDENT_HOLDOUT=FALSE", flush=True)
    print("MPAI23_TRUE_UNFAMILIAR_TRANSFER=NOT_PROVEN", flush=True)
    print("MPAI23_SCIENTIFIC_ACCEPTANCE=FALSE", flush=True)
    print("MPAI23_MODEL_PROMOTION=FALSE", flush=True)
    print("MPAI23_PRODUCTION_MEMORY_WRITES=0", flush=True)
    del model
    gc.collect()

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        cause = str(exc)
        code = cause if re.fullmatch(r"MPAI23_[A-Z0-9_]{3,90}", cause) else "MPAI23_PRIVATE_EXCEPTION"
        print("MPAI23_FAILURE_CLASS=" + code, flush=True)
        print("MPAI23_FAILURE_STAGE=" + STATUS, flush=True)
        print("MPAI23_FAILURE_TYPE=" + type(exc).__name__, flush=True)
        sys.exit(2)
