package main

import (
 "encoding/json"
 "os"
 "path/filepath"
 "strings"
 "testing"
)

func goodConfig()config {
 return config{Schema:configSchema,ArchiveID:strings.Repeat("a",64),
  KeyID:"FORGE_TEST_ONLY",AuthorityKeyHex:strings.Repeat("b",64),
  AuthorityEpoch:3,BindingSHA256:strings.Repeat("c",64),
  WitnessKeyHex:strings.Repeat("d",64),MinimumRevision:1,
  Authority:peerConfig{URL:"https://authority.example.test:8443",
   ServerSPKISHA256:strings.Repeat("e",64)},
  Witness:peerConfig{URL:"https://witness.example.test:8443",
   ServerSPKISHA256:strings.Repeat("f",64)}}
}
func TestDecodePinnedConfigurationFailClosed(t *testing.T) {
 base:=goodConfig()
 good,_:=json.Marshal(base)
 if _,err:=decode(good);err!=nil{t.Fatal(err)}
 for _,tc:=range []struct{name string;mutate func(*config)}{
  {"missing schema",func(c *config){c.Schema=""}},
  {"empty archive",func(c *config){c.ArchiveID=""}},
  {"shared keys",func(c *config){c.WitnessKeyHex=c.AuthorityKeyHex}},
  {"shared endpoint",func(c *config){c.Witness.URL=c.Authority.URL}},
  {"shared spki",func(c *config){c.Witness.ServerSPKISHA256=c.Authority.ServerSPKISHA256}},
  {"zero revision",func(c *config){c.MinimumRevision=0}},
  {"zero epoch",func(c *config){c.AuthorityEpoch=0}},
  {"uppercase hex",func(c *config){c.ArchiveID=strings.Repeat("A",64)}},
  {"invalid key name",func(c *config){c.KeyID="../secrets"}},
 }{
  t.Run(tc.name,func(t *testing.T){cfg:=goodConfig();tc.mutate(&cfg)
   b,_:=json.Marshal(cfg)
   if _,err:=decode(b);err==nil{t.Fatal("invalid independent pins accepted")}
  })
 }
 for _,raw:=range [][]byte{
  []byte("{}{}"),[]byte("{"),[]byte(`{"extra":1}`),
  append(good,[]byte("{}")...),make([]byte,maxConfigBytes+1),
  []byte(strings.Replace(string(good),`"schema":`,`"unknown":8,"schema":`,1)),
 }{
  if _,err:=decode(raw);err==nil{t.Fatal("ambiguous config accepted")}
 }
}
func TestRejectUnpinnedFilesAndUnconfiguredProbe(t *testing.T) {
 if _,err:=readRegular("relative.json",maxConfigBytes);err==nil{t.Fatal("relative file accepted")}
 if _,err:=run("");err==nil{t.Fatal("missing config accepted")}
 dir:=t.TempDir()
 f:=filepath.Join(dir,"config.json")
 if err:=os.WriteFile(f,[]byte("{}"),0600);err!=nil{t.Fatal(err)}
 if _,err:=run(f);err==nil{t.Fatal("empty config accepted")}
 link:=filepath.Join(dir,"linked-config.json")
 if err:=os.Symlink(f,link);err==nil{
  if _,err:=readRegular(link,maxConfigBytes);err==nil{t.Fatal("symlink accepted")}
 }
}
