package main

import (
 "bytes"
 "os"
 "path/filepath"
 "runtime"
 "strings"
 "testing"
)

func TestNoEvidenceNoReport(t *testing.T){
 var b bytes.Buffer
 err:=run(nil,&b)
 if err==nil||b.Len()!=0{t.Fatal("CLI emitted report without authenticated exported evidence")}
}
func TestCannotAliasTrustAndEvidence(t *testing.T){
 path:=filepath.Join(t.TempDir(),"evidence.json")
 var b bytes.Buffer
 args:=[]string{"--wingless-evidence",path,"--yggdrasil-evidence",path,
  "--signed-export",path,"--independent-anchor",path,"--independent-lane-pins",path,
  "--wingless-selection-audit",path,"--yggdrasil-selection-audit",path,
  "--independent-audit-pins",path}
 if err:=run(args,&b);err==nil||b.Len()!=0{t.Fatal("aliased independent inputs accepted")}
}
func TestRejectSymlinkEvidence(t *testing.T){
 if runtime.GOOS=="windows"{t.Skip("symlink permission varies on Windows")}
 d:=t.TempDir()
 original:=filepath.Join(d,"actual")
 alias:=filepath.Join(d,"alias")
 if err:=os.WriteFile(original,[]byte("{}"),0600);err!=nil{t.Fatal(err)}
 if err:=os.Symlink(original,alias);err!=nil{t.Fatal(err)}
 if _,err:=readRegularFile(alias,1024);err==nil{t.Fatal("symlink accepted")}
}
func TestRequireAbsoluteAndBoundedEvidence(t *testing.T){
 if _,err:=readRegularFile("relative",128);err==nil{t.Fatal("relative path accepted")}
 file:=filepath.Join(t.TempDir(),"x")
 if err:=os.WriteFile(file,[]byte(strings.Repeat("x",1025)),0600);err!=nil{t.Fatal(err)}
 if _,err:=readRegularFile(file,1024);err==nil{t.Fatal("oversize accepted")}
}
