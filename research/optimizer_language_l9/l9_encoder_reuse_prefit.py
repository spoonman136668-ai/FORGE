#!/usr/bin/env python3
"""L9 frozen Transformer encoder-reuse equivalence prefit.

Synthetic-only prospective performance diagnostic. Does not read WebNLG,
fit models, select epochs, change frozen model code or authorize AUDIT_DEV.
"""
from __future__ import annotations
import argparse
import hashlib
import io
import json
import math
import time
import zipfile
from pathlib import Path
import torch
import l9_model_suite as frozen

EPOCHS=(4,8,12)
ROLE_SHA="b9995c1846f5e1d99bf8bc4083dde0ebb41140906284bcf050a7ed6fe0efe726"
MODEL_BLOB="710ce648a30ffc55647f689c5f4aa3ac13b07066"
RELEASE="a7ea49b5ffa5011edf81e8530c59b3552a965023"
ZIP_DIGEST={1701:"17a90a22f1659a572f6987b73ff7e36bdf92d9f14b87a839f5d50a0cadc3adbc",
            1702:"24bb0277b30fc90d69372ab25542379897a4c543a8b0010a2c9d8230972b733d"}
FIXTURES=[
    (("Alpha","employedAt","Beta"),),
    (("Alice","livesIn","Boston"),("Boston","locatedIn","America")),
    (("Entity ñ","relatedTo","Another é"),("Third entity","owns","Fourth")),
]
def require(condition,message):
    if not condition:
        raise ValueError(message)
def sha(x:bytes)->str:
    return hashlib.sha256(x).hexdigest()
def checkpoint_from_zip(zipfile_path:Path,seed:int,epoch:int):
    import os
    data=zipfile_path.read_bytes()
    require(sha(data)==ZIP_DIGEST[seed],"artifact ZIP digest drift")
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        require(len(z.namelist())==4,"artifact contains unexpected files")
        receipt_raw=z.read("receipt.json")
        receipt=json.loads(receipt_raw)
        required={
            "schema":"forge.optimizer.language.l9.neural-train-only-development-v1",
            "status":"NEURAL_TRAIN_COMPLETE_SELECT_NOT_RUN_DEVELOPMENT_ONLY",
            "source_release_sha":RELEASE,
            "role_identity_sha256":ROLE_SHA,
            "model_suite_git_blob":MODEL_BLOB,
            "arm":"SMALL_TRANSFORMER","seed":seed,
            "train_examples":8480,
            "select_count_loaded_but_unseen_by_fit":2154,
            "select_fidelity_scored":False,
            "audit_dev_reference_consumed":False,
            "official_test_consumed":False,
            "scientific_go":False,
            "model_fit_role":"L9_TRAIN",
            "checkpoint_epochs":[4,8,12],
        }
        for key,value in required.items():
            require(receipt.get(key)==value,"frozen fit identity drift: "+key)
        require(set(receipt["checkpoints"])=={"4","8","12"},"epoch coverage drift")
        info=receipt["checkpoints"][str(epoch)]
        name=f"SMALL_TRANSFORMER-seed{seed}-epoch{epoch}-inference.pt"
        require(info["inference_file"]==name,"checkpoint file mismatch")
        model_bytes=z.read(name)
        require(sha(model_bytes)==info["inference_sha256"],"checkpoint hash drift")
        require(len(model_bytes)==info["inference_bytes"]<=3145728,"checkpoint length drift")
    state=torch.load(io.BytesIO(model_bytes),map_location="cpu",weights_only=True)
    require(isinstance(state,dict) and set(state)=={"model"},"inference payload malformed")
    net=frozen.build_transformer_model()
    net.load_state_dict(state["model"],strict=True)
    net.eval()
    require(sum(p.numel() for p in net.parameters())==424387,"model parameter drift")
    require(all(bool(torch.isfinite(p).all()) for p in net.parameters()),"nonfinite checkpoint")
    return net,{"epoch":epoch,"checkpoint_sha256":info["inference_sha256"],
                "fit_receipt_sha256":sha(receipt_raw)}

def baseline(net,src,steps=64,ignore_eos=False):
    tgt=torch.full((1,1),frozen.BOS,dtype=torch.long)
    for _ in range(steps):
        logits=net.forward(src,tgt)[:,-1,:]
        nxt=logits.argmax(dim=-1,keepdim=True)
        tgt=torch.cat((tgt,nxt),dim=1)
        if not ignore_eos and bool((nxt==frozen.EOS).all()):break
    return tgt[:,1:]

def encoder_reuse(net,src,steps=64,ignore_eos=False):
    # No layer weight, output distribution or decoding-rule changes.
    # Cache the deterministic encoder output while retaining full decoder recompute.
    mask=(src==frozen.PAD)
    memory=net.transformer.encoder(net._embed(src),src_key_padding_mask=mask)
    tgt=torch.full((1,1),frozen.BOS,dtype=torch.long)
    for _ in range(steps):
        causal=torch.nn.Transformer.generate_square_subsequent_mask(tgt.shape[1],device=tgt.device)
        h=net.transformer.decoder(net._embed(tgt),memory,
                    tgt_mask=causal,tgt_key_padding_mask=(tgt==frozen.PAD),
                    memory_key_padding_mask=mask)
        nxt=net.output(h)[:,-1,:].argmax(dim=-1,keepdim=True)
        tgt=torch.cat((tgt,nxt),dim=1)
        if not ignore_eos and bool((nxt==frozen.EOS).all()):break
    return tgt[:,1:]

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--artifact-zip",type=Path,required=True)
    p.add_argument("--seed",type=int,choices=(1701,1702),required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    require(not a.out.exists(),"refusing to overwrite")
    require(torch.__version__.split("+")[0]=="2.5.1","PyTorch reference runtime drift")
    torch.set_num_threads(2)
    fixtures=[]
    for f in FIXTURES:
        encoded=frozen.encode_source(f)
        require(encoded is not None and len(encoded)<=frozen.MAX_SOURCE_BYTES+2,"invalid synthetic fixture")
        fixtures.append(torch.tensor([encoded],dtype=torch.long))
    results=[]; long_case=None
    with torch.inference_mode():
        for epoch in EPOCHS:
            net,meta=checkpoint_from_zip(a.artifact_zip,a.seed,epoch)
            for fixture_index,src in enumerate(fixtures):
                start=time.perf_counter()
                original=baseline(net,src)
                full_wall=time.perf_counter()-start
                start=time.perf_counter()
                accelerated=encoder_reuse(net,src)
                reused_wall=time.perf_counter()-start
                require(torch.equal(original,accelerated),
                   f"FAIL_CLOSED_TOKEN_MISMATCH seed={a.seed} epoch={epoch} fixture={fixture_index}")
                results.append({"seed":a.seed,"epoch":epoch,"fixture_id":fixture_index,
                  "tokens":int(original.numel()),
                  "original_wall_s":round(full_wall,5),
                  "encoder_reuse_wall_s":round(reused_wall,5),
                  "exact_token_equivalence":True,
                  "checkpoint_sha256":meta["checkpoint_sha256"]})
            if epoch==12:
                src=fixtures[1]
                start=time.perf_counter()
                o=baseline(net,src,steps=513,ignore_eos=True)
                orig_wall=time.perf_counter()-start
                start=time.perf_counter()
                a2=encoder_reuse(net,src,steps=513,ignore_eos=True)
                reuse_wall=time.perf_counter()-start
                require(torch.equal(o,a2),"FAIL_CLOSED_513_TOKEN_MISMATCH")
                long_case={"seed":a.seed,"epoch":12,"forced_steps":513,
                   "token_equivalence":True,
                   "full_wall_s":round(orig_wall,5),
                   "reuse_wall_s":round(reuse_wall,5),
                   "sequence_sha256":sha(bytes(json.dumps(o.tolist(),separators=(",",":")),"utf-8"))}
            del net
    require(len(results)==9 and long_case is not None,"missing prefit cases")
    evidence={
        "schema":"forge.optimizer.language.l9.encoder-reuse-synthetic-prefit-v1",
        "status":"SYNTHETIC_EQUIVALENCE_ONLY_NOT_SELECT",
        "source_suite_blob":MODEL_BLOB,
        "role_identity_sha256":ROLE_SHA,
        "seed":a.seed,
        "python_torch":torch.__version__,
        "cases":results,"long_case":long_case,
        "no_webnlg_records_loaded":True,
        "audit_reference_consumed":False,
        "official_test_consumed":False,
        "fit_or_selection_performed":False,
        "not_qualified_for_frozen_select_substitution":True,
        "scientific_go":False
    }
    a.out.parent.mkdir(parents=True,exist_ok=True)
    raw=(json.dumps(evidence,sort_keys=True,separators=(",",":"),ensure_ascii=False)+"\n").encode("utf-8")
    a.out.write_bytes(raw)
    print("L9_ENCODER_REUSE_SYNTHETIC_EQUIV=PASS")
    print("L9_SEED="+str(a.seed)+" L9_SHORT_CASES=9 L9_LONG_STEPS=513")
    print("L9_PREFIT_SHA256="+sha(raw))
    print("L9_SELECT_EVALUATED=FALSE")
    print("L9_AUDIT_DEV_CONSUMED=FALSE")
    print("L9_SCIENTIFIC_GO=FALSE")
if __name__=="__main__":
    main()
