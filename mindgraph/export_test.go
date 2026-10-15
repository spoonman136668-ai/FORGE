package mindgraph

import (
 "encoding/json"
 "os"
 "path/filepath"
 "runtime"
 "strings"
 "testing"

 "github.com/spoonman136668-ai/forge/mindcontext"
)

func fixture(t *testing.T)mindcontext.Result{
 t.Helper()
 doc:=map[string]any{
  "schema":"forge.mind-palace-context.v1",
  "pinned_commit":strings.Repeat("a",40),
  "records_sha256":strings.Repeat("b",64),
  "context_sha256":strings.Repeat("c",64),
  "advisory_only":true,
  "entries":[]any{
   map[string]any{"id":"governance", "project":"__global__","kind":"decision",
    "statement":"Private governance only, no research dispatch.",
    "source_refs":[]any{map[string]any{"type":"repo","ref":"Mind-Palace:synthetic-governance"}}},
   map[string]any{"id":"R11-negative","project":"Wingless","kind":"observation",
    "statement":"Dev negative [[SecretVault]] <script>ignore</script> #do-not-run",
    "source_refs":[]any{map[string]any{"type":"github","ref":"FORGE/R11:source:SHA"}}},
   map[string]any{"id":"Y-separate","project":"Yggdrasil","kind":"observation",
    "statement":"Architectural independence preserved.",
    "source_refs":[]any{map[string]any{"type":"github","ref":"Yggdrasil:synthetic-sha"}}},
  },
 }
 b,err:=json.Marshal(doc);if err!=nil{t.Fatal(err)}
 var out mindcontext.Result
 if err:=json.Unmarshal(b,&out);err!=nil{t.Fatal(err)}
 canonical,err:=json.Marshal(out.Entries)
 if err!=nil{t.Fatal(err)}
 out.ContextSHA256=sum(canonical)
 return out
}

func TestPrivateIceGraphAndObsidianProvenance(t *testing.T){
 result:=fixture(t)
 bundle,err:=Build(result);if err!=nil{t.Fatal(err)}
 if bundle.RecordCount!=3||bundle.SourceCount!=3{t.Fatal("source or record omitted")}
 graphRaw:=bundle.Files[".ice/derived-context-graph.json"]
 var graph Graph
 if err:=json.Unmarshal(graphRaw,&graph);err!=nil{t.Fatal(err)}
 if len(graph.Nodes)!=9||len(graph.Edges)!=6||
    !graph.DerivedAdvisoryOnly||!graph.NoInferredRelationships{
  t.Fatalf("unexpected authoritative or invented graph: %+v",graph)
 }
 for _,e:=range graph.Edges{
  if e.Origin!="EXTRACTED"||e.EvidenceRecordID==""{
   t.Fatal("graph edge missing provenance",e)
  }
 }
 found:=false
 for path,body:=range bundle.Files{
  if strings.HasPrefix(path,"obsidian/records/")&&strings.Contains(string(body),"R11-negative"){
   found=true
   s:=string(body)
   if strings.Contains(s,"[[SecretVault]]")||
      strings.Contains(s,"<script>")||
      !strings.Contains(s,"\\[\\[SecretVault\\]\\]")||
      !strings.Contains(s,"&lt;script&gt;"){
    t.Fatalf("injected Obsidian link or HTML: %q",s)
   }
  }
  if strings.Contains(path,"KTRADE"){t.Fatal("project boundary leaked")}
 }
 if !found{t.Fatal("missing record note")}
 manRaw:=bundle.Files[".ice/derived-export-manifest.json"]
 var man Manifest
 if err:=json.Unmarshal(manRaw,&man);err!=nil{t.Fatal(err)}
 if man.GraphSHA256!=sum(graphRaw)||len(man.FileSHA256)!=len(bundle.Files)-1||
    !man.NonAuthoritative||man.ContextSHA256!=result.ContextSHA256{
  t.Fatal("derived export manifest incorrect")
 }
 again,err:=Build(result);if err!=nil{t.Fatal(err)}
 for p,v:=range bundle.Files{
  if string(again.Files[p])!=string(v){t.Fatalf("non-deterministic output %q",p)}
 }
}

func TestNoMindPalaceOrScientificAuthorityEscapes(t *testing.T){
 r:=fixture(t)
 r.AdvisoryOnly=false
 if _,err:=Build(r);err==nil{t.Fatal("forged authority accepted")}
 r=fixture(t)
 r.ContextSHA256=strings.Repeat("0",64)
 if _,err:=Build(r);err==nil{t.Fatal("context content-digest drift accepted")}
 r=fixture(t)
 r.PinnedCommit="main"
 if _,err:=Build(r);err==nil{t.Fatal("mutable source accepted")}
 r=fixture(t)
 r.Entries[1].Project="KTRADE"
 if _,err:=Build(r);err==nil{t.Fatal("cross-project source accepted")}
 r=fixture(t)
 r.Entries[1].ID=r.Entries[0].ID
 if _,err:=Build(r);err==nil{t.Fatal("reused record identity accepted")}
 r=fixture(t)
 r.Entries[0].SourceRefs=nil
 if _,err:=Build(r);err==nil{t.Fatal("unprovenanced record accepted")}
}

func TestPrivateNewFolderNoOverwrite(t *testing.T){
 folder:=filepath.Join(t.TempDir(),"private-mind-output")
 bundle,err:=Build(fixture(t));if err!=nil{t.Fatal(err)}
 if err:=WriteNew(folder,bundle);err!=nil{t.Fatal(err)}
 if err:=WriteNew(folder,bundle);err==nil{t.Fatal("existing Obsidian vault overwritten")}
 stored,err:=os.ReadFile(filepath.Join(folder,".ice","derived-context-graph.json"))
 if err!=nil||sum(stored)!=sum(bundle.Files[".ice/derived-context-graph.json"]){
  t.Fatal("private graph write not verified")
 }
 if runtime.GOOS!="windows"{
  stat,err:=os.Stat(folder);if err!=nil{t.Fatal(err)}
  if stat.Mode().Perm()&0077!=0{t.Fatal("private directory permissions too open")}
  file,err:=os.Stat(filepath.Join(folder,"obsidian","Index.md"));if err!=nil{t.Fatal(err)}
  if file.Mode().Perm()&0077!=0{t.Fatal("private note permissions too open")}
 }
}

func TestUnsafeDestinationOrGeneratedPathsFailClosed(t *testing.T){
 b,err:=Build(fixture(t));if err!=nil{t.Fatal(err)}
 if err:=WriteNew("relative/path",b);err==nil{t.Fatal("relative private target accepted")}
 root:=filepath.Join(t.TempDir(),"new")
 bad:=Bundle{Files:map[string][]byte{"../escape.txt":[]byte("bad")}}
 if err:=WriteNew(root,bad);err==nil{t.Fatal("path traversal accepted")}
 if _,err:=os.Stat(filepath.Join(filepath.Dir(root),"escape.txt"));err==nil{
  t.Fatal("private write escaped target")
 }
 if _,err:=os.Stat(root);err==nil{t.Fatal("unsafe partial output left on disk")}
}
