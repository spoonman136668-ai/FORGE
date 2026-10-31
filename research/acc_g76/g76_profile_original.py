"""G76 bounded profiler capture; authentic RTX FP16 SDPA baseline only."""
from __future__ import annotations

import hashlib
import json
import os
import platform
import urllib.request
from pathlib import Path

import torch
import transformers
from huggingface_hub import snapshot_download
from transformers import AutoModelForCausalLM, AutoTokenizer

from g76i_timeline import run_timeline

MODEL_REPO = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
MODEL_REV = "c13e4efb205d7a8e5d13c088aa10a9dabac9b96a"
WEIGHT_SHA256 = "6e6001da2106d4757498752a021df6c2bdc332c650aae4bae6b0c004dcf14933"
WEIGHT_BYTES = 2_200_119_864
TEXT_REPO_REV = "81db45c9c48c592f0b77f01fc59e677ad0a5634e"
TEXT_PATH = "1342.txt"
TEXT_BLOB_SHA1 = "0a7d439c2f34b0dfacb88b7116429a9575b5735c"
TEXT_BYTES = 717_602
TEXT_URL = f"https://raw.githubusercontent.com/GITenberg/Pride-and-Prejudice_1342/{TEXT_REPO_REV}/{TEXT_PATH}"
CASES = ((24576, 512), (98304, 1536))


def git_blob_sha1(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def load_frozen_text(path: Path) -> bytes:
    if not path.is_file():
        with urllib.request.urlopen(TEXT_URL, timeout=40) as response:
            raw = response.read(TEXT_BYTES + 1)
        if len(raw) != TEXT_BYTES or git_blob_sha1(raw) != TEXT_BLOB_SHA1:
            raise RuntimeError("G76_TEXT_SOURCE_DRIFT")
        path.write_bytes(raw)
    raw = path.read_bytes()
    if len(raw) != TEXT_BYTES or git_blob_sha1(raw) != TEXT_BLOB_SHA1:
        raise RuntimeError("G76_TEXT_SOURCE_DRIFT")
    return raw


def run() -> dict:
    import torch
    import transformers
    from huggingface_hub import snapshot_download
    from transformers import AutoTokenizer, AutoModelForCausalLM

    if torch.__version__ != "2.8.0+cu128" or torch.version.cuda != "12.8":
        raise RuntimeError("G76_TORCH_CUDA_RUNTIME_DRIFT")
    if transformers.__version__ != "4.52.3":
        raise RuntimeError("G76_TRANSFORMERS_RUNTIME_DRIFT")
    if not torch.cuda.is_available() or torch.cuda.device_count() != 1:
        raise RuntimeError("G76_CUDA_DEVICE_REQUIRED")
    device = torch.device("cuda:0")
    gpu = torch.cuda.get_device_name(device)
    capability = torch.cuda.get_device_capability(device)
    free, total = torch.cuda.mem_get_info(device)
    if "RTX 5070 Ti Laptop GPU" not in gpu or capability != (12, 0) or free < 7_000 * 1024**2:
        raise RuntimeError("G76_ORIGINAL_RTX_ADMISSION_FAILED")
    probe = torch.ones((1024, 1024), device=device, dtype=torch.float32)
    product = probe @ probe
    torch.cuda.synchronize(device)
    if not product.is_cuda or float(product[0, 0].item()) != 1024.0:
        raise RuntimeError("G76_REAL_CUDA_MATMUL_FAILED")
    del probe, product
    torch.cuda.empty_cache()

    temp = Path(os.environ["RUNNER_TEMP"])
    corpus_path = temp / "acc-g76-austen.txt"
    raw = load_frozen_text(corpus_path)
    corpus = raw.decode("utf-8", errors="strict")

    snapshot = Path(snapshot_download(
        repo_id=MODEL_REPO, revision=MODEL_REV, token=False,
        allow_patterns=["config.json", "generation_config.json", "model.safetensors",
                        "tokenizer.json", "tokenizer_config.json", "special_tokens_map.json"]))
    weight_path = snapshot / "model.safetensors"
    if not weight_path.is_file() or weight_path.stat().st_size != WEIGHT_BYTES:
        raise RuntimeError("G76_MODEL_WEIGHT_SIZE_DRIFT")
    weight_hash = sha256(weight_path.read_bytes())
    if weight_hash != WEIGHT_SHA256:
        raise RuntimeError("G76_MODEL_WEIGHT_HASH_DRIFT")

    tokenizer = AutoTokenizer.from_pretrained(
        str(snapshot), use_fast=True, local_files_only=True, trust_remote_code=False)
    model = AutoModelForCausalLM.from_pretrained(
        str(snapshot), torch_dtype=torch.float16, attn_implementation="sdpa",
        use_safetensors=True, trust_remote_code=False, local_files_only=True).eval().to(device)
    if model.config.model_type != "llama" or model.config.num_hidden_layers != 22:
        raise RuntimeError("G76_MODEL_ARCHITECTURE_DRIFT")
    if model.config._attn_implementation != "sdpa":
        raise RuntimeError("G76_SDPA_CONFIG_NOT_ACTIVE")
    parameters = list(model.parameters())
    if any(parameter.dtype != torch.float16 or parameter.device.type != "cuda"
           for parameter in parameters):
        raise RuntimeError("G76_MODEL_PARAMETER_DTYPE_DEVICE_DRIFT")

    torch.backends.cuda.matmul.allow_tf32 = False
    output_dir = Path(os.environ["G76_OUTPUT_DIR"])
    output_dir.mkdir(parents=True, exist_ok=False)
    cases = []
    for char_offset, context_tokens in CASES:
        excerpt = corpus[char_offset:char_offset + 30_000]
        encoded = tokenizer(excerpt, add_special_tokens=False, truncation=True,
                            max_length=1536, return_tensors="pt")["input_ids"][0]
        if encoded.numel() < context_tokens:
            raise RuntimeError("G76_FROZEN_TEXT_WINDOW_TOO_SHORT")
        ids = encoded[:context_tokens].reshape(1, -1).to(device)
        ids_digest = sha256(json.dumps(ids[0].detach().cpu().tolist(),
                                       separators=(",", ":")).encode())
        result = run_timeline(model, ids, tokenizer, output_dir, tokens=64)
        cases.append(dict(
            char_offset=char_offset,
            context_tokens=context_tokens,
            input_token_ids_sha256=ids_digest,
            result=result))
    report = dict(
        schema="forge.acc.g76.profiler_capture.v1",
        status="PASS_COMPLETE_FROZEN_GPU_TRACE",
        source_head=os.environ.get("GITHUB_SHA", ""),
        model=dict(repo=MODEL_REPO, revision=MODEL_REV, weight_sha256=weight_hash,
                   weight_bytes=WEIGHT_BYTES, architecture="Llama 22 layer"),
        text_source=dict(repo="GITenberg/Pride-and-Prejudice_1342", revision=TEXT_REPO_REV,
                         path=TEXT_PATH, git_blob_sha1=git_blob_sha1(raw),
                         bytes=len(raw), sha256=sha256(raw),
                         scope="Previously exposed G74 source; profiling diagnostic only"),
        runtime=dict(python=platform.python_version(), torch=torch.__version__,
                      cuda=torch.version.cuda, transformers=transformers.__version__,
                      gpu=gpu, capability=list(capability),
                      free_vram_before_load_mib=free // 1024**2,
                      total_vram_mib=total // 1024**2),
        profiler=dict(activities=["CPU", "CUDA"], record_shapes=False,
                      profile_memory=False, with_stack=False,
                      sdpa_operator="aten::scaled_dot_product_attention",
                      overhead_fraction="UNMEASURED", speedup="UNMEASURED"),
        cases=cases,
        science_acceptance="NOT_GRANTED",
        acceleration_claim="NOT_MADE",
        production_approval="NOT_GRANTED")
    report_path = output_dir / "g76i_run.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    result = run()
    print("G76_RESULT=" + json.dumps(result, sort_keys=True, separators=(",", ":")))
