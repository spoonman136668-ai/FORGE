package main

import (
 "context"
 "errors"
 "path/filepath"
 "testing"

 "github.com/spoonman136668-ai/forge/witnesshost"
)
func TestWitnessExecutableNeverBootsWithoutIndependentConfig(t *testing.T){
 for _,args:=range [][]string{
  nil,
  {},
  {"-config",filepath.Join(t.TempDir(),"missing.json")},
  {"-config","not-absolute.json"},
  {"-config","foo.json","unexpected"},
 }{
  if err:=run(context.Background(),args);!errors.Is(err,witnesshost.ErrUnprovisioned){
   t.Fatalf("unprovisioned witness host accepted args %q: %v",args,err)
  }
 }
 ctx,cancel:=context.WithCancel(context.Background());cancel()
 if err:=run(ctx,[]string{"-config","nonexistent"});!errors.Is(err,witnesshost.ErrUnprovisioned){
  t.Fatal("canceled unprovisioned service launched",err)
 }
}
