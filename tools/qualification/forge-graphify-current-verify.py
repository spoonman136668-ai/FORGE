#!/usr/bin/env python3
"""Read-only exact-commit FORGE advisory knowledge verifier."""
import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path
from urllib.parse import unquote

SOURCE="d8bccc604f8607bf10f9d8bc6aa568d1f98af559"
# Expected digest and note count must be pinned from independently read candidate commit, not derived from its own manifest.
LINKS=re.compile(r"(?<!\\)\[\[([^\[\]\r\n]+)\]\]")
SECRET=re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|github_pat_[A-Za-z0-9_]{70,}|ghp_[A-Za-z0-9]{36}|AKIA[0-9A-Z]{16}")

def fail(message):
    raise RuntimeError(message)

def norm(value):
    return unicodedata.normalize("NFC",value.replace("\\","/")).casefold()

def main(root, expected_digest, expected_notes):
    if not re.fullmatch(r"[0-9a-f]{64}",expected_digest):fail("EXPECTED_DIGEST_NOT_PINNED")
    if not 1 <= expected_notes <= 10000:fail("EXPECTED_NOTE_COUNT_NOT_PINNED")
    graph=root/"Graphify"/"Source"/"graph.json"
    info=root/"Graphify"/"Source"/"LAST-BUILD.json"
    vault=root/"Graphify"/"Obsidian"
    manifest=vault/".graphify_obsidian_manifest.json"
    if any(not x.is_file() for x in (graph,info,manifest)):fail("SOURCE_OR_MANIFEST_MISSING")
    record=json.loads(info.read_text(encoding="utf-8-sig"))
    for k,v in (
        ("schema","research.advisory-graphify.v1"),
        ("source_repo","spoonman136668-ai/FORGE"),
        ("source_branch","main"),("source_commit",SOURCE),
        ("graphify_version","0.9.53"),("mode","code-only"),
        ("model_calls",0),("authority","advisory_navigation_only"),
        ("scientific_authority",False),("promotion_authorized",False)):
        if record.get(k)!=v:fail("SOURCE_BOUNDARY_"+k.upper())
    digest=hashlib.sha256(graph.read_bytes()).hexdigest()
    if digest!=expected_digest or record.get("graph_sha256")!=expected_digest:fail("PUBLISHED_GRAPH_HASH_DRIFT")
    readme=root/"README.md"
    if not readme.is_file():fail("READ_ME_MISSING")
    readme_text=readme.read_text(encoding="utf-8-sig")
    if SOURCE not in readme_text or expected_digest not in readme_text:fail("README_PIN_MISMATCH")
    parsed=json.loads(graph.read_text(encoding="utf-8-sig"))
    if not isinstance(parsed,(dict,list)) or not parsed:fail("GRAPH_STRUCTURE")
    m=json.loads(manifest.read_text(encoding="utf-8-sig"))
    if not isinstance(m,(dict,list)) or not m:fail("MANIFEST_STRUCTURE")
    print("FORGE_ADVISORY_EXACT_COMMITTED_GRAPH_SHA256=PASS",flush=True)
    notes=sorted(vault.rglob("*.md"))
    if len(notes)!=expected_notes or record.get("obsidian_notes")!=len(notes):fail("NOTE_COUNT")
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
    print("FORGE_ADVISORY_PINNED_NOTES_WINDOWS_PATHS=PASS",flush=True)
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
    print("FORGE_ADVISORY_ALL_WIKILINKS=PASS",flush=True)
    print("FORGE_ADVISORY_WIKILINKS_CHECKED="+str(count),flush=True)
    print("FORGE_ADVISORY_BASIC_SECRET_PATTERN_SCREEN=PASS",flush=True)
    print("FORGE_ADVISORY_REVIEW_ONLY_NO_RESEARCH_PROMOTION=PASS",flush=True)

if __name__=="__main__":
    try:
        if len(sys.argv)!=4:fail("REQUIRED_EXACT_DIGEST_AND_COUNT_ARGUMENTS")
        main(Path(sys.argv[1]).resolve(),sys.argv[2],int(sys.argv[3]))
    except (RuntimeError,OSError,ValueError,KeyError,IndexError,UnicodeError) as e:
        print("FORGE_ADVISORY_VALIDATION=FAIL:"+str(e.__class__.__name__ if not isinstance(e,RuntimeError) else e),flush=True)
        sys.exit(1)
