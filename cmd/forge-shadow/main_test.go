package main
import (
 "os"
 "testing"
)
func TestShadowCommandFailsClosedWithoutArchive(t *testing.T){
 if err:=run(nil);err==nil{t.Fatal("missing journal accepted")}
 if err:=run([]string{"--archive",t.TempDir()});err==nil{t.Fatal("unprovisioned journal accepted")}
 dir:=t.TempDir()
 if err:=os.WriteFile(dir+"/spoof.json",[]byte("{}"),0600);err!=nil{t.Fatal(err)}
 if err:=run([]string{"--archive",dir});err==nil{t.Fatal("unverified original accepted")}
}
