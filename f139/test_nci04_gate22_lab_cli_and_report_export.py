"""Tests for Gate 22: Multi-generation Lab CLI and HTML Research Dashboard Exporter."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from f139.nci04_lab_cli import LAB_CLI_SCHEMA, run_multi_generation_lab
from f139.nci04_report_export import EXPORT_SCHEMA, export_research_html_report

FORGE_ROOT = Path(__file__).resolve().parent.parent


class Gate22LabCLIAndReportExportTests(unittest.TestCase):
    def test_multi_generation_lab_cli_and_html_report_export_end_to_end(self):
        with tempfile.TemporaryDirectory(prefix="forge_gate22_") as td:
            root = Path(td)
            state_dir = root / "lab_state"
            out_html = root / "dashboard.html"

            # 1. Run 2-generation evolutionary sweep via Python API
            rep = run_multi_generation_lab(
                state_dir=state_dir,
                generations=2,
                wave_size=3,
            )
            self.assertEqual(rep["schema"], LAB_CLI_SCHEMA)
            self.assertEqual(rep["generations_executed"], 2)
            self.assertGreaterEqual(rep["total_verified"], 6)
            self.assertGreaterEqual(len(rep["overall_pareto_ids"]), 1)
            self.assertFalse(rep["auto_promote_checkpoint"])
            self.assertEqual(rep["paid_model_calls"], 0)

            # 2. Run Lab CLI with --markdown flag
            proc = subprocess.run(
                [sys.executable, "-B", "-m", "f139.nci04_lab_cli",
                 "--state-dir", str(state_dir), "--generations", "1", "--markdown"],
                cwd=str(FORGE_ROOT),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=60,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr.decode("utf-8", errors="replace"))
            self.assertIn("FORGE Multi-Generation Lab Leaderboard", proc.stdout.decode("utf-8"))

            # 3. Export self-contained HTML dashboard via CLI
            proc_html = subprocess.run(
                [sys.executable, "-B", "-m", "f139.nci04_report_export",
                 "--state-dir", str(state_dir), "--out", str(out_html)],
                cwd=str(FORGE_ROOT),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30,
                check=False,
            )
            self.assertEqual(proc_html.returncode, 0, proc_html.stderr.decode("utf-8", errors="replace"))
            rcpt = json.loads(proc_html.stdout.decode("utf-8").strip())
            self.assertEqual(rcpt["schema"], EXPORT_SCHEMA)
            self.assertTrue(rcpt["chain_verified"])
            self.assertTrue(out_html.is_file())
            html_text = out_html.read_text(encoding="utf-8")
            self.assertIn("FORGE Experimental Research Dashboard", html_text)
            self.assertIn("slow-fast-trust", html_text)

            # Direct API call also deterministic
            rcpt2 = export_research_html_report(state_dir=state_dir, output_html=out_html)
            self.assertEqual(rcpt["html_sha256"], rcpt2["html_sha256"])


if __name__ == "__main__":
    unittest.main()
