package main

import (
 "bytes"
 "strings"
 "testing"
)

func TestG61SourceEligibility(t *testing.T) {
 for _,p:=range []string{"f139/local_controller.py","fsaadmission/archive.go","scripts/F139WindowsJobSupervisor.cs"} {
  if !g61Eligible(p){t.Fatalf("missing source %s",p)}
 }
 for _,p:=range []string{jsonFile,htmlFile,iceFile,"private.key","output.exe"} {
  if g61Eligible(p){t.Fatalf("unsafe source %s",p)}
 }
}
func TestG61CSharpLocatorsAreProvisional(t *testing.T) {
 raw:=[]byte("public static class Worker\n{\n private struct Config {}\n public static int Run() { return 0; }\n}\n")
 s,e:=g61Extract("scripts/Job.cs","https://example.invalid/source",raw)
 if e!=nil{t.Fatal(e)}
 if len(s)!=2||s[0].Name!="Worker"||s[1].Name!="Config"{t.Fatalf("wrong C# names: %+v",s)}
 for _,v:=range s{if v.Evidence!="lexical-locator-only"||v.Start<1||strings.Contains(v.Evidence,"reviewed"){t.Fatal("C# confidence escalated")}}
}
func TestG61GoASTFailClosed(t *testing.T) {
 sy,e:=g61Extract("x.go","https://example.invalid",[]byte("package x\nfunc F(){}\n"))
 if e!=nil||len(sy)!=1||sy[0].Evidence!="go-ast-locator-only"{t.Fatalf("bad Go AST: %+v %v",sy,e)}
 if _,e=g61Extract("bad.go","https://example.invalid",[]byte("not Go"));e==nil{t.Fatal("unparseable source accepted")}
}
func TestG61HTMLNotAuthority(t *testing.T) {
 a:=Atlas{Schema:schema,Repository:repository,SourceCommit:g61Target,Authority:"public-source-navigation-only",
  Files:[]File{{Path:"x.cs",URL:"https://example.invalid"}},
  Symbols:[]Symbol{{File:"x.cs",Name:"<script>alert(1)</script>"}}}
 r,e:=render(a);if e!=nil{t.Fatal(e)}
 if bytes.Contains(r[htmlFile],[]byte("<script>alert(1)</script>")){t.Fatal("unescaped HTML")}
 if !bytes.Contains(r[htmlFile],[]byte("Public source syntax locators only")){t.Fatal("advisory label missing")}
}
func TestG61PinnedSourceAndCoverage(t *testing.T) {
 root,e:=rootPath();if e!=nil{t.Fatal(e)}
 a,s,e:=g61Build(root);if e!=nil{t.Fatal(e)}
 if s.Reused!=747||s.Modified!=16||s.Added!=18||s.CSharp!=1||a.Counts.Files!=781 {t.Fatalf("scope drift %+v %+v",s,a.Counts)}
 found:=false
 for _,v:=range a.Symbols {
  if v.File=="scripts/F139WindowsJobSupervisor.cs"&&v.Name=="F139WindowsJobSupervisor" {
   if v.Evidence!="lexical-locator-only"||!strings.Contains(v.URL,g61Target){t.Fatal("C# locator provenance drift")}
   found=true
  }
 }
 if !found{t.Fatal("new C# class not navigable")}
 for _,f:=range a.Files {
  if strings.HasSuffix(f.Path,".go")&&f.URL==""{t.Fatal("missing Go source identity")}
 }
}
