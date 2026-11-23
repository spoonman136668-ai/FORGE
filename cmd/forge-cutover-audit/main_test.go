package main

import (
 "bytes"
 "crypto/ed25519"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "os"
 "path/filepath"
 "strings"
 "testing"
)
func testBundle(t *testing.T)bundle{
 t.Helper()
 h:=sha256.Sum256([]byte("TEST ONLY cutover bundle key"))
 pk:=hex.EncodeToString(ed25519.NewKeyFromSeed(h[:]).Public().(ed25519.PublicKey))
 return bundle{
  Schema:schema,
  LegacyStateDirectory:filepath.Join(t.TempDir(),"old_state"),
  LegacySHA256Pins:map[string]string{"S09":strings.Repeat("a",64)},
  LegacyPlan:oldPlan{TrustedCollectorPublicKeyHex:pk},
  FSAAnchor:anchorWire{PublicKeyHex:pk},
  FSAPin:pinWire{PublicKeyHex:pk,WitnessPublicKeyHex:pk},
  ForgeOriginalGrantPublicKeyHex:pk,
 }
}
func TestCanonicalBundleNoAuthorityOnIncompleteCustody(t *testing.T){
 b:=testBundle(t)
 path:=filepath.Join(t.TempDir(),"bundle.json")
 raw,err:=json.Marshal(b);if err!=nil{t.Fatal(err)}
 if err=os.WriteFile(path,append(raw,'\n'),0600);err!=nil{t.Fatal(err)}
 loaded,err:=readBundle(path);if err!=nil{t.Fatal(err)}
 if loaded.Schema!=schema{t.Fatal("unexpected schema")}
 var out bytes.Buffer
 if err=run([]string{"--bundle",path},&out,1000);err==nil{t.Fatal("incomplete CKB/FSA custody permitted")}
 if out.Len()!=0{t.Fatal("failure produced an approval-like report")}
 if err=os.WriteFile(path,append(raw,[]byte("{}")...),0600);err!=nil{t.Fatal(err)}
 if _,err=readBundle(path);err==nil{t.Fatal("trailing JSON admitted")}
}
func TestUnknownFieldAndDuplicateKeyRejected(t *testing.T){
 path:=filepath.Join(t.TempDir(),"bundle.json")
 b:=testBundle(t)
 raw,err:=json.Marshal(b);if err!=nil{t.Fatal(err)}
 var m map[string]any
 if err=json.Unmarshal(raw,&m);err!=nil{t.Fatal(err)}
 m["unauthorized_launch"]=true
 bad,err:=json.Marshal(m);if err!=nil{t.Fatal(err)}
 if err=os.WriteFile(path,append(bad,'\n'),0600);err!=nil{t.Fatal(err)}
 if _,err=readBundle(path);err==nil{t.Fatal("unknown command field accepted")}
 duplicate:=[]byte("{\"schema\":\""+schema+"\",\"schema\":\""+schema+"\"}\n")
 if err=os.WriteFile(path,duplicate,0600);err!=nil{t.Fatal(err)}
 if _,err=readBundle(path);err==nil{t.Fatal("duplicate top-level trust field accepted")}
}
func TestNoRelativeInputOrInvalidClock(t *testing.T){
 var out bytes.Buffer
 if err:=run([]string{"--bundle","relative.json"},&out,1000);err==nil{t.Fatal("relative evidence path accepted")}
 if err:=run([]string{"--bundle","/any/evidence.json"},&out,0);err==nil{t.Fatal("caller-provided invalid current time accepted")}
}
