import json
import pathlib
import tempfile
import unittest
import xml.etree.ElementTree as ET

import l9_split_builder as l9

class SplitBuilderTests(unittest.TestCase):
    def test_category_partition_normalizes_case_and_space(self):
        self.assertEqual(l9.category_partition("  Artist "), l9.category_partition("artist"))

    def test_graph_identity_is_order_and_whitespace_invariant(self):
        a=[(" A ","p","B"),("B"," q "," C ")]
        b=[("B","q","C"),("A","p","B")]
        self.assertEqual(l9.graph_identity(a), l9.graph_identity(b))
        self.assertNotEqual(l9.graph_identity(a), l9.graph_identity([("A","p","DIFFERENT")]))

    def test_role_does_not_depend_on_path_id_or_reference_text(self):
        graph=[("A","p","B")]
        gid=l9.graph_identity(graph)
        r1=l9.example_role("TRAIN","Artist",gid)
        r2=l9.example_role("TRAIN","artist",gid)
        self.assertEqual(r1,r2)

    def test_manifest_rejects_test_or_path_escape(self):
        good={"role":"TRAIN","mode":"100644","oid":"a"*40,"path":"release_v3.0/en/train/1triples/Artist.xml"}
        l9.validate_manifest_entries([good])
        bad=dict(good,path="release_v3.0/en/test/rdf-to-text-generation-test-data-with-refs-en.xml")
        with self.assertRaises(l9.SplitError):
            l9.validate_manifest_entries([bad])

    def test_parser_ignores_entry_id_and_reference_text_for_identity(self):
        xml1=b'''<benchmark><entries><entry category="Artist" eid="1"><modifiedtripleset>
        <mtriple>A | p | B</mtriple></modifiedtripleset><lex><text>secret one</text></lex></entry></entries></benchmark>'''
        xml2=b'''<benchmark><entries><entry category="Artist" eid="999"><modifiedtripleset>
        <mtriple>A | p | B</mtriple></modifiedtripleset><lex><text>totally different words</text></lex></entry></entries></benchmark>'''
        a=l9.parse_blob(xml1,"TRAIN","1"*40)[0]
        b=l9.parse_blob(xml2,"TRAIN","2"*40)[0]
        self.assertEqual(a["graph_sha256"],b["graph_sha256"])
        self.assertEqual(a["role"],b["role"])
        self.assertNotIn("secret",json.dumps(a))

    def test_parser_rejects_missing_or_malformed_graph(self):
        missing=b'<benchmark><entries><entry category="Artist"><modifiedtripleset/></entry></entries></benchmark>'
        malformed=b'<benchmark><entries><entry category="Artist"><modifiedtripleset><mtriple>A | B</mtriple></modifiedtripleset></entry></entries></benchmark>'
        with self.assertRaises(l9.SplitError):
            l9.parse_blob(missing,"TRAIN","1"*40)
        with self.assertRaises(l9.SplitError):
            l9.parse_blob(malformed,"TRAIN","1"*40)

    def test_train_and_audit_category_rules_are_structurally_disjoint(self):
        categories=["Artist","Airport","Astronaut","Building","Company","City","University"]
        for c in categories:
            p=l9.category_partition(c)
            self.assertIn(p,{"L9_TRAIN_CATEGORY","L9_AUDIT_CATEGORY"})
            gid=l9.graph_identity([(c,"predicate","object")])
            train_role=l9.example_role("TRAIN",c,gid)
            dev_role=l9.example_role("DEV",c,gid)
            if p=="L9_AUDIT_CATEGORY":
                self.assertEqual(train_role,"UNUSED_TRAIN_HELDOUT_CATEGORY")
                self.assertEqual(dev_role,"L9_AUDIT_DEV")
            else:
                self.assertIn(train_role,{"L9_TRAIN","L9_SELECT"})
                self.assertEqual(dev_role,"UNUSED_DEV_TRAIN_CATEGORY")

if __name__ == "__main__":
    unittest.main()
