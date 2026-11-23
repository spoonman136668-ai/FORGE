// FORGE G29 public code navigation, isolated from runtime and scientific authority.
package main

import (
 "bytes"
 "crypto/sha1"
 "crypto/sha256"
 "encoding/base64"
 "encoding/hex"
 "encoding/json"
 "errors"
 "flag"
 "fmt"
 "go/ast"
 "go/parser"
 "go/token"
 "os"
 "os/exec"
 "path/filepath"
 "regexp"
 "sort"
 "strings"
)

const repository = "spoonman136668-ai/FORGE"
const schema = "forge.ice.public-source-atlas.v1"
const jsonFile = ".ice/public-code-atlas.json"
const htmlFile = ".ice/public-code-atlas.html"
const iceFile = ".ice/public-code-atlas.ice"

type File struct {
 Path string `json:"path"`
 SHA256 string `json:"sha256"`
 Kind string `json:"kind"`
 URL string `json:"source_url"`
}
type Symbol struct {
 ID string `json:"id"`
 File string `json:"file"`
 Name string `json:"name"`
 Kind string `json:"kind"`
 Start int `json:"start_line"`
 End int `json:"end_line"`
 Evidence string `json:"evidence_basis"`
 URL string `json:"source_url"`
}
type Counts struct {
 Files int `json:"files"`
 Symbols int `json:"symbols"`
 GoFiles int `json:"go_files"`
}
type Atlas struct {
 Schema string `json:"schema"`
 Repository string `json:"repository"`
 SourceCommit string `json:"source_commit"`
 Authority string `json:"authority"`
 SourceReviewedLabels int `json:"source_reviewed_labels"`
 OtherRepoEvidenceImported bool `json:"other_repo_evidence_imported"`
 PrivateScientificDataIncluded bool `json:"private_scientific_data_included"`
 Counts Counts `json:"counts"`
 Files []File `json:"files"`
 Symbols []Symbol `json:"symbols"`
}

func git(root string,args ...string)([]byte,error){
 c:=exec.Command("git",args...);c.Dir=root
 out,err:=c.CombinedOutput()
 if err!=nil{return nil,fmt.Errorf("git %q: %w: %s",args,err,string(out))}
 return out,nil
}
func rootPath()(string,error){
 out,err:=git(".","rev-parse","--show-toplevel");if err!=nil{return "",err}
 return strings.TrimSpace(string(out)),nil
}
func tree(root,commit string)(map[string]string,error){
 out,err:=git(root,"ls-tree","-r","-z",commit);if err!=nil{return nil,err}
 result:=map[string]string{}
 for _,record:=range bytes.Split(out,[]byte{0}){
  if len(record)==0{continue}
  p:=bytes.SplitN(record,[]byte{'	'},2);if len(p)!=2{return nil,errors.New("invalid git tree record")}
  meta:=strings.Fields(string(p[0]));if len(meta)!=3||meta[1]!="blob"{continue}
  path:=string(p[1])
  if path==jsonFile||path==htmlFile||path==iceFile{continue}
  if !strings.HasSuffix(path,".go")&&!strings.HasSuffix(path,".py")&&
     !strings.HasSuffix(path,".ps1")&&!strings.HasSuffix(path,".yml")&&
     !strings.HasSuffix(path,".yaml")&&!strings.HasSuffix(path,".md")&&
     !strings.HasSuffix(path,".json"){continue}
  result[path]=meta[2]
 }
 return result,nil
}
func blobGitSHA(raw []byte)string{
 sum:=sha1.Sum(append([]byte(fmt.Sprintf("blob %d\x00",len(raw))),raw...))
 return hex.EncodeToString(sum[:])
}
func pinnedFile(root,path,wantSHA string)([]byte,error){
 if filepath.IsAbs(path)||strings.Contains(path,"..")||strings.Contains(path,"\\"){return nil,errors.New("unsafe source path")}
 raw,err:=os.ReadFile(filepath.Join(root,filepath.FromSlash(path)));if err!=nil{return nil,err}
 if blobGitSHA(raw)==wantSHA{return raw,nil}
 lf:=bytes.ReplaceAll(raw,[]byte("\r\n"),[]byte("\n"))
 if blobGitSHA(lf)==wantSHA{return lf,nil}
 return nil,fmt.Errorf("FORGE_ATLAS_BLOB_IDENTITY_DRIFT %s",path)
}
func symbol(path,kind,name,evidence,url string,start,end int)Symbol{
 return Symbol{ID:"forge:"+path+"::"+kind+"::"+name+"@"+fmt.Sprint(start),
  File:path,Name:name,Kind:kind,Start:start,End:end,Evidence:evidence,
  URL:fmt.Sprintf("%s#L%d-L%d",url,start,end)}
}
var pyDecl=regexp.MustCompile(`(?m)^\s*(?:async\s+)?(def|class)\s+([A-Za-z_][A-Za-z_0-9]*)`)
var psDecl=regexp.MustCompile(`(?im)^\s*function\s+([A-Za-z_][A-Za-z_0-9-]*)`)
var workflowName=regexp.MustCompile(`(?m)^name:\s*(.+)$`)
func parseGo(path,url string,raw []byte)([]Symbol,error){
 fset:=token.NewFileSet()
 node,err:=parser.ParseFile(fset,path,raw,0)
 if err!=nil{return nil,fmt.Errorf("FORGE_GO_AST_INVALID %s: %w",path,err)}
 out:=[]Symbol{}
 for _,decl:=range node.Decls{
  switch d:=decl.(type){
  case *ast.FuncDecl:
   name:=d.Name.Name
   if d.Recv!=nil&&len(d.Recv.List)>0{
    switch recv:=d.Recv.List[0].Type.(type){
    case *ast.Ident:name=recv.Name+"."+name
    case *ast.StarExpr:if typ,ok:=recv.X.(*ast.Ident);ok{name=typ.Name+"."+name}
    }
   }
   st,en:=fset.Position(d.Pos()).Line,fset.Position(d.End()).Line
   out=append(out,symbol(path,"go-function",name,"go-ast-locator-only",url,st,en))
  case *ast.GenDecl:
   for _,sp:=range d.Specs{if ts,ok:=sp.(*ast.TypeSpec);ok{
    st,en:=fset.Position(ts.Pos()).Line,fset.Position(ts.End()).Line
    out=append(out,symbol(path,"go-type",ts.Name.Name,"go-ast-locator-only",url,st,en))
   }}
  }
 }
 return out,nil
}
func build(root,source string)(Atlas,error){
 zero:=Atlas{}
 if !regexp.MustCompile("^[0-9a-f]{40}$").MatchString(source){return zero,errors.New("not exact source SHA")}
 head,err:=git(root,"rev-parse","HEAD");if err!=nil{return zero,err}
 current:=strings.TrimSpace(string(head))
 if _,err=git(root,"merge-base","--is-ancestor",source,current);err!=nil{return zero,errors.New("source commit not ancestor")}
 before,err:=tree(root,source);if err!=nil{return zero,err}
 now,err:=tree(root,current);if err!=nil{return zero,err}
 if len(before)!=len(now){return zero,errors.New("FORGE_ATLAS_SOURCE_SET_DRIFT")}
 paths:=make([]string,0,len(before))
 for path,sha:=range before{if now[path]!=sha{return zero,fmt.Errorf("FORGE_ATLAS_HEAD_SOURCE_DRIFT %s",path)};paths=append(paths,path)}
 sort.Strings(paths)
 a:=Atlas{Schema:schema,Repository:repository,SourceCommit:source,
  Authority:"public-source-navigation-only",SourceReviewedLabels:0,
  OtherRepoEvidenceImported:false,PrivateScientificDataIncluded:false,
  Files:[]File{},Symbols:[]Symbol{}}
 for _,path:=range paths{
  raw,err:=pinnedFile(root,path,before[path]);if err!=nil{return zero,err}
  sum:=sha256.Sum256(raw)
  ext:=filepath.Ext(path);kind:="document-or-config"
  if ext==".go"{kind="go"}else if ext==".py"{kind="python"}else if ext==".ps1"{kind="powershell"}else if strings.HasPrefix(path,".github/workflows/"){kind="workflow"}
  url:="https://github.com/"+repository+"/blob/"+source+"/"+path
  a.Files=append(a.Files,File{Path:path,SHA256:hex.EncodeToString(sum[:]),Kind:kind,URL:url})
  switch kind{
  case "go":
   a.Counts.GoFiles++
   xs,e:=parseGo(path,url,raw);if e!=nil{return zero,e};a.Symbols=append(a.Symbols,xs...)
  case "python":
   for _,loc:=range pyDecl.FindAllSubmatchIndex(raw,-1){
    name:=string(raw[loc[4]:loc[5]]);typ:=string(raw[loc[2]:loc[3]])
    line:=bytes.Count(raw[:loc[0]],[]byte{'\n'})+1
    a.Symbols=append(a.Symbols,symbol(path,"python-"+typ,name,"lexical-locator-only",url,line,line))
   }
  case "powershell":
   for _,loc:=range psDecl.FindAllSubmatchIndex(raw,-1){
    name:=string(raw[loc[2]:loc[3]])
    line:=bytes.Count(raw[:loc[0]],[]byte{'\n'})+1
    a.Symbols=append(a.Symbols,symbol(path,"powershell-function",name,"lexical-locator-only",url,line,line))
   }
  case "workflow":
   if loc:=workflowName.FindSubmatchIndex(raw);len(loc)>=4{
    name:=strings.TrimSpace(string(raw[loc[2]:loc[3]]))
    line:=bytes.Count(raw[:loc[0]],[]byte{'\n'})+1
    a.Symbols=append(a.Symbols,symbol(path,"workflow",name,"lexical-locator-only",url,line,line))
   }
  }
 }
 sort.Slice(a.Symbols,func(i,j int)bool{
  x,y:=a.Symbols[i],a.Symbols[j]
  if x.File!=y.File{return x.File<y.File}
  if x.Start!=y.Start{return x.Start<y.Start}
  return x.ID<y.ID
 })
 a.Counts.Files=len(a.Files);a.Counts.Symbols=len(a.Symbols)
 return a,nil
}
func render(a Atlas)(map[string][]byte,error){
 raw,err:=json.MarshalIndent(a,"","  ");if err!=nil{return nil,err}
 jsonContent:=append(raw,'\n')
 packed,err:=json.Marshal(a);if err!=nil{return nil,err}
 embedded:=strings.ReplaceAll(strings.ReplaceAll(string(packed),"<","\\u003c"),">","\\u003e")
 html:=`<!doctype html><html lang="en"><head><meta charset="utf-8"><title>FORGE public code atlas</title><meta name="viewport" content="width=device-width,initial-scale=1"><style>body{font:15px system-ui;background:#101b26;color:#edf4fa;margin:0;padding:24px}main{max-width:1200px;margin:auto;display:grid;grid-template-columns:40% 60%;gap:16px}section{background:#1e3042;padding:15px;border:1px solid #4d6378}button{display:block;width:100%;text-align:left;background:#30465d;color:white;border:1px solid #516980;padding:6px}input{font:inherit;padding:9px;width:90%}a{color:#99e5f5}@media(max-width:700px){main{display:block}}</style></head><body><main><section><h1>FORGE source atlas</h1><p>Public source syntax locators only; not scientific authority, not human-reviewed interpretation.</p><p id="counts"></p><input id="q" aria-label="Search source files and symbols"><div id="matches"></div></section><section><h2>Source</h2><div id="detail"></div></section></main><script id="atlas" type="application/json">`+embedded+`</script><script>(()=>{const a=JSON.parse(document.getElementById("atlas").textContent),q=document.getElementById("q"),list=document.getElementById("matches"),d=document.getElementById("detail");document.getElementById("counts").textContent=a.counts.files+" files / "+a.counts.symbols+" provisional symbols";const it=[...a.files.map(x=>({name:x.path,o:x})),...a.symbols.map(x=>({name:x.name+" | "+x.file,o:x}))];function add(t,s,p){const n=document.createElement(t);n.textContent=s;p.append(n);return n}function show(x){d.replaceChildren();add("h3",x.name,d);add("p",x.o.evidence_basis||"verified Git source file",d);let a=add("a","Open pinned source",d);a.href=x.o.source_url;a.target="_blank";a.rel="noopener noreferrer"}function draw(){list.replaceChildren();for(const x of it.filter(z=>z.name.toLowerCase().includes(q.value.toLowerCase())).slice(0,200)){const b=add("button",x.name,list);b.onclick=()=>show(x)}}q.oninput=draw;draw();})();</script></body></html>`
 ice:=fmt.Sprintf(`TITLE: FORGE Public Source Atlas
STATUS: ADVISORY CODE LOCATORS ONLY
REPOSITORY: %s
SOURCE_COMMIT: %s
FILES: %d
GO_FILES: %d
SYMBOLS: %d
SOURCE_REVIEWED_LABELS: 0
OTHER_PROJECT_REVIEW_IMPORTS: FALSE
PRIVATE_SCIENTIFIC_DATA_INCLUDED: FALSE
FSA_AUTHORITY: NONE
CKB_PLANE_LINKAGE: NONE
EXISTING_FORGE_ICE_EVIDENCE_MODIFIED: FALSE
`,repository,a.SourceCommit,a.Counts.Files,a.Counts.GoFiles,a.Counts.Symbols)
 return map[string][]byte{jsonFile:jsonContent,htmlFile:[]byte(html),iceFile:[]byte(ice)},nil
}
func main(){
 source:=flag.String("source-commit","","full source commit")
 check:=flag.Bool("check",false,"verify generated atlas blobs")
 pending:=flag.Bool("check-if-present",false,"validate when artifacts are present")
 write:=flag.Bool("write",false,"write derived artifacts locally")
 emit:=flag.Bool("emit-base64",false,"emit chunked exact-head artifacts")
 g61:=flag.Bool("g61",false,"qualify exact G60 source delta without touching G29 snapshot")
 g61Out:=flag.String("g61-out","","optional isolated directory for G61 derived navigation")
 flag.Parse()
 root,err:=rootPath();fail:=func(e error){fmt.Fprintln(os.Stderr,e);os.Exit(1)}
 if err!=nil{fail(err)}
 if *g61{if e:=g61Run(root,*g61Out);e!=nil{fail(e)};return}
 src:=*source
 if src==""{b,e:=os.ReadFile(filepath.Join(root,jsonFile));if e==nil{var v struct{SourceCommit string `json:"source_commit"`};if e=json.Unmarshal(b,&v);e!=nil{fail(e)};src=v.SourceCommit}else{h,e:=git(root,"rev-parse","HEAD");if e!=nil{fail(e)};src=strings.TrimSpace(string(h))}}
 a,err:=build(root,src);if err!=nil{fail(err)}
 data,err:=render(a);if err!=nil{fail(err)}
 present:=0
 for k:=range data{if _,e:=os.Stat(filepath.Join(root,k));e==nil{present++}}
 if *check||(*pending&&present>0){
  if present!=len(data){fail(errors.New("partial FORGE public atlas artifacts"))}
  for path,want:=range data{
   committed,e:=git(root,"show","HEAD:"+path);if e!=nil{fail(e)}
   if !bytes.Equal(committed,want){fail(fmt.Errorf("FORGE_ATLAS_STALE_GIT_BLOB %s",path))}
  }
  fmt.Println("FORGE_G29_PUBLIC_ATLAS_SNAPSHOT_PASS")
 }else if *pending{fmt.Println("FORGE_G29_SNAPSHOT_PENDING_FIRST_COMMIT")}
 if *write{for path,content:=range data{dest:=filepath.Join(root,path);if err=os.MkdirAll(filepath.Dir(dest),0755);err!=nil{fail(err)};if err=os.WriteFile(dest,content,0644);err!=nil{fail(err)}}}
 if *emit{
  payload:=map[string]string{}
  for k,v:=range data{payload[k]=string(v)}
  b,e:=json.Marshal(payload);if e!=nil{fail(e)}
  encoded:=base64.StdEncoding.EncodeToString(b)
  size:=3600;total:=(len(encoded)+size-1)/size
  for i:=0;i<total;i++{end:=(i+1)*size;if end>len(encoded){end=len(encoded)}
   fmt.Printf("FORGE_G29_B64_CHUNK_%04d_OF_%04d:%s\n",i+1,total,encoded[i*size:end])}
 }
 fmt.Printf("FORGE_G29_PUBLIC_SOURCE_INDEX_PASS commit=%s files=%d go=%d symbols=%d\n",src,a.Counts.Files,a.Counts.GoFiles,a.Counts.Symbols)
}
