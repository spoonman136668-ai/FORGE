"""L5 public Alice prefix completion and complete source/resource receipt.

Fitted comparators receive same 750 TRAIN records, frozen models then
evaluate the TRAIN, SELECT and DEV roles without selecting hypotheses.
No original L1-L4 heldout or protected Q21/FSA first-use is accessed.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import sys
import time
import tracemalloc

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from source import ROLES,COUNTS,BLOB,load,digest,canonical
from models import ARMS,build_all

PROTO=HERE/"L5_FROZEN_PROTOCOL.json"


def guard():
    p=json.loads(PROTO.read_text(encoding="utf-8"))
    assert p["schema"]=="forge.optimizer.language.l5.prospective-public-subword-v1"
    assert p["stage"]=="FIRST_PROTOCOL_ONLY_COMMIT_BEFORE_SOURCE_LEARNER_AND_DEV"
    assert p["external_source"]["git_blob_sha1"]==BLOB
    assert p["source"]["roles"]==COUNTS
    assert tuple(p["arms"])==ARMS
    assert p["governance"]["mode"]=="ADDITIVE_ISOLATED_PUBLIC_DEVELOPMENT"
    return p


def edit_distance(a,b):
    prev=list(range(len(b)+1))
    for i,ca in enumerate(a,1):
        row=[i]
        for j,cb in enumerate(b,1):
            row.append(min(row[-1]+1,prev[j]+1,prev[j-1]+int(ca!=cb)))
        prev=row
    return prev[-1]


def evaluate(model,batch,train_words):
    exact=novel_exact=novel_total=novel_output=prefix_violations=abstain=0
    edit=char_correct=total_chars=operations=0
    pred_hash=hashlib.sha256()
    startwall=time.perf_counter()
    startcpu=time.process_time()
    for r in batch:
        # The model receives ONLY exposed semantic input, never target GOLD.
        public={"left":r["left"],"right":r["right"],"prefix":r["prefix"]}
        guess,work=model.predict(public)
        word=r["gold"]
        if type(guess) is not str or type(work) is not int or work<0:
            raise ValueError("L5_UNREGISTERED_GENERATOR_RETURN")
        pred_hash.update(guess.encode("ascii")+b"\n")
        if guess==word:
            exact+=1
        if word not in train_words:
            novel_total+=1
            novel_exact+=int(guess==word)
        novel_output+=int(guess not in train_words)
        prefix_violations+=int(not guess.startswith(public["prefix"]))
        abstain+=int(len(guess)==len(public["prefix"]))
        edit+=edit_distance(guess,word)/max(len(guess),len(word))
        char_correct+=sum(a==b for a,b in zip(guess,word))
        total_chars+=len(word)
        operations+=work
    cpu=time.process_time()-startcpu
    wall=time.perf_counter()-startwall
    n=len(batch)
    return {
        "examples":n,"full_word_exact_match":exact/n,
        "unseen_train_target_count":novel_total,
        "unseen_train_target_exact":novel_exact/novel_total if novel_total else None,
        "unseen_train_target_exact_numerator":novel_exact,
        "normalized_edit_distance":edit/n,
        "position_character_accuracy":char_correct/total_chars,
        "novel_output_rate":novel_output/n,
        "prefix_violation_rate":prefix_violations/n,
        "prefix_only_abstention_rate":abstain/n,
        "output_sha256":pred_hash.hexdigest(),
        "lookup_expansion_proxy_not_FLOPs":operations,
        "serial_inference_cpu_seconds":cpu,
        "serial_wall_us_per_word":wall*1e6/n,
    }


def rss():
    if os.name=="posix":
        import resource
        r=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return int(r if sys.platform=="darwin" else r*1024)
    if os.name=="nt":
        import ctypes
        from ctypes import wintypes
        class MEM(ctypes.Structure):
            _fields_=[("cb",wintypes.DWORD),("PageFaultCount",wintypes.DWORD),
                ("PeakWorkingSetSize",ctypes.c_size_t),("WorkingSetSize",ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage",ctypes.c_size_t),("QuotaPagedPoolUsage",ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage",ctypes.c_size_t),
                ("PagefileUsage",ctypes.c_size_t),("PeakPagefileUsage",ctypes.c_size_t)]
        m=MEM();m.cb=ctypes.sizeof(m)
        if ctypes.windll.psapi.GetProcessMemoryInfo(
            ctypes.windll.kernel32.GetCurrentProcess(),ctypes.byref(m),m.cb):
            return int(m.PeakWorkingSetSize)
    return None


def run(path):
    guard()
    tracemalloc.start()
    started=time.process_time()
    start=time.process_time()
    raw_sha,roles=load(path)
    source_cpu=time.process_time()-start
    hashes={role:digest(batch) for role,batch in roles.items()}
    seen=set()
    for role in ROLES:
        rows=roles[role]
        if len(rows)!=COUNTS[role]:
            raise ValueError("L5_FROZEN_ROLE_SIZE")
        for row in rows:
            window=canonical((row["left"],row["gold"],row["right"]))
            if window in seen:
                raise ValueError("L5_EXPOSED_SOURCE_DUPLICATION")
            seen.add(window)
    train_words={row["gold"] for row in roles["L5_TRAIN"]}
    trained={}
    resources={}
    for arm in ARMS:
        start=time.process_time()
        if arm=="WORD_PREFIX_LEXICON":
            from models import FittedPrefixLexicon
            model=FittedPrefixLexicon().fit(roles["L5_TRAIN"])
        elif arm in ("CHAR_BIGRAM_BEAM","CHAR_TRIGRAM_BEAM","CHAR_4GRAM_BEAM"):
            from models import FittedCharGram
            model=FittedCharGram(
                {"CHAR_BIGRAM_BEAM":2,"CHAR_TRIGRAM_BEAM":3,
                 "CHAR_4GRAM_BEAM":4}[arm]).fit(roles["L5_TRAIN"])
        elif arm=="CHAR_TRIGRAM_PLUS_CONTEXT":
            from models import ContextualCharGram
            model=ContextualCharGram().fit(roles["L5_TRAIN"])
        else:
            from models import FittedSuffixReuse
            model=FittedSuffixReuse().fit(roles["L5_TRAIN"])
        fitcpu=time.process_time()-start
        cp=model.checkpoint()
        trained[arm]=model
        resources[arm]={
            "train_cpu_seconds":fitcpu,
            "trained_checkpoint_bytes":len(cp),
            "trained_checkpoint_sha256":hashlib.sha256(cp).hexdigest(),
            "train_examples":COUNTS["L5_TRAIN"],
            "select_examples_reporting_only":COUNTS["L5_SELECT"],
            "source_target_train_vocab_words":len(train_words),
            "actual_hardware_parallelism":False,
        }
    frozen={arm:resources[arm]["trained_checkpoint_sha256"] for arm in ARMS}
    evaluations={}
    for role in ROLES:
        evaluations[role]={}
        for arm in ARMS:
            evaluations[role][arm]=evaluate(trained[arm],roles[role],train_words)
            if hashlib.sha256(trained[arm].checkpoint()).hexdigest()!=frozen[arm]:
                raise ValueError("L5_DEV_OR_SELECT_MUTATED_MODEL")
    _,peak=tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return {
        "schema":"forge.optimizer.language.l5.public-subword-receipt.v1",
        "scope":"PUBLIC_EXTERNAL_PREFIX_DEV_ONLY",
        "external_git_blob_sha1":BLOB,"external_raw_sha256":raw_sha,
        "previous_L1_L4_DEV_consumed":0,
        "Q21_FSA_first_use":False,
        "native_science_unchanged":True,
        "scientific_promotion":False,
        "externally_blinded_first_use":False,
        "learned_fundamental_cognition":False,
        "complete_resource_matched_LM_comparison":False,
        "energy_joules":"NOT_MEASURED","hardware_flops":"NOT_MEASURED",
        "source_role_sha256":hashes,
        "role_counts":COUNTS,
        "train_input_label_bytes":len(canonical(roles["L5_TRAIN"])),
        "source_generation_CPU_seconds":source_cpu,
        "train_target_vocabulary_words":len(train_words),
        "model_resources":resources,"role_evaluations":evaluations,
        "whole_process_CPU_seconds":time.process_time()-started,
        "peak_process_RSS_bytes":rss(),
        "peak_python_tracemalloc_bytes":peak,
        "os":platform.platform(),
    }


if __name__=="__main__":
    if len(sys.argv)!=2:
        raise SystemExit("usage: runner.py external-file")
    print(json.dumps(run(sys.argv[1]),indent=2,sort_keys=True,allow_nan=False))
