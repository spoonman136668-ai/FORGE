"""Zero-Dependency Read-Only HTML Research Dashboard Exporter for FORGE F139 (Gate 22).

Reads a FORGE lab `state_dir` (`research_evidence.jsonl` + `checkpoint_vault/`)
strictly read-only, verifies the cryptographic hash chain, and writes a single
self-contained dark-mode HTML dashboard showing:
  - Chain integrity & KPI summary cards,
  - Per-architecture family breakdown (verified, negative, best metric),
  - Vaulted checkpoints (exact SHA-256 digests & sizes),
  - Complete chronological trial log (including retained crashes/failures).

Usage:
  python -B -m f139.nci04_report_export --state-dir ./lab_state --out report.html
"""
from __future__ import annotations

import argparse
import html
import json
from pathlib import Path

from f139.nci04_checkpoint_vault import list_vault_checkpoints, vault_disk_usage_bytes
from f139.nci04_evidence_store import read_evidence_records, summarize_evidence_store
from f139.nci04_native_contract import canonical, digest

EXPORT_SCHEMA = "forge.f139.html-research-dashboard-export.v1"


def export_research_html_report(*, state_dir: Path, output_html: Path) -> dict:
    """Export verified evidence store and checkpoint vault to a self-contained HTML file."""
    state_dir = Path(state_dir).resolve()
    store_path = state_dir / "research_evidence.jsonl"
    vault_root = state_dir / "checkpoint_vault"

    records = read_evidence_records(store_path)
    summary = summarize_evidence_store(store_path)
    ckpts = list_vault_checkpoints(vault_root)
    vault_bytes = vault_disk_usage_bytes(vault_root)

    verified_total = sum(1 for r in records if r["status"] in ("VERIFIED", "QUALIFIED"))
    negative_total = sum(1 for r in records if r["status"] in ("NEGATIVE", "REJECTED"))

    fam_rows = []
    for fam, st in sorted(summary["by_family"].items()):
        best_str = (
            f"{st['best_metric']} = {st['best_value']:.6g}"
            if st["best_value"] is not None
            else "—"
        )
        fam_rows.append(
            f"<tr><td><code>{html.escape(fam)}</code></td>"
            f"<td>{st['total']}</td><td>{st['verified'] + st['qualified']}</td>"
            f"<td>{st['negative'] + st['rejected']}</td>"
            f"<td><code>{html.escape(best_str)}</code></td></tr>"
        )

    ckpt_rows = []
    for c in ckpts[-50:]:
        ckpt_rows.append(
            f"<tr><td><code>{html.escape(c['experiment_id'])}</code></td>"
            f"<td>{html.escape(c['method_family'])}</td>"
            f"<td>{c['size_bytes']} B</td>"
            f"<td><code>{html.escape(c['checkpoint_sha256'][:16])}…</code></td></tr>"
        )

    trial_rows = []
    for r in reversed(records[-100:]):
        val = f"{r['primary_metric']}={r['primary_value']}" if r.get("primary_value") is not None else "—"
        err = r.get("payload", {}).get("error", "")
        badge = "ok" if r["status"] in ("VERIFIED", "QUALIFIED") else "bad"
        trial_rows.append(
            f"<tr><td>#{r['seq']}</td>"
            f"<td><code>{html.escape(r['method_family'])}</code></td>"
            f"<td><span class='badge {badge}'>{html.escape(r['status'])}</span></td>"
            f"<td><code>{html.escape(str(val))}</code></td>"
            f"<td>{html.escape(str(err)[:120])}</td></tr>"
        )

    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>FORGE Research Dashboard</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0f1419; color: #e6edf3; margin: 0; padding: 28px; }}
  h1, h2 {{ margin: 0 0 12px 0; font-weight: 600; }}
  .sub {{ color: #8b949e; font-size: 13px; margin-bottom: 24px; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 14px; margin-bottom: 28px; }}
  .card {{ background: #161b22; border: 1px solid #30363d; border-radius: 10px; padding: 16px; }}
  .kpi {{ font-size: 26px; font-weight: 700; color: #58a6ff; margin-top: 6px; }}
  .label {{ font-size: 12px; color: #8b949e; text-transform: uppercase; letter-spacing: .05em; }}
  table {{ width: 100%; border-collapse: collapse; margin-bottom: 28px; background: #161b22; border: 1px solid #30363d; border-radius: 8px; overflow: hidden; }}
  th, td {{ text-align: left; padding: 10px 12px; border-bottom: 1px solid #21262d; font-size: 13px; }}
  th {{ background: #1c2128; color: #8b949e; font-weight: 600; }}
  code {{ background: #21262d; padding: 2px 6px; border-radius: 4px; font-size: 12px; }}
  .badge {{ padding: 2px 8px; border-radius: 99px; font-size: 11px; font-weight: 600; }}
  .ok {{ background: #1f6feb33; color: #58a6ff; }}
  .bad {{ background: #f8514933; color: #ff7b72; }}
</style>
</head>
<body>
  <h1>FORGE Experimental Research Dashboard</h1>
  <div class="sub">Chain Verified: <strong>{summary['chain_verified']}</strong> &middot; Head Digest: <code>{html.escape(summary['head_record_sha256'][:16])}…</code> &middot; Auto-Promote: <code>False</code> &middot; Paid Calls: <code>0</code></div>
  <div class="grid">
    <div class="card"><div class="label">Total Trials</div><div class="kpi">{summary['total_records']}</div></div>
    <div class="card"><div class="label">Verified / Qualified</div><div class="kpi">{verified_total}</div></div>
    <div class="card"><div class="label">Negative / Crashed</div><div class="kpi">{negative_total}</div></div>
    <div class="card"><div class="label">Vault Checkpoints</div><div class="kpi">{len(ckpts)} ({vault_bytes} B)</div></div>
  </div>
  <h2>Per-Architecture Family Summary</h2>
  <table><thead><tr><th>Family</th><th>Total</th><th>Verified</th><th>Negative</th><th>Best Metric</th></tr></thead>
  <tbody>{''.join(fam_rows) or '<tr><td colspan="5">No records yet</td></tr>'}</tbody></table>
  <h2>Vaulted Checkpoints (Latest 50)</h2>
  <table><thead><tr><th>Experiment</th><th>Family</th><th>Size</th><th>SHA-256</th></tr></thead>
  <tbody>{''.join(ckpt_rows) or '<tr><td colspan="4">No checkpoints vaulted yet</td></tr>'}</tbody></table>
  <h2>Recent Trial Ledger (Latest 100)</h2>
  <table><thead><tr><th>Seq</th><th>Family</th><th>Status</th><th>Primary Metric</th><th>Error / Notes</th></tr></thead>
  <tbody>{''.join(trial_rows) or '<tr><td colspan="5">No trials recorded yet</td></tr>'}</tbody></table>
</body>
</html>
"""
    out = Path(output_html)
    out.parent.mkdir(parents=True, exist_ok=True)
    raw_html = page.encode("utf-8")
    out.write_bytes(raw_html)

    receipt = {
        "schema": EXPORT_SCHEMA,
        "output_html": str(out.resolve()),
        "html_sha256": digest(raw_html),
        "html_bytes": len(raw_html),
        "total_records": summary["total_records"],
        "vault_checkpoints": len(ckpts),
        "chain_verified": summary["chain_verified"],
        "paid_model_calls": 0,
        "auto_promote_checkpoint": False,
        "scientific_first_use": False,
    }
    receipt["receipt_sha256"] = digest(canonical(receipt))
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export FORGE research evidence to HTML dashboard")
    parser.add_argument("--state-dir", type=Path, required=True, help="FORGE lab state directory")
    parser.add_argument("--out", type=Path, required=True, help="Output HTML file path")
    ns = parser.parse_args(argv)
    rcpt = export_research_html_report(state_dir=ns.state_dir, output_html=ns.out)
    print(json.dumps(rcpt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
