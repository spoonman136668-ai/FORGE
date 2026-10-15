// Package mindgraph turns the existing read-only, source-pinned .ice context
// into a PRIVATE local provenance graph and Obsidian/Graphify input. It cannot
// ingest or write to Mind-Palace, and has no research authority.
package mindgraph

import (
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "fmt"
 "sort"
 "strings"

 "github.com/spoonman136668-ai/forge/mindcontext"
)

const Schema="forge.private-mind-derived-graph.v1"
const MaxNotes=24
var ErrBlocked=errors.New("FORGE_MIND_GRAPH_FAIL_CLOSED")
type Node struct{
 ID string `json:"id"`
 Kind string `json:"kind"`
 Label string `json:"label"`
 Project string `json:"project,omitempty"`
 RecordID string `json:"record_id,omitempty"`
 Statement string `json:"statement,omitempty"`
 SourceType string `json:"source_type,omitempty"`
 SourceRef string `json:"source_ref,omitempty"`
}
type Edge struct{
 From string `json:"from"`
 To string `json:"to"`
 Kind string `json:"kind"`
 EvidenceRecordID string `json:"evidence_record_id"`
 Origin string `json:"origin"`
}
type Graph struct{
 Schema string `json:"schema"`
 PinnedMindCommit string `json:"pinned_mind_commit"`
 RecordsSHA256 string `json:"records_sha256"`
 ContextSHA256 string `json:"context_sha256"`
 DerivedAdvisoryOnly bool `json:"derived_advisory_only"`
 NoInferredRelationships bool `json:"no_inferred_relationships"`
 Nodes []Node `json:"nodes"`
 Edges []Edge `json:"edges"`
}
type Manifest struct{
 Schema string `json:"schema"`
 PinnedMindCommit string `json:"pinned_mind_commit"`
 ContextSHA256 string `json:"context_sha256"`
 GraphSHA256 string `json:"graph_sha256"`
 FileSHA256 map[string]string `json:"file_sha256"`
 RecordCount int `json:"record_count"`
 SourceCount int `json:"source_count"`
 NonAuthoritative bool `json:"non_authoritative"`
}
type Bundle struct{
 Files map[string][]byte
 RecordCount int
 SourceCount int
}
func hash(s string)string{d:=sha256.Sum256([]byte(s));return hex.EncodeToString(d[:])}
func sum(b []byte)string{d:=sha256.Sum256(b);return hex.EncodeToString(d[:])}
func hexCheck(s string,n int)bool{
 if len(s)!=n{return false}
 for _,r:=range s{if !(r>='0'&&r<='9'||r>='a'&&r<='f'){return false}}
 return true
}
func projectOK(p string)bool{
 switch p{case "__global__","Wingless","Yggdrasil","Research":return true}
 return false
}
func escape(s string)string{
 // Never permit untrusted advisory prose to create Obsidian wikilinks,
 // Markdown directives, HTML, YAML frontmatter, or fenced code.
 r:=strings.NewReplacer("\r"," ","\n"," ","\x00"," ","\\","\\\\",
  "[","\\[","]","\\]","<","&lt;",">","&gt;",
  "`","'","#","\\#","|","\\|")
 s=r.Replace(s)
 return strings.TrimSpace(s)
}
func data(v any)([]byte,error){b,e:=json.MarshalIndent(v,"","  ");return append(b,'\n'),e}
func Build(context mindcontext.Result)(Bundle,error){
 var empty Bundle
 if context.Schema!="forge.mind-palace-context.v1"||!context.AdvisoryOnly||
    !hexCheck(context.PinnedCommit,40)||!hexCheck(context.RecordsSHA256,64)||
    !hexCheck(context.ContextSHA256,64)||len(context.Entries)==0||
    len(context.Entries)>MaxNotes{return empty,ErrBlocked}
 files:=map[string][]byte{}
 graph:=Graph{Schema:Schema,PinnedMindCommit:context.PinnedCommit,
  RecordsSHA256:context.RecordsSHA256,ContextSHA256:context.ContextSHA256,
  DerivedAdvisoryOnly:true,NoInferredRelationships:true}
 projects:=map[string]bool{}
 sources:=map[string]Node{}
 seen:=map[string]bool{}
 var index strings.Builder
 index.WriteString("# FORGE private research context\n\n")
 index.WriteString("Derived, advisory-only view of source-pinned Mind-Palace `.ice` records.\n")
 index.WriteString("**Not** an independent scientific authority or permission to dispatch experiments.\n\n")
 index.WriteString("Projects: [[projects/global|Global governance]], [[projects/Wingless|Wingless]], [[projects/Yggdrasil|Yggdrasil]], [[projects/Research|Research]].\n\n")
 for _,entry:=range context.Entries{
  if !projectOK(entry.Project)||len(entry.ID)<1||len(entry.ID)>180||
     len(entry.Kind)==0||len(entry.Kind)>50||
     len(entry.Statement)==0||len(entry.Statement)>mindcontext.MaxStatementBytes||
     len(entry.SourceRefs)==0||len(entry.SourceRefs)>12{return empty,ErrBlocked}
  if seen[entry.ID]||strings.TrimSpace(entry.ID)!=entry.ID{return empty,ErrBlocked}
  seen[entry.ID]=true
  for _,p:=range []string{entry.Project}{
   if !projects[p]{
    projects[p]=true
    graph.Nodes=append(graph.Nodes,Node{ID:"project:"+p,Kind:"project",Label:p,Project:p})
   }
  }
  rid:="record:"+hash(entry.Project+"\x00"+entry.ID)
  path:="obsidian/records/"+hash(entry.Project+"\x00"+entry.ID)+".md"
  projectNote:=entry.Project
  if projectNote=="__global__"{projectNote="global"}
  recordNote:="records/"+hash(entry.Project+"\x00"+entry.ID)
  graph.Nodes=append(graph.Nodes,Node{ID:rid,Kind:"record",Label:entry.ID,
   Project:entry.Project,RecordID:entry.ID,Statement:entry.Statement})
  graph.Edges=append(graph.Edges,Edge{From:rid,To:"project:"+entry.Project,
   Kind:"belongs_to",EvidenceRecordID:entry.ID,Origin:"EXTRACTED"})
  var note strings.Builder
  note.WriteString("# Advisory record "+escape(entry.ID)+"\n\n")
  note.WriteString("Project: [[projects/"+projectNote+"|"+escape(entry.Project)+"]]\n\n")
  note.WriteString("Kind: "+escape(entry.Kind)+"\n\n")
  note.WriteString("Statement (untrusted source content):\n\n> "+escape(entry.Statement)+"\n\n")
  note.WriteString("Original source references (not scientific endorsements):\n\n")
  for _,src:=range entry.SourceRefs{
   if len(src.Type)<1||len(src.Type)>36||len(src.Ref)<1||len(src.Ref)>512||
      strings.ContainsAny(src.Type+src.Ref,"\r\n\x00"){return empty,ErrBlocked}
   sid:="source:"+hash(src.Type+"\x00"+src.Ref)
   if _,ok:=sources[sid];!ok{
    sources[sid]=Node{ID:sid,Kind:"source",Label:src.Type,
      SourceType:src.Type,SourceRef:src.Ref}
   }
   graph.Edges=append(graph.Edges,Edge{From:rid,To:sid,
     Kind:"cites_source",EvidenceRecordID:entry.ID,Origin:"EXTRACTED"})
   key:=hash(src.Type+"\x00"+src.Ref)
   note.WriteString("- [[sources/"+key+"|source "+key[:12]+"]]: "+escape(src.Type)+" "+escape(src.Ref)+"\n")
  }
  files[path]=[]byte(note.String())
  // The Graphify stage is explicit and private. These are source notes, not
  // Graphify's own graph.json schema; the actual graphify CLI is optional.
  files["graphify-input/records/"+hash(entry.Project+"\x00"+entry.ID)+".md"]=[]byte(note.String())
  index.WriteString("- [["+recordNote+"|"+escape(entry.ID)+"]] ("+escape(entry.Project)+")\n")
 }
 order:=[]string{"__global__","Wingless","Yggdrasil","Research"}
 for _,p:=range order{
  if !projects[p]{continue}
  label:=p
  if label=="__global__"{label="global"}
  var body strings.Builder
  body.WriteString("# "+escape(p)+"\n\n")
  body.WriteString("Private advisory source-pinned research context, not instructions.\n\n")
  for _,entry:=range context.Entries{
   if entry.Project==p{
    body.WriteString("- [[records/"+hash(entry.Project+"\x00"+entry.ID)+"|"+escape(entry.ID)+"]]\n")
   }
  }
  files["obsidian/projects/"+label+".md"]=[]byte(body.String())
 }
 keys:=make([]string,0,len(sources))
 for k:=range sources{keys=append(keys,k)}
 sort.Strings(keys)
 for _,id:=range keys{
  node:=sources[id]
  key:=strings.TrimPrefix(id,"source:")
  files["obsidian/sources/"+key+".md"]=[]byte("# Provenance source\n\nType: "+escape(node.SourceType)+"\n\nReference: "+escape(node.SourceRef)+"\n\nSource reference only; validate original bytes before scientific use.\n")
  graph.Nodes=append(graph.Nodes,node)
 }
 sort.Slice(graph.Nodes,func(i,j int)bool{return graph.Nodes[i].ID<graph.Nodes[j].ID})
 sort.Slice(graph.Edges,func(i,j int)bool{
  a,b:=graph.Edges[i],graph.Edges[j]
  return a.From+"|"+a.To+"|"+a.Kind<b.From+"|"+b.To+"|"+b.Kind
 })
 files["obsidian/Index.md"]=[]byte(index.String())
 files["graphify-input/README.md"]=[]byte("# Private FORGE advisory evidence corpus\n\nThis folder is a bounded export of provenance-bearing `.ice` research notes. No inferred or accepted scientific relations. If running the third-party Graphify semantic analyzer, use a PRIVATE LOCAL backend; do not send private notes to a paid or remote model.\n")
 b,err:=data(graph);if err!=nil{return empty,err}
 files[".ice/derived-context-graph.json"]=b
 checks:=map[string]string{}
 for path,content:=range files{checks[path]=sum(content)}
 man:=Manifest{Schema:"forge.private-mind-derived-export.v1",
  PinnedMindCommit:context.PinnedCommit,ContextSHA256:context.ContextSHA256,
  GraphSHA256:sum(b),FileSHA256:checks,RecordCount:len(context.Entries),
  SourceCount:len(sources),NonAuthoritative:true}
 bm,err:=data(man);if err!=nil{return empty,err}
 files[".ice/derived-export-manifest.json"]=bm
 if len(files)>14*MaxNotes+15{return empty,fmt.Errorf("%w: too many files",ErrBlocked)}
 return Bundle{Files:files,RecordCount:len(context.Entries),SourceCount:len(sources)},nil
}
