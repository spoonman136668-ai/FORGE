package main

import (
 "bytes"
 "os"
 "path/filepath"
 "strings"
 "testing"
)
func TestNonAbsoluteRejected(t *testing.T) {
 if err:=verify("relative.json",&bytes.Buffer{});err==nil{t.Fatal("relative file accepted")}
}
func TestUntrustedSnapshotNeverAuthorizesMerge(t *testing.T) {
 file:=filepath.Join(t.TempDir(),"source.json")
 content:="{\"Repository\":\"spoonman136668-ai/FORGE\",\"PR\":{\"HeadSHA\":\"incomplete\"},\"Pages\":{}}"
 if err:=os.WriteFile(file,[]byte(content),0600);err!=nil{t.Fatal(err)}
 var out bytes.Buffer
 if err:=verify(file,&out);err!=nil{t.Fatal(err)}
 if !strings.Contains(out.String(),"\"MergeAuthorized\":false") ||
    !strings.Contains(out.String(),"\"SourceQualified\":false") {
  t.Fatal("unqualified snapshot elevated",out.String())
 }
}
func TestExtraJSONDenied(t *testing.T) {
 file:=filepath.Join(t.TempDir(),"source.json")
 if err:=os.WriteFile(file,[]byte("{} {}"),0600);err!=nil{t.Fatal(err)}
 if err:=verify(file,&bytes.Buffer{});err==nil{t.Fatal("multiple snapshots accepted")}
}
func TestSymlinkDenied(t *testing.T) {
 file:=filepath.Join(t.TempDir(),"real")
 if err:=os.WriteFile(file,[]byte("{}"),0600);err!=nil{t.Fatal(err)}
 alias:=filepath.Join(filepath.Dir(file),"link")
 if os.Symlink(file,alias)!=nil{t.Skip("symlink unavailable")}
 if err:=verify(alias,&bytes.Buffer{});err==nil{t.Fatal("symlink accepted")}
}
