package ckbcustody

import (
 "encoding/json"
 "os"
 "path/filepath"
 "strings"
 "testing"
)

func TestReadS14WakeBindingFromExactPinnedFirstUse(t *testing.T){
 root,pins:=fixtures(t,true)
 binding,err:=ReadS14WakeBinding(root,pins)
 if err!=nil{t.Fatal(err)}
 if binding.WakeRunID!=38281455598||
  binding.WakeMainSHA!=strings.Repeat("a",40)||
  binding.ControllerSHA!=strings.Repeat("b",40)||
  binding.PermanentLedgerSHA256!=pins["S14"]{
  t.Fatal("incorrect original CKB wake identity",binding)
 }
}
func TestMissingOrChangedS14WakeBindingBlocks(t *testing.T){
 root,pins:=fixtures(t,false)
 if _,err:=ReadS14WakeBinding(root,pins);err==nil{t.Fatal("missing S14 first-use ledger accepted")}
 root,pins=fixtures(t,true)
 path:=filepath.Join(root,"s14-first-use-consumed.v1.json")
 data,err:=os.ReadFile(path);if err!=nil{t.Fatal(err)}
 var raw map[string]any
 if err=json.Unmarshal(data,&raw);err!=nil{t.Fatal(err)}
 raw["wake_run_id"]=0
 putLedger(t,root,"s14-first-use-consumed.v1.json",raw)
 if _,err=ReadS14WakeBinding(root,pins);err==nil{t.Fatal("changed wake ID accepted")}
 root,pins=fixtures(t,true)
 pins["S14"]=strings.Repeat("0",64)
 if _,err=ReadS14WakeBinding(root,pins);err==nil{t.Fatal("pin drift accepted")}
}
