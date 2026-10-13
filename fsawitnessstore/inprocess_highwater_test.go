package fsawitnessstore

import (
 "context"
 "errors"
 "os"
 "path/filepath"
 "strings"
 "testing"

 "github.com/spoonman136668-ai/forge/researchlog"
)

// A witness instance that already acknowledged revision 3 must not serve
// independently signed revision 2 if a valid last receipt is removed.
func TestInProcessWitnessHighwaterRejectsCompleteTailRollback(t *testing.T){
 p,key:=fixture(t)
 store,root:=newStore(t,p,key)
 ctx:=context.Background()
 next:=signed(t,p,key,1,3,strings.Repeat("c",64))
 if err:=store.Append(ctx,next);err!=nil{t.Fatal(err)}
 path:=filepath.Join(root,"receipts","00000001.json")
 committed,err:=os.ReadFile(path);if err!=nil{t.Fatal(err)}
 if err:=os.Remove(path);err!=nil{t.Fatal(err)}
 if _,err:=store.ReadWitness(ctx,p.ArchiveID);!errors.Is(err,ErrBlocked){
  t.Fatal("previously observed highwater rolled back silently",err)
 }
 // Restoring a path cannot silently clear poisoned-state uncertainty.
 if err:=os.WriteFile(path,committed,0600);err!=nil{t.Fatal(err)}
 if _,err:=store.ReadWitness(ctx,p.ArchiveID);!errors.Is(err,ErrBlocked){
  t.Fatal("poisoned process resumed without independent reconciliation",err)
 }
 if err:=store.Append(ctx,signed(t,p,key,2,4,strings.Repeat("d",64)));!errors.Is(err,ErrBlocked){
  t.Fatal("poisoned instance continued advancing witness",err)
 }
 // Recovery is an independently pinned NEW instance, not a retry from the
 // poisoned one; this only validates source logic, not physical durability.
 pinned:=p;pinned.MinimumRevision=3
 recovered,err:=Open(root,pinned);if err!=nil{t.Fatal(err)}
 got,err:=recovered.ReadWitness(ctx,p.ArchiveID)
 if err!=nil||got.Head.Revision!=3{t.Fatal(got,err)}
}

func TestInProcessWitnessRejectsTamperAfterEarlierRead(t *testing.T){
 p,key:=fixture(t)
 store,root:=newStore(t,p,key)
 ctx:=context.Background()
 if _,err:=store.ReadWitness(ctx,p.ArchiveID);err!=nil{t.Fatal(err)}
 path:=filepath.Join(root,"receipts","00000000.json")
 original,err:=os.ReadFile(path);if err!=nil{t.Fatal(err)}
 if err:=os.WriteFile(path,[]byte("{}"),0600);err!=nil{t.Fatal(err)}
 if _,err:=store.ReadWitness(ctx,p.ArchiveID);!errors.Is(err,ErrBlocked){t.Fatal("corruption not rejected",err)}
 if err:=os.WriteFile(path,original,0600);err!=nil{t.Fatal(err)}
 if _,err:=store.ReadWitness(ctx,p.ArchiveID);!errors.Is(err,ErrBlocked){
  t.Fatal("corrupted process resumed after external restoration",err)
 }
 // No change to the independent genesis contract.
 if _,err:=Open(root,p);err!=nil{t.Fatal("fresh pinned inspection failed",err)}
 if err:=store.Append(ctx,signed(t,p,key,1,3,strings.Repeat("c",64)));!errors.Is(err,ErrBlocked){
  t.Fatal("previously poisoned signer store admitted append",err)
 }
 _=researchlog.Genesis
}
