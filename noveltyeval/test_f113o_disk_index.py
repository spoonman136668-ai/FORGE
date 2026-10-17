"""F113-O: source-neutral disk index adverse tests, original Freebase blocked."""
import hashlib
from pathlib import Path
import sqlite3
import tempfile
import unittest

import f113o_disk_index as f

SOURCE=b"film.a\tfilm.film.directed_by\tdirector.a\n"+(
       b"director.a\tpeople.person.parents\tparent.a\n") + (
       b"director.b\tpeople.person.parents\tparent.b\n") + (
       b"film.a\tfilm.film.directed_by\tdirector.b\n") + (
       b"actor.a\tfilm.film.directed_by\tfilm.a\n")

class SyntheticDiskIndexFixtures(unittest.TestCase):
    def setUp(self):
        self.scratch=tempfile.TemporaryDirectory(prefix="f113o-test-")
        self.addCleanup(self.scratch.cleanup)
        self.base=Path(self.scratch.name)
        self.source_dir=self.base/"source"
        self.index_dir=self.base/"index"
        self.source_dir.mkdir()
        self.index_dir.mkdir()
        self.source=self.source_dir/"fixture.tsv"
        self.dest=self.index_dir/"fixture.sqlite"
        self.source.write_bytes(SOURCE)

    def build(self,raw=None,rows=5):
        if raw is None:raw=self.source.read_bytes()
        return f.build_fixture(self.source,self.dest,f.digest_bytes(raw),len(raw),rows)

    def test_readonly_exact_two_step_and_direction_ambiguity_are_explicit(self):
        proof=self.build()
        self.assertTrue(proof["transaction_published"])
        self.assertFalse(proof["original_freebase_source_admitted"])
        forward=f.resolve_fixture(self.dest,proof["source_sha256"],proof["sqlite_sha256"],
            "film.a",[("film.film.directed_by","forward"),
                      ("people.person.parents","forward")],f.AUTH)
        backward=f.resolve_fixture(self.dest,proof["source_sha256"],proof["sqlite_sha256"],
            "film.a",[("film.film.directed_by","reverse")],f.AUTH)
        self.assertEqual(forward,["parent.a","parent.b"])
        self.assertEqual(backward,["actor.a"])
        self.assertEqual(f.resolve_fixture(self.dest,proof["source_sha256"],proof["sqlite_sha256"],
            "unknown",[("film.film.directed_by","forward")],f.AUTH),[])
        self.assertTrue(self.dest.is_file())

    def test_wrong_digest_size_count_and_duplication_never_publish(self):
        with self.assertRaises(f.Denied):
            f.build_fixture(self.source,self.dest,"0"*64,len(SOURCE),5)
        self.assertFalse(self.dest.exists())
        with self.assertRaises(f.Denied):
            f.build_fixture(self.source,self.dest,f.digest_bytes(SOURCE),len(SOURCE)+1,5)
        self.assertFalse(self.dest.exists())
        with self.assertRaises(f.Denied):self.build(rows=6)
        self.assertFalse(self.dest.exists())
        duplicate=SOURCE+SOURCE.splitlines(keepends=True)[0]
        self.source.write_bytes(duplicate)
        with self.assertRaises(f.Denied):self.build(raw=duplicate,rows=6)
        self.assertFalse(self.dest.exists())

    def test_missing_line_crlf_invalid_fields_sql_injection_and_truncation(self):
        for raw in (b"a\tr\tb",
                    b"a\tr\tb\r\n",
                    b"a\tr\n",
                    b"a\tbad role\tb\n",
                    b"a\tDROP TABLE edges;--\tb\n",
                    b"a\trole\tb\tfour\n",
                    b"a\x00a\trole\tb\n",
                    b"a\tr\tb\n" + b"z"*800+b"\n"):
            self.source.write_bytes(raw)
            with self.assertRaises(f.Denied):
                f.build_fixture(self.source,self.dest,f.digest_bytes(raw),len(raw),raw.count(b"\n"))
            self.assertFalse(self.dest.exists())

    def test_real_source_and_bad_auth_hard_refuse_even_with_approved_fixture(self):
        proof=self.build()
        kwargs=dict(db_path=self.dest,source_sha256=proof["source_sha256"],
                    index_sha256=proof["sqlite_sha256"],root="film.a",
                    steps=[("film.film.directed_by","forward")])
        for authorization in ("freebaseqa","",None,"ORIGINAL_FREEBASE_GRAPH"):
            with self.assertRaises(f.Denied):
                f.resolve_fixture(**kwargs,auth=authorization)
        for steps in ([],[("film.film.directed_by","unknown")],
                      [("film.film.directed_by","forward")]*3,
                      [("r' OR 1=1 --","forward")]):
            with self.assertRaises(f.Denied):
                f.resolve_fixture(self.dest,proof["source_sha256"],
                                  proof["sqlite_sha256"],"film.a",steps,f.AUTH)
        graph=f.original_freebase_eligibility({"publisher_source_url":"forged"})
        self.assertFalse(graph["full_publisher_graph_admitted"])
        self.assertFalse(graph["original_edge_directions_authenticated"])
        self.assertEqual(graph["source_graph_queries"],0)
        self.assertGreater(len(graph["unresolved_custody_fields"]),0)

    def test_wrong_sha_or_tampered_index_denied_and_no_index_write(self):
        proof=self.build()
        with self.assertRaises(f.Denied):
            f.resolve_fixture(self.dest,proof["source_sha256"],"0"*64,
                              "film.a",[("film.film.directed_by","forward")],f.AUTH)
        with self.assertRaises(f.Denied):
            f.resolve_fixture(self.dest,"0"*64,proof["sqlite_sha256"],
                              "film.a",[("film.film.directed_by","forward")],f.AUTH)
        with self.assertRaises(f.Denied):
            self.build()
        altered=self.dest.read_bytes()
        self.dest.write_bytes(altered+b"x")
        with self.assertRaises(f.Denied):
            f.resolve_fixture(self.dest,proof["source_sha256"],proof["sqlite_sha256"],
                              "film.a",[("film.film.directed_by","forward")],f.AUTH)

    def test_synthetic_source_symlink_rejected_and_missing_input(self):
        link=self.source_dir/"source-link.tsv"
        try:link.symlink_to(self.source)
        except (OSError,NotImplementedError):return
        with self.assertRaises(f.Denied):
            f.build_fixture(link,self.dest,f.digest_bytes(SOURCE),len(SOURCE),5)
        self.assertFalse(self.dest.exists())

    def test_explicit_frontier_budget_no_truncation_even_two_hop(self):
        data=b"".join(
          b"root\ta.b\tn%03d\n"%i for i in range(130))
        self.source.write_bytes(data)
        proof=self.build(raw=data,rows=130)
        with self.assertRaises(f.Denied):
            f.resolve_fixture(self.dest,proof["source_sha256"],proof["sqlite_sha256"],
                              "root",[("a.b","forward")],f.AUTH)
        with self.assertRaises(f.Denied):
            f.resolve_fixture(self.dest,proof["source_sha256"],proof["sqlite_sha256"],
                              "root",[("a.b","forward")],f.AUTH,max_frontier=10)

    def test_no_publisher_archive_source_opened(self):
        report=f.run_diagnostic()
        self.assertEqual(report["status"],f.STATUS)
        self.assertEqual(report["source"]["status"],
                         "PUBLISHER_SOURCE_LOCATED_ARCHIVE_BYTES_UNAVAILABLE")
        self.assertFalse(report["source_archive_downloaded"])
        self.assertEqual(report["index_bytes_written_from_original_freebase"],0)
        self.assertEqual(report["synthetic_verified_two_hop_nodes"],2)
        self.assertEqual(report["synthetic_verified_reverse_nodes"],1)
        self.assertEqual(report["real_qa_answers_scored"],0)

if __name__=="__main__":unittest.main()
