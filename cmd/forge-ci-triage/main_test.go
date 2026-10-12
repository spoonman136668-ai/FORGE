package main
import(
 "strings"
 "testing"
 "github.com/spoonman136668-ai/forge/repairregistry"
)
func TestCLIExactKnownFailureOnly(t *testing.T){
 dir:=t.TempDir()
 args:=[]string{"--registry",dir,"--repository","spoonman136668-ai/FORGE",
 "--run-id","38309699707","--sha",strings.Repeat("a",40),
 "--job","linux","--step","Public isolation",
 "--workflow","FORGE public Linux and Windows qualification"}
 r,err:=run(args)
 if err!=nil||r.Status!=repairregistry.AdvisoryOnly||len(r.Findings)!=0{t.Fatal(r,err)}
 args[9]="windows"
 if _,err:=run(args);err==nil{t.Fatal("wrong job accepted")}
 if _,err:=run([]string{"--registry",dir});err==nil{t.Fatal("missing provenance accepted")}
}
