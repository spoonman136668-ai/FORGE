#!/usr/bin/env python3
"""ACC-62 / U14 universal procedural-weight lossless-capacity falsifier.

This proves a universal counting obstruction, not a negative benchmark on real LLM
weights. Never infer physical memory, GPU speed or scientific first-use success.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import platform
import struct
import zlib
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
REGISTRY=ROOT/"research/ac07_sourcefree/ac08_portfolio.py"
PRE=ROOT/"docs/research/ACC-62-U14-PREEXEC-20261030.md"
REGISTRY_BLOB="5126c860771fb024ccfc14c3f7ee8925edf29787"
PRE_COMMIT="fbb6793b2e37e3493468c7ea7b2bf9810c39adda"
SIZES=(256,4096,65536)
PERIODS=(1,2,8,64)
CONTROL_KEYS=(0,1,2)
PERIOD_LABEL=b"forge-acc62-u14-v1:period:"
CONTROL_LABEL=b"forge-acc62-u14-v1:control:"

def git_blob(payload: bytes) -> str:
    return hashlib.sha1(b"blob "+str(len(payload)).encode()+b"\0"+payload).hexdigest()

def sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()

def source_identity() -> dict:
    if not REGISTRY.is_file() or git_blob(REGISTRY.read_bytes().replace(b"\r\n",b"\n"))!=REGISTRY_BLOB:
        raise RuntimeError("ACC62_U14_ORIGINAL_REGISTRY_DRIFT")
    text=REGISTRY.read_text(encoding="utf-8")
    if '"procedural synthesis of arbitrary weights"' not in text:
        raise RuntimeError("ACC62_U14_ORIGINAL_CLAIM_TITLE_MISSING")
    if not PRE.is_file() or "U14" not in PRE.read_text(encoding="utf-8"):
        raise RuntimeError("ACC62_U14_PROSPECTIVE_PROTOCOL_MISSING")
    return {"original_registry_git_blob":REGISTRY_BLOB,
            "prereg_commit":PRE_COMMIT,"original_claim":"U14",
            "scope":"RESTRICTED_MATH_AND_PYTHON_CONTROLS_NOT_MODEL_SPEED"}

def number_of_all_source_weights(nbytes: int) -> int:
    if nbytes<1:raise ValueError("nonpositive source length")
    return 1<<(8*nbytes)

def number_of_shorter_bit_codes(nbytes: int) -> int:
    # For lengths 0..(8*N-1), sum 2**k == 2**(8*N)-1.
    if nbytes<1:raise ValueError("nonpositive source length")
    return (1<<(8*nbytes))-1

def fixed_seed16(seed: int) -> bytes:
    if not 0<=seed<=255:raise ValueError("seed outside one byte")
    return bytes((seed,seed ^ 0xA5))

def periodic_pattern(period: int) -> bytes:
    if period not in PERIODS:raise ValueError("unfrozen period")
    return bytes(hashlib.sha256(PERIOD_LABEL+struct.pack(">II",period,i)).digest()[0]
                 for i in range(period))

def periodic_encode(original: bytes, period: int) -> bytes | None:
    if period not in PERIODS or len(original) not in SIZES:
        raise ValueError("unfrozen corpus/period")
    pattern=original[:period]
    if pattern*(len(original)//period)!=original:
        return None
    # Payload: byte length 4 + period count 1 + exact original pattern.
    return struct.pack(">IB",len(original),period)+pattern

def periodic_decode(encoded: bytes) -> bytes:
    if len(encoded)<6:raise ValueError("truncated")
    n,period=struct.unpack(">IB",encoded[:5])
    if n not in SIZES or period not in PERIODS or len(encoded)!=5+period or n%period:
        raise ValueError("invalid descriptor")
    return encoded[5:]*(n//period)

def periodic_source(n: int, period: int) -> bytes:
    if n not in SIZES or period not in PERIODS or n%period:
        raise ValueError("unfrozen case")
    return periodic_pattern(period)*(n//period)

def control_source(n: int, key: int) -> bytes:
    if n not in SIZES or key not in CONTROL_KEYS:raise ValueError("unfrozen control")
    chunks=[]
    for counter in range((n+31)//32):
        chunks.append(hashlib.sha256(CONTROL_LABEL+
                      struct.pack(">II",n,key)+struct.pack(">I",counter)).digest())
    return b"".join(chunks)[:n]

def report() -> dict:
    custody=source_identity()
    if not (number_of_shorter_bit_codes(2)==65535 and number_of_all_source_weights(2)==65536
            and len({fixed_seed16(k) for k in range(256)})==256):
        raise RuntimeError("UNIVERSAL_PIGEONHOLE_FALSIFIER_DRIFT")
    structured=[]
    controls=[]
    for n in SIZES:
        for period in PERIODS:
            data=periodic_source(n,period)
            enc=periodic_encode(data,period)
            if enc is None or periodic_decode(enc)!=data:
                raise RuntimeError("STRUCTURED_EXACT_RECONSTRUCTION_FAILED")
            structured.append({"nbytes":n,"period":period,"source_sha256":sha(data),
                "decoded_sha256":sha(periodic_decode(enc)),"raw_bytes":n,
                "descriptor_bytes":len(enc),"zlib6_bytes":len(zlib.compress(data,6)),
                "exact":True})
        for key in CONTROL_KEYS:
            data=control_source(n,key)
            enc=periodic_encode(data,64)
            # The high-entropy-looking examples come from a published small
            # hash-based program, so their true algorithmic entropy is not asserted.
            if enc is not None:
                raise RuntimeError("CONTROL_ACCIDENTALLY_PERIODIC")
            packed=zlib.compress(data,6)
            if zlib.decompress(packed)!=data:
                raise RuntimeError("CONTROL_REFERENCE_COMPRESSION_NOT_EXACT")
            controls.append({"nbytes":n,"key":key,"source_sha256":sha(data),
                "zlib6_bytes":len(packed),"periodic_decoder_can_represent":False,
                "zlib6_recovered_sha256":sha(zlib.decompress(packed))})
    if len(structured)!=12 or len(controls)!=9:
        raise RuntimeError("FROZEN_MATRIX_INCOMPLETE")
    return {"schema":"forge.acc62.u14.capacity.source-bound.v1",
        "classification":{"universal_arbitrary_exact_shrinking":"U14_NO_GO_PROVEN",
                          "restricted_structured_lossless":"U14_PASS_RESTRICTED_ONLY",
                          "original_model_weight_speed_accuracy_rss":"UNVERIFIED",
                          "scientific_first_use":"NOT_ESTABLISHED",
                          "production_admission":"NOT_GRANTED"},
        "identity":custody,
        "counting_two_byte_weights":{"source_space":number_of_all_source_weights(2),
            "all_shorter_codewords":number_of_shorter_bit_codes(2),
            "fixed_one_byte_seed_capacity":256,
            "fixed_one_byte_seed_unique_outputs":len({fixed_seed16(i) for i in range(256)}),
            "unrepresented_minimum_one_byte_seed":65536-256},
        "structured":structured,"controls":controls,
        "note":"Only universal ALL tensors exact-short representation is disproved. "
               "No genuine pretrained model weights, GPU measurements, cold RSS or "
               "amortized decoder code cost were measured. Structural positives "
               "cannot be generalized, and hash-derived controls are not truly random."}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--json",type=Path,required=True)
    args=p.parse_args()
    result=report()
    args.json.parent.mkdir(parents=True,exist_ok=True)
    args.json.write_bytes((json.dumps(result,indent=2,sort_keys=True)+"\n").encode("utf-8"))
    print("ACC62_U14_SCOPE=RESTRICTED_SOURCE_BOUND")
    print("ACC62_U14_UNIVERSAL="+result["classification"]["universal_arbitrary_exact_shrinking"])
    print("ACC62_U14_STRUCTURED="+result["classification"]["restricted_structured_lossless"])
    print("ACC62_U14_MODEL_RESOURCE=UNVERIFIED")

if __name__=="__main__":main()
