package main
import (
 "testing"
 "github.com/spoonman136668-ai/forge/repairregistry"
)
func TestCLIRejectsMissingRegistryAndInference(t *testing.T){
 if _,err:=run([]string{});err==nil{t.Fatal("missing registry accepted")}
 if _,err:=run([]string{"--registry",t.TempDir(),"--repository","repo","--component","ci",
 "--signature","failed","--scope","exact","--preconditions","one"});err!=nil&&err!=repairregistry.ErrBlocked{t.Fatal(err)}
}
