"""F112-O synthetic graph-archive integrity and false source-direction tests."""
import hashlib
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest import mock
import warnings
import zipfile

import f112o_publisher_graph_declaration as p
import f112o_synthetic_archive_direction as z

def digest(x):
    return hashlib.sha256(x).hexdigest()

def build_zip(folder,entries,compression=zipfile.ZIP_STORED):
    archive=folder/"graph.zip"
    with zipfile.ZipFile(archive,"w",compression=compression) as out:
        for name,raw in entries:
            out.writestr(name,raw)
    return archive

def manifest(file,entries):
    return {
        "archive_bytes":file.stat().st_size,
        "archive_sha256":digest(file.read_bytes()),
        "members":{k:{"bytes":len(v),"sha256":digest(v)} for k,v in entries},
    }

class OriginalArchiveCustodyTests(unittest.TestCase):
    def test_exact_bytes_synthetic_fixture_success_never_scientific_admission(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            data=[("triples.txt",b"alpha|edge.label|beta\n")]
            filename=build_zip(root,data)
            report=z.verify_fixture_archive(filename,manifest(filename,data))
            self.assertEqual(report["status"],"SYNTHETIC_FIXTURE_BYTES_VERIFIED_ONLY")
            self.assertEqual(report["all_members_checked"],1)
            self.assertFalse(report["freebase_graph_admitted"])
            self.assertFalse(report["original_freebase_archive_verified"])
            self.assertEqual(report["graph_queries"],0)

    def test_original_archive_sha_mismatch_and_member_sha_mismatch_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            data=[("edges.txt",b"a|r|b\n")]
            file=build_zip(root,data)
            m=manifest(file,data)
            m["archive_sha256"]="0"*64
            with self.assertRaises(z.Denied):z.verify_fixture_archive(file,m)
            m=manifest(file,data)
            m["members"]["edges.txt"]["sha256"]="0"*64
            with self.assertRaises(z.Denied):z.verify_fixture_archive(file,m)

    def test_archive_zip_slip_absolute_backslash_and_duplicate_denied(self):
        for name in ("../bad.txt","/absolute","x\\bad","a/./b","a//b","a/../b","C:drive"):
            self.assertFalse(z.valid_member_name(name),name)
            with tempfile.TemporaryDirectory() as d:
                root=Path(d)
                data=[(name,b"xyz")]
                file=build_zip(root,data)
                with self.assertRaises(z.Denied):z.verify_fixture_archive(file,manifest(file,data))
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore",UserWarning)
                file=build_zip(root,[("edges.txt",b"A"),("edges.txt",b"B")])
            m={"archive_bytes":file.stat().st_size,
               "archive_sha256":digest(file.read_bytes()),
               "members":{"edges.txt":{"bytes":1,"sha256":digest(b"B")}}}
            with self.assertRaises(z.Denied):z.verify_fixture_archive(file,m)

    def test_symlink_nested_and_zip_bomb_denied(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            file=root/"link.zip"
            info=zipfile.ZipInfo("edge.txt")
            info.create_system=3
            info.external_attr=(stat.S_IFLNK|0o777)<<16
            with zipfile.ZipFile(file,"w") as output:output.writestr(info,b"target")
            m=manifest(file,[("edge.txt",b"target")])
            with self.assertRaises(z.Denied):z.verify_fixture_archive(file,m)
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            large=b"x"*100000
            data=[("huge.txt",large)]
            file=build_zip(root,data,compression=zipfile.ZIP_DEFLATED)
            with self.assertRaises(z.Denied):z.verify_fixture_archive(file,manifest(file,data))

    def test_truncated_and_undeclared_extra_member_denied(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            data=[("one.txt",b"one"),("two.txt",b"two")]
            file=build_zip(root,data)
            m=manifest(file,data[:1])
            with self.assertRaises(z.Denied):z.verify_fixture_archive(file,m)
            raw=file.read_bytes()
            file.write_bytes(raw[:len(raw)//2])
            m=manifest(file,data)
            with self.assertRaises(z.Denied):z.verify_fixture_archive(file,m)

    def test_synthetic_direction_witness_never_source_freebase_direction(self):
        edges=[("film","film.role","director"),
               ("actor","film.role","film")]
        disp=z.direction_disposition(edges,"film","film.role")
        self.assertEqual(disp["synthetic_candidate_count"],2)
        self.assertTrue(disp["synthetic_direction_ambiguous"])
        self.assertFalse(disp["original_freebase_graph_directions_qualified"])
        self.assertFalse(disp["source_predicate_direction_certificate"])
        only=z.direction_disposition([edges[0]],"film","film.role")
        self.assertEqual(only["synthetic_candidate_count"],1)
        self.assertFalse(only["original_freebase_graph_directions_qualified"])
        zero=z.direction_disposition([edges[0]],"unknown","film.role")
        self.assertEqual(zero["synthetic_candidate_count"],0)
        with self.assertRaises(z.Denied):
            z.synthetic_direction_candidates([("no-triple",)],"a","r")

    def test_publisher_text_is_documented_logical_order_not_physical_direction(self):
        sample=("# FreebaseQA (v1.0) Freebase\n"
                "Freebase triples.\n"
                "2.2GB zip 16M 182M\n"
                "CC-BY-4.0\n"
                "The path from the topic entity node to the answer node\n"+p.GRAPH_LINK)
        declaration=p.interpret_declaration(sample,"Attribution 4.0 International")
        self.assertTrue(declaration["author_declares_logical_topic_to_answer_path"])
        self.assertFalse(declaration["logical_order_is_graph_edge_orientation"])
        self.assertFalse(declaration["original_graph_archive_sha256_provided_in_readme"])
        self.assertFalse(declaration["original_graph_ready_for_query"])
        with self.assertRaises(p.Denied):
            p.interpret_declaration(sample.replace("182M","18M"),
                                    "Attribution 4.0 International")

    def test_no_original_json_fetch_paths_admitted(self):
        for source in p.DENIED_SPLITS:
            with self.assertRaises(p.Denied):
                p.document_bytes(Path("."),source)
        with self.assertRaises(p.Denied):
            p.git_metadata(Path("."),["rev-parse","HEAD:FreebaseQA-eval.json"])
        with self.assertRaises(p.Denied):
            p.git_metadata(Path("."),["show","HEAD:FreebaseQA-train.json"])

if __name__=="__main__":unittest.main()
