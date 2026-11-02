"""Development-only integration oracle invoked by the Go adapter regression.

Consumed history here is a controlled fixture, not the original owner ledger.
"""
import json
import sys
from pathlib import Path

from f139.nci04_genenv_source import compile_operator_vectors
from f139.nci04_model_free_search import candidates, normalized
from f139.nci04_portfolio_source_boundary import _sha


def check(raw):
    before = Path("f139/fixtures/model_free_yggdrasil_992ef.py").read_bytes()
    consumed = tuple(candidates(before))
    result = json.loads(raw)["result"]
    # Content identity of the actual existing generator and compiler, not a
    # family name standing in for source. This oracle grants no owner authority.
    paths = ("genenv/genenv.go", "f139/nci04_genenv_source.py",
             "f139/nci04_model_free_search.py")
    mechanism = b"".join(p.encode() + b"\0" + Path(p).read_bytes() for p in paths)
    receipts = compile_operator_vectors(
        raw, result_sha256=_sha(raw), frozen_sha256=result["frozen_sha256"],
        history_sha256=result["history_sha256"], mechanism=mechanism,
        mechanism_sha256=_sha(mechanism), before=before,
        historical_sha256=frozenset(_sha(x[1]) for x in consumed),
        historical_ast_sha256=frozenset(normalized(x[1]) for x in consumed))
    assert len(receipts) == 4
    assert len({c.after_sha256 for c, _ in receipts}) == 4
    assert len({ast_id for _, ast_id in receipts}) == 4
    assert all(c.generator == "dgm_genenv" and c.lane == "Yggdrasil" for c, _ in receipts)
    return {"consumed_fixture_candidates": 3, "fresh_source_candidates": 4,
            "model_calls": 0, "owner_demonstration": False}


if __name__ == "__main__":
    raw = sys.stdin.buffer.read() if len(sys.argv) == 1 else b""
    if len(sys.argv) == 2:
        lines = Path(sys.argv[1]).read_text("utf-8-sig").splitlines()
        markers = [line.split("F139_GENENV_RESULT=", 1)[1] for line in lines
                   if "F139_GENENV_RESULT=" in line]
        if len(markers) != 1:
            raise ValueError("GENENV_EXACT_EXPORT_REQUIRED")
        raw = markers[0].encode("utf-8")
    print(json.dumps(check(raw), sort_keys=True))
