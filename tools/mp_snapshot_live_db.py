import pathlib, re, sqlite3, sys, urllib.parse

root = pathlib.Path(sys.argv[1]).resolve()
cfg = pathlib.Path(sys.argv[2]).resolve()
out = pathlib.Path(sys.argv[3]).resolve()
text = cfg.read_text(encoding="utf-8-sig")

state_indent = None
db_name = None
for line in text.splitlines():
    indent = len(line) - len(line.lstrip(" "))
    if re.fullmatch(r"\s*state:\s*(?:#.*)?", line):
        state_indent = indent
        continue
    if state_indent is None:
        continue
    if line.strip() and not line.lstrip().startswith("#") and indent <= state_indent:
        state_indent = None
        continue
    m = re.fullmatch(r"\s*sqlite_path:\s*(.+?)\s*(?:#.*)?", line)
    if m:
        db_name = m.group(1).strip().strip("\"'")
        break

if db_name is None:
    raise RuntimeError("MP_RECON_DB_LOCATOR")

p = pathlib.Path(db_name)
live = (p if p.is_absolute() else root / p).resolve()
if not live.is_relative_to(root) or not live.is_file():
    raise RuntimeError("MP_RECON_DB_SCOPE")

uri = "file:" + urllib.parse.quote(str(live).replace("\\", "/"), safe="/:") + "?mode=ro"
with sqlite3.connect(uri, uri=True, timeout=5.0) as src:
    src.execute("PRAGMA query_only=ON")
    with sqlite3.connect(str(out)) as dst:
        src.backup(dst)

with sqlite3.connect(str(out)) as db:
    if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
        raise RuntimeError("MP_RECON_SNAPSHOT_INTEGRITY")

print("MP_RECON_SNAPSHOT_INTEGRITY=PASS")
