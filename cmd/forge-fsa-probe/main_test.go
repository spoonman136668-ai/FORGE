package main

import (
 "context"
 "errors"
 "path/filepath"
 "testing"

 "github.com/spoonman136668-ai/forge/fsaprobe"
)
func TestNoTrustProbeWithoutIndependentPinnedConfig(t *testing.T){
 for _,args:=range [][]string{nil,{},{"-config","relative.json"},
  {"-config",filepath.Join(t.TempDir(),"missing.json")},
  {"-config","unknown.json","unexpected"}}{
  if _,err:=run(context.Background(),args);!errors.Is(err,fsaprobe.ErrBlocked){
   t.Fatalf("unprovisioned trust probe accepted %q: %v",args,err)
  }
 }
}
