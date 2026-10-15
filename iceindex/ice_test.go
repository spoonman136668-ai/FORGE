package iceindex

import (
 "encoding/json"
 "os"
 "path/filepath"
 "runtime"
 "strings"
 "testing"
)

type manifest struct {
 Schema string `json:"schema"`
 Project string `json:"project"`
 Repository string `json:"repository"`
 Visibility string `json:"visibility"`
 Authority string `json:"authority"`
 SourceParentCommit string `json:"source_parent_commit"`
 SourceParentTree string `json:"source_parent_tree"`
 Graphify struct{
  Package string `json:"package"`
  Version string `json:"version"`
  Mode string `json:"mode"`
  ModelCalls int `json:"model_calls"`
  BuildTool string `json:"build_tool"`
 } `json:"graphify"`
 Safeguards map[string]bool `json:"safeguards"`
 Artifacts map[string]string `json:"artifacts"`
}
type node struct{
 ID string `json:"id"`
 Kind string `json:"kind"`
 SourcePath string `json:"source_path"`
 Status string `json:"status"`
}
type edge struct{
 From string `json:"from"`
 To string `json:"to"`
 Relation string `json:"relation"`
}
type structure struct{
 Schema string `json:"schema"`
 Repository string `json:"repository"`
 Nodes []node `json:"nodes"`
 Edges []edge `json:"edges"`
 Governance map[string]any `json:"governance"`
}
type qualified struct{
 ID string `json:"id"`
 Commit string `json:"commit"`
 RunID int64 `json:"run_id"`
 State string `json:"state"`
 ScientificOriginal bool `json:"scientific_original"`
}
type evidence struct{
 Schema string `json:"schema"`
 Repository string `json:"repository"`
 Classification string `json:"classification"`
 Entries []qualified `json:"entries"`
 ResearchAuthority struct{
  Status string `json:"status"`
  ExternalCAS bool `json:"external_monotonic_first_use_CAS_proven"`
  KeyCustody bool `json:"independent_FSA_signer_custody_proven"`
  RawOriginals bool `json:"raw_originals_immutable_proven"`
  Generations int `json:"real_scientific_generations_run"`
 } `json:"research_authority"`
}
func root(t *testing.T)string{
 t.Helper()
 _,file,_,ok:=runtime.Caller(0);if !ok{t.Fatal("caller file missing")}
 return filepath.Clean(filepath.Join(filepath.Dir(file),".."))
}
func read(t *testing.T,p string,out any){
 t.Helper()
 raw,err:=os.ReadFile(filepath.Join(root(t),p));if err!=nil{t.Fatal(err)}
 if len(raw)==0||len(raw)>200000{t.Fatalf("invalid size %s",p)}
 if err=json.Unmarshal(raw,out);err!=nil{t.Fatalf("invalid JSON %s: %v",p,err)}
}
func hexSHA(s string,n int)bool{
 if len(s)!=n{return false}
 for _,c:=range s{if !(c>='0'&&c<='9'||c>='a'&&c<='f'){return false}}
 return true
}
func TestR17ICEAdvisorySourceAndNoAuthorityEscalation(t *testing.T){
 var m manifest;read(t,".ice/manifest.json",&m)
 if m.Schema!="forge.ice.manifest.v1"||m.Project!="FORGE"||
  m.Repository!="spoonman136668-ai/FORGE"||m.Visibility!="public-source-metadata-only"||
  m.Authority!="advisory-navigation-only"||
  m.SourceParentCommit!="982a654a3ed34719787aeb4a57bbe5e2f485c451"||
  m.SourceParentTree!="c06a7932d771479158701f4cd8d2d6f795adda15"||
  m.Graphify.Package!="graphifyy"||m.Graphify.Version!="0.9.53"||
  m.Graphify.Mode!="code-only"||m.Graphify.ModelCalls!=0||
  m.Graphify.BuildTool!="tools/Build-FORGE-Graphify.ps1"{
  t.Fatalf("manifest identity or code-only Graphify drift: %+v",m)
 }
 for _,name:=range []string{"raw_private_scientific_data_in_public_ice",
  "credentials_in_public_ice","mutable_scientific_authority_from_ice",
  "other_project_queue_authority","live_execution_from_ice",
  "generated_graphs_are_durable_proof"}{
  value,ok:=m.Safeguards[name];if !ok||value{t.Fatalf("unsafe ICE boundary: %s",name)}
 }
 expected:=map[string]string{
  "architecture":".ice/structure.json",
  "evidence":".ice/evidence-index.json",
  "graphify_graph":".ice/derived/graphify/graph.json",
  "obsidian_vault":".ice/derived/obsidian",
 }
 for k,want:=range expected{if m.Artifacts[k]!=want{t.Fatalf("artifact drift: %s %s",k,m.Artifacts[k])}}
}
func TestR17ArchitectureCompleteCrossLinkedAndPublic(t *testing.T){
 var s structure;read(t,".ice/structure.json",&s)
 if s.Schema!="forge.ice.structure.v1"||s.Repository!="spoonman136668-ai/FORGE"||
  len(s.Nodes)<25||len(s.Edges)<20{t.Fatal("incomplete project architecture graph")}
 all:=map[string]bool{}
 for _,n:=range s.Nodes{
  if n.ID==""||all[n.ID]||n.Kind==""||n.Status==""||
   n.SourcePath==""||filepath.IsAbs(n.SourcePath)||
   strings.HasPrefix(n.SourcePath,"..")||strings.Contains(n.SourcePath,"\\")||
   strings.Contains(n.SourcePath,":"){t.Fatalf("unsafe architecture node: %+v",n)}
  all[n.ID]=true
  stat,err:=os.Stat(filepath.Join(root(t),filepath.FromSlash(n.SourcePath)))
  if err!=nil||stat==nil{t.Fatalf("ungrounded architecture node: %s: %v",n.ID,err)}
 }
 edges:=map[string]bool{}
 for _,e:=range s.Edges{
  key:=e.From+":"+e.Relation+":"+e.To
  if !all[e.From]||!all[e.To]||e.Relation==""||edges[key]{
   t.Fatalf("invalid or duplicate edge: %+v",e)
  }
  edges[key]=true
 }
 for _,name:=range []string{"optimizer","first-use","eligibility","issuer","trust",
  "science-history","private-archive","context","Wingless","Yggdrasil"}{
  if !all[name]{t.Fatalf("FORGE general architecture node missing: %s",name)}
 }
 for _,flag:=range []string{"fsa_active","original_science_qualified",
  "graphify_generated_graph_authoritative","obsidian_notes_authoritative",
  "Mind_Palace_private_context_mirrored"}{
  if s.Governance[flag]!=false{t.Fatalf("authority uplift by graph: %s",flag)}
 }
}
func TestR17QualificationIndexPreservesNegativePhysicalGate(t *testing.T){
 var e evidence;read(t,".ice/evidence-index.json",&e)
 if e.Schema!="forge.ice.public-qualification-index.v1"||
  e.Repository!="spoonman136668-ai/FORGE"||
  e.Classification!="public_engineering_qualification_only"||
  len(e.Entries)!=5{
  t.Fatal("bad derived evidence index")
 }
 for _,item:=range e.Entries{
  if item.ID==""||item.RunID<=0||!hexSHA(item.Commit,40)||
   item.ScientificOriginal||!strings.HasPrefix(item.State,"source_qualified"){
   t.Fatalf("scientific original assertion in public .ice: %+v",item)
  }
 }
 if e.ResearchAuthority.Status!="not_deployed"||
  e.ResearchAuthority.ExternalCAS||e.ResearchAuthority.KeyCustody||
  e.ResearchAuthority.RawOriginals||e.ResearchAuthority.Generations!=0{
  t.Fatal("unqualified physical gate marked ready")
 }
}
