package main

import (
 "context"
 "errors"
 "path/filepath"
 "testing"

 "github.com/spoonman136668-ai/forge/authorityhost"
)
func TestAuthorityExecutableFailsClosedWithoutPinnedProvisioning(t *testing.T){
 for _,args:=range [][]string{
  nil,{},{"-config","relative.json"},
  {"-config",filepath.Join(t.TempDir(),"missing.json")},
  {"-config","any.json","unexpected"},
 }{
  if err:=run(context.Background(),args);!errors.Is(err,authorityhost.ErrUnprovisioned){
   t.Fatalf("unprovisioned authority host accepted %q: %v",args,err)
  }
 }
}
