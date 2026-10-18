package main
import(
 "bytes"
 "go/parser"
 "go/token"
 "testing"
)
func TestG29BlobIdentity(t *testing.T){
 raw:=[]byte("package a\n")
 h:=blobGitSHA(raw)
 b:=append([]byte{},raw...)
 if blobGitSHA(b)!=h{t.Fatal("identity mismatch")}
 if blobGitSHA(append(b,byte('!')))==h{t.Fatal("modified blob retained identity")}
}
func TestG29NativeGoAST(t *testing.T){
 raw:=[]byte("package atlas\ntype State struct{}\nfunc (s *State) Move() {}\n")
 if _,err:=parser.ParseFile(token.NewFileSet(),"sample.go",raw,0);err!=nil{t.Fatal(err)}
 sy,err:=parseGo("unit/sample.go","https://example.invalid/synthetic",raw)
 if err!=nil{t.Fatal(err)}
 if len(sy)!=2||sy[0].Name!="State"||sy[1].Name!="State.Move"{t.Fatalf("bad native Go locators %+v",sy)}
 if bytes.Contains([]byte(sy[1].Evidence),[]byte("reviewed")){t.Fatal("semantic review must not be asserted")}
}
func TestG29SafeRepositoryIdentity(t *testing.T){
 root,err:=rootPath();if err!=nil{t.Fatal(err)}
 h,err:=git(root,"rev-parse","HEAD");if err!=nil{t.Fatal(err)}
 a,err:=build(root,string(bytes.TrimSpace(h)));if err!=nil{t.Fatal(err)}
 if a.Repository!=repository||a.SourceReviewedLabels!=0||a.PrivateScientificDataIncluded||a.OtherRepoEvidenceImported{t.Fatal("FORGE authority drift")}
 if a.Counts.GoFiles<100||a.Counts.Symbols<100{t.Fatalf("atlas suspiciously incomplete %+v",a.Counts)}
}
