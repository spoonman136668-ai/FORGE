//go:build windows

package main

import (
 "bytes"
 "crypto/ed25519"
 "crypto/rand"
 "os"
 "path/filepath"
 "testing"
)

func TestDPAPICurrentUserRoundTrip(t *testing.T){
 seed:=make([]byte,ed25519.SeedSize)
 if _,err:=rand.Read(seed);err!=nil{t.Fatal(err)}
 blob,err:=dpapi(seed,true);if err!=nil{t.Fatal(err)}
 if bytes.Equal(blob,seed){t.Fatal("plaintext key persisted")}
 restored,err:=dpapi(blob,false);if err!=nil{t.Fatal(err)}
 if !bytes.Equal(restored,seed){t.Fatal("DPAPI altered seed")}
}
func TestBootstrapNoOverwriteAndSignedProof(t *testing.T){
 path:=filepath.Join(t.TempDir(),"owner.dpapi")
 if err:=bootstrap(path);err!=nil{t.Fatal(err)}
 if err:=bootstrap(path);err==nil{t.Fatal("identity overwritten")}
 seed,err:=loadSeed(path);if err!=nil{t.Fatal(err)}
 pk:=ed25519.NewKeyFromSeed(seed)
 data:=[]byte(domain+"challenge")
 sig:=ed25519.Sign(pk,data)
 if !ed25519.Verify(pk.Public().(ed25519.PublicKey),data,sig){t.Fatal("signature invalid")}
 if err:=os.WriteFile(path,[]byte("incorrect-key"),0600);err!=nil{t.Fatal(err)}
 if _,err:=loadSeed(path);err==nil{t.Fatal("tamper accepted")}
}
