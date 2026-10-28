#!/usr/bin/env python3
"""Read-only exact-commit Yggdrasil advisory knowledge verifier."""
import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path
from urllib.parse import unquote

SOURCE="14275a69ee553d2ed17c4a9e551d2486454d58f3"
DIGEST="f5b6f8f9d66e886ca12fbb8c2a8dd0578e2af98d46fe69205507af36648077af"
LINKS=re.compile(r"(?<!\\)\[\[([^\[\]\r\n]+)\]\]")
SECRET=re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|github_pat_[A-Za-z0-9_]{70,}|ghp_[A-Za-z0-9]{36}|AKIA[0-9A-Z]{16}")

def fail(message):
    raise RuntimeError(message)

def norm(value):
    return unicodedata.normalize("NFC",value.replace("\\","/")).casefold()

def main(root):
    graph=root/"Graphify"/"Source"/"graph.json"
    info=root/"Graphify"/"Source"/"LAST-BUILD.json"
    vault=root/"Graphify"/"Obsidian"
    manifest=vault/".graphify_obsidian_manifest.json"
    if any(not x.is_file() for x in (graph,info,manifest)):fail("SOURCE_OR_MANIFEST_MISSING")
    record=json.loads(info.read_text(encoding="utf-8-sig"))
    for k,v in (
        ("schema","research.advisory-graphify.v1"),
        ("source_repo","spoonman136668-ai/Yggdrasil"),
        ("source_branch","main"),("source_commit",SOURCE),
        ("graphify_version","0.9.53"),("mode","code-only"),
        ("model_calls",0),("authority","advisory_navigation_only"),
        ("scientific_authority",False),("promotion_authorized",False)):
        if record.get(k)!=v:fail("SOURCE_BOUNDARY_"+k.upper())
    digest=hashlib.sha256(graph.read_bytes()).hexdigest()
    if digest!=DIGEST or record.get("graph_sha256")!=DIGEST:fail("PUBLISHED_GRAPH_HASH_DRIFT")
    parsed=json.loads(graph.read_text(encoding="utf-8-sig"))
    if not isinstance(parsed,(dict,list)) or not parsed:fail("GRAPH_STRUCTURE")
    m=json.loads(manifest.read_text(encoding="utf-8-sig"))
    if not isinstance(m,(dict,list)) or not m:fail("MANIFEST_STRUCTURE")
    print("YGG_ADVISORY_EXACT_COMMITTED_GRAPH_SHA256=PASS",flush=True)
    notes=sorted(vault.rglob("*.md"))
    if len(notes)!=144 or record.get("obsidian_notes")!=len(notes):fail("NOTE_COUNT")
    files={}
    bases={}
    for note in notes:
        if note.is_symlink():fail("SYMLINK_FORBIDDEN")
        if len(str(note.absolute()))>=260:fail("WINDOWS_RETAIL_PATH_EXCEEDED")
        rel=note.relative_to(vault).as_posix()
        key=norm(rel[:-3])
        if key in files:fail("CASEFOLD_COLLISION")
        files[key]=note
        bases.setdefault(norm(note.stem),[]).append(key)
    print("YGG_ADVISORY_144_NOTES_WINDOWS_PATHS=PASS",flush=True)
    count=0
    for note in notes:
        content=note.read_text(encoding="utf-8-sig")
        if SECRET.search(content):fail("POTENTIAL_SECRET_IN_NOTE")
        for hit in LINKS.findall(content):
            target=unquote(hit.split("|",1)[0].split("#",1)[0].strip())
            if not target:continue
            target=target.replace("\\","/")
            if target.startswith("/") or ".." in target.split("/"):fail("LINK_PATH_TRAVERSAL")
            if target.lower().endswith(".md"):target=target[:-3]
            key=norm(target)
            if "/" in target:
                from_here=norm((note.parent/target).relative_to(vault).as_posix())
                if key not in files and from_here not in files:fail("UNRESOLVED_NESTED_WIKILINK")
            elif len(bases.get(key,()))!=1:
                fail("UNRESOLVED_OR_AMBIGUOUS_WIKILINK")
            count+=1
    if count==0:fail("NO_WIKILINKS")
    if SECRET.search(graph.read_text(encoding="utf-8-sig")):fail("POTENTIAL_SECRET_IN_GRAPH")
    print("YGG_ADVISORY_ALL_WIKILINKS=PASS",flush=True)
    print("YGG_ADVISORY_WIKILINKS_CHECKED="+str(count),flush=True)
    print("YGG_ADVISORY_BASIC_SECRET_PATTERN_SCREEN=PASS",flush=True)
    print("YGG_ADVISORY_REVIEW_ONLY_NO_RESEARCH_PROMOTION=PASS",flush=True)

if __name__=="__main__":
    try:
        main(Path(sys.argv[1]).resolve())
    except (RuntimeError,OSError,ValueError,KeyError,IndexError,UnicodeError) as e:
        print("YGG_ADVISORY_VALIDATION=FAIL:"+str(e.__class__.__name__ if not isinstance(e,RuntimeError) else e),flush=True)
        sys.exit(1)
