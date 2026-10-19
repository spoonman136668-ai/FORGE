package main

// G61: immutable, read-only FORGE source atlas delta. All relationships remain
// provisional locators; neither FSA nor controller authority is touched.
import (
 "bytes"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "fmt"
 "os"
 "path/filepath"
 "regexp"
 "sort"
 "strings"
)
const (
 g61Base = "c6f5823ee48c1df81d6d197b7cff3090b392c4cb"
 g61Target = "07b585dde1e9ea88bf4d768b46412ee77673b140"
 g61BaselineBlob = "0030963a413ff9905138fc9bb25d169199658166"
)
type g61Stats struct {
 Baseline string `json:"baseline_source"`
 BaselineBlob string `json:"baseline_atlas_blob"`
 Target string `json:"target_source"`
 Reused int `json:"exact_blob_reused"`
 Modified int `json:"modified_files"`
 Added int `json:"added_files"`
 CSharp int `json:"csharp_files"`
 DeltaPaths []string `json:"delta_paths"`
}
var csharpDecl=regexp.MustCompile(`(?m)^\s*(?:(?:public|private|protected|internal|static|sealed|abstract|partial)\s+)*(class|struct|interface|record)\s+([A-Za-z_][A-Za-z_0-9]*)\b`)
func g61Eligible(p string)bool{
 if p==jsonFile||p==htmlFile||p==iceFile{return false}
 switch filepath.Ext(p){case ".go",".py",".ps1",".yml",".yaml",".md",".json",".cs":return true}
 return false
}
func g61Tree(root,rev string)(map[string]string,error){
 raw,e:=git(root,"ls-tree","-r","-z",rev);if e!=nil{return nil,e}
 out:=map[string]string{}
 for _,line:=range bytes.Split(raw,[]byte{0}){
  if len(line)==0{continue}
  parts:=bytes.SplitN(line,[]byte{9},2)
  if len(parts)!=2{return nil,errors.New("G61_BAD_TREE_RECORD")}
  meta:=strings.Fields(string(parts[0]));if len(meta)!=3{return nil,errors.New("G61_BAD_TREE_METADATA")}
  if meta[1]!="blob"{continue}
  p:=string(parts[1]);if !g61Eligible(p){continue}
  if out[p]!=""{return nil,errors.New("G61_DUPLICATE_PATH")}
  out[p]=meta[2]
 }
 return out,nil
}
func g61Source(root,rev,path,sha string)([]byte,error){
 if filepath.IsAbs(path)||strings.Contains(path,"..")||strings.ContainsRune(path,92){return nil,errors.New("G61_UNSAFE_PATH")}
 raw,e:=git(root,"show",rev+":"+path);if e!=nil{return nil,e}
 if blobGitSHA(raw)!=sha{return nil,fmt.Errorf("G61_SOURCE_BLOB_DRIFT %s",path)}
 return raw,nil
}
func g61Extract(path,url string,raw []byte)([]Symbol,error){
 ext:=filepath.Ext(path)
 if ext==".go"{return parseGo(path,url,raw)}
 out:=[]Symbol{}
 appendLocators:=func(re *regexp.Regexp,kind string,nameGroup int){
  for _,m:=range re.FindAllSubmatchIndex(raw,-1){
   start,end:=m[nameGroup*2],m[nameGroup*2+1]
   if start<0||end<0{continue}
   line:=bytes.Count(raw[:m[0]],[]byte{10})+1
   out=append(out,symbol(path,kind,string(raw[start:end]),"lexical-locator-only",url,line,line))
  }
 }
 switch ext {
 case ".py":
  appendLocators(pyDecl,"python-declaration",2)
 case ".ps1":
  appendLocators(psDecl,"powershell-function",1)
 case ".cs":
  appendLocators(csharpDecl,"csharp-declaration",2)
 case ".yaml",".yml":
  if strings.HasPrefix(path,".github/workflows/"){appendLocators(workflowName,"workflow",1)}
 }
 return out,nil
}
func g61Build(root string)(Atlas,g61Stats,error){
 empty:=Atlas{}
 stats:=g61Stats{Baseline:g61Base,BaselineBlob:g61BaselineBlob,Target:g61Target,DeltaPaths:[]string{}}
 head,e:=git(root,"rev-parse","HEAD");if e!=nil{return empty,stats,e}
 current:=strings.TrimSpace(string(head))
 if _,e=git(root,"merge-base","--is-ancestor",g61Target,current);e!=nil{return empty,stats,errors.New("G61_TARGET_NOT_ANCESTOR")}
 dirty,e:=git(root,"status","--porcelain");if e!=nil{return empty,stats,e}
 if len(bytes.TrimSpace(dirty))!=0{return empty,stats,errors.New("G61_DIRTY_CHECKOUT")}
 diff,e:=git(root,"diff","--name-only",g61Target,current);if e!=nil{return empty,stats,e}
 allowed:=map[string]bool{
  "cmd/forge-code-atlas/main.go":true,
  "cmd/forge-code-atlas/g61.go":true,
  "cmd/forge-code-atlas/g61_test.go":true,
  ".github/workflows/forge-g29-source-atlas.yml":true,
  "docs/G61-SOURCE-COVERAGE.md":true,
  "cmd/forge-code-atlas/g62.go":true,
  "cmd/forge-code-atlas/g62_test.go":true,
  "scripts/test_g62_navigator.js":true,
  "docs/G62-NAVIGATION-CLOSURE.md":true,
 }
 for _,p:=range strings.Split(strings.TrimSpace(string(diff)),string([]byte{10})){
  if p!=""&&!allowed[p]{return empty,stats,fmt.Errorf("G61_UNAUTHORIZED_HEAD_DELTA %s",p)}
 }
 blob,e:=git(root,"rev-parse",current+":"+jsonFile);if e!=nil{return empty,stats,e}
 if strings.TrimSpace(string(blob))!=g61BaselineBlob{return empty,stats,errors.New("G61_BASELINE_ARTIFACT_DRIFT")}
 b,e:=git(root,"show",current+":"+jsonFile);if e!=nil{return empty,stats,e}
 var base Atlas
 if e=json.Unmarshal(b,&base);e!=nil{return empty,stats,e}
 if base.Schema!=schema||base.Repository!=repository||base.SourceCommit!=g61Base||
  base.Counts.Files!=763||base.Counts.Symbols!=3386||base.SourceReviewedLabels!=0||
  base.PrivateScientificDataIncluded||base.OtherRepoEvidenceImported{
  return empty,stats,errors.New("G61_UNQUALIFIED_BASELINE")
 }
 old,e:=g61Tree(root,g61Base);if e!=nil{return empty,stats,e}
 target,e:=g61Tree(root,g61Target);if e!=nil{return empty,stats,e}
 if len(old)!=len(base.Files){return empty,stats,errors.New("G61_BASELINE_SET_DRIFT")}
 files:=map[string]File{}
 for _,f:=range base.Files{
  if old[f.Path]==""||files[f.Path].Path!=""||
   !strings.HasPrefix(f.URL,"https://github.com/"+repository+"/blob/"+g61Base+"/"+f.Path){
   return empty,stats,fmt.Errorf("G61_BASELINE_SOURCE_INVALID %s",f.Path)
  }
  files[f.Path]=f
 }
 groups:=map[string][]Symbol{}
 for _,s:=range base.Symbols{
  if files[s.File].Path==""||s.Start<1||s.End<s.Start{
   return empty,stats,errors.New("G61_BASELINE_SYMBOL_INVALID")
  }
  groups[s.File]=append(groups[s.File],s)
 }
 for p:=range old{if target[p]==""{return empty,stats,fmt.Errorf("G61_DELETION_REQUIRES_NEW_GATE %s",p)}}
 paths:=make([]string,0,len(target));for p:=range target{paths=append(paths,p)};sort.Strings(paths)
 a:=Atlas{Schema:schema,Repository:repository,SourceCommit:g61Target,
  Authority:"public-source-navigation-only",Files:[]File{},Symbols:[]Symbol{}}
 for _,p:=range paths{
  if old[p]!=""&&old[p]==target[p]{
   a.Files=append(a.Files,files[p])
   a.Symbols=append(a.Symbols,groups[p]...)
   stats.Reused++
  }else{
   raw,err:=g61Source(root,g61Target,p,target[p]);if err!=nil{return empty,stats,err}
   sum:=sha256.Sum256(raw)
   kind:="document-or-config"
   switch filepath.Ext(p){case ".go":kind="go";case ".py":kind="python";case ".ps1":kind="powershell";case ".cs":kind="csharp"}
   if strings.HasPrefix(p,".github/workflows/"){kind="workflow"}
   url:="https://github.com/"+repository+"/blob/"+g61Target+"/"+p
   a.Files=append(a.Files,File{Path:p,SHA256:hex.EncodeToString(sum[:]),Kind:kind,URL:url})
   sy,err:=g61Extract(p,url,raw);if err!=nil{return empty,stats,err}
   a.Symbols=append(a.Symbols,sy...)
   if old[p]!=""{stats.Modified++}else{stats.Added++}
   if filepath.Ext(p)==".cs"{stats.CSharp++}
   stats.DeltaPaths=append(stats.DeltaPaths,p)
  }
  if filepath.Ext(p)==".go"{a.Counts.GoFiles++}
 }
 if stats.Reused!=747||stats.Modified!=16||stats.Added!=20||stats.CSharp!=1||len(stats.DeltaPaths)!=36{
  return empty,stats,fmt.Errorf("G61_SCOPE_DRIFT reused=%d modified=%d added=%d cs=%d",
   stats.Reused,stats.Modified,stats.Added,stats.CSharp)
 }
 sort.Slice(a.Symbols,func(i,j int)bool{
  x,y:=a.Symbols[i],a.Symbols[j]
  if x.File!=y.File{return x.File<y.File};if x.Start!=y.Start{return x.Start<y.Start}
  return x.ID<y.ID
 })
 a.Counts.Files=len(a.Files);a.Counts.Symbols=len(a.Symbols)
 if a.Counts.Files!=783{return empty,stats,errors.New("G61_BAD_UNION_COUNT")}
 return a,stats,nil
}
func g61Run(root,out string)error{
 a,s,e:=g61Build(root);if e!=nil{return e}
 if out!=""{
  if e=os.MkdirAll(out,0700);e!=nil{return e}
  rendered,e:=renderG62(a);if e!=nil{return e}
  names:=map[string]string{jsonFile:"G61_SOURCE_ATLAS.json",htmlFile:"G61_SOURCE_ATLAS.html",iceFile:"G61_SOURCE_ATLAS.ice"}
  for src,data:=range rendered{
   if e=os.WriteFile(filepath.Join(out,names[src]),data,0600);e!=nil{return e}
  }
  evidence,e:=json.MarshalIndent(s,"","  ");if e!=nil{return e}
  if e=os.WriteFile(filepath.Join(out,"G61_DELTA_PROVENANCE.json"),append(evidence,byte(10)),0600);e!=nil{return e}
 }
 fmt.Printf("FORGE_G61_EXACT_SOURCE_PASS target=%s reused=%d modified=%d added=%d csharp=%d files=%d symbols=%d\n",
  s.Target,s.Reused,s.Modified,s.Added,s.CSharp,a.Counts.Files,a.Counts.Symbols)
 return nil
}
