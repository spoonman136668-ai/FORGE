package main

import (
 "os"
 "path/filepath"
 "testing"
)
func TestRejectUnpinnedOrMissingHistory(t *testing.T){
 if err:=execute("","","","","","","","","");err==nil{
  t.Fatal("untrusted unconfigured research accepted")
 }
 path:=filepath.Join(t.TempDir(),"bad.json")
 if err:=os.WriteFile(path,[]byte("{}{}"),0600);err!=nil{t.Fatal(err)}
 var out map[string]any
 if err:=readJSON(path,&out);err==nil{t.Fatal("concatenated JSON accepted")}
}
func TestOutputExclusiveAndReadOnly(t *testing.T){
 path:=filepath.Join(t.TempDir(),"result.json")
 if err:=writeJSONOnce(path,map[string]any{"dispatch_authorized":false});err!=nil{t.Fatal(err)}
 if err:=writeJSONOnce(path,map[string]any{"dispatch_authorized":true});err==nil{
  t.Fatal("second write overwrote immutable result")
 }
}
