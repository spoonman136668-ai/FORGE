package fsawitnessguard

import (
 "bytes"
 "context"
 "crypto/ed25519"
 "encoding/hex"
 "encoding/json"
 "errors"
 "strings"
 "sync"
 "testing"
 "github.com/spoonman136668-ai/forge/fsaremote"
 "github.com/spoonman136668-ai/forge/researchlog"
)

type memoryLedger struct {
 mu sync.Mutex
 current fsaremote.SignedWitness
 calls int
 conflict bool
 ambiguous bool
}
func(m *memoryLedger)Read(_ context.Context)(fsaremote.SignedWitness,error) {
 m.mu.Lock();defer m.mu.Unlock();return m.current,nil
}
func(m *memoryLedger)CompareAndSwap(_ context.Context,expected string,next fsaremote.SignedWitness)(bool,error) {
 m.mu.Lock();defer m.mu.Unlock();m.calls++
 actual,_:=digest(m.current)
 if m.conflict||actual!=expected{return false,nil}
 m.current=next
 if m.ambiguous{return false,errors.New("write may have committed")}
 return true,nil
}
type memoryFloor struct {
 mu sync.Mutex
 current Commitment
 calls int
 broken bool
 outage bool
}
func(m *memoryFloor)Read(_ context.Context)(Commitment,error) {
 m.mu.Lock();defer m.mu.Unlock()
 if m.outage{return Commitment{},errors.New("separate domain unreachable")}
 return m.current,nil
}
func(m *memoryFloor)CompareAndSwap(_ context.Context,expected,next Commitment)(bool,error) {
 m.mu.Lock();defer m.mu.Unlock();m.calls++
 if m.broken{return false,errors.New("indeterminate floor write")}
 if m.current!=expected{return false,nil}
 if next.Revision<=m.current.Revision{return false,errors.New("nonmonotonic")}
 m.current=next;return true,nil
}
func signed(t *testing.T,h fsaremote.WitnessHead,private ed25519.PrivateKey)fsaremote.SignedWitness {
 t.Helper()
 raw,err:=json.Marshal(h);if err!=nil{t.Fatal(err)}
 signature:=ed25519.Sign(private,append([]byte("FORGE-FSA-INDEPENDENT-HIGHWATER-V1\n"),raw...))
 return fsaremote.SignedWitness{Head:h,SignatureHex:hex.EncodeToString(signature)}
}
func setup(t *testing.T)(*Guard,*memoryLedger,*memoryFloor,fsaremote.SignedWitness,fsaremote.SignedWitness,ed25519.PrivateKey) {
 t.Helper()
 authorityKey:=ed25519.NewKeyFromSeed(bytes.Repeat([]byte{1},32)).Public().(ed25519.PublicKey)
 witnessPrivate:=ed25519.NewKeyFromSeed(bytes.Repeat([]byte{2},32))
 p:=fsaremote.Pin{ArchiveID:strings.Repeat("a",64),KeyID:"witness-key-1",
  PublicKey:authorityKey,AuthorityEpoch:3,BindingSHA256:strings.Repeat("c",64),
  WitnessPublicKey:witnessPrivate.Public().(ed25519.PublicKey),MinimumRevision:5}
 h:=fsaremote.WitnessHead{Schema:fsaremote.WitnessSchema,Domain:fsaremote.WitnessDomain,
  ArchiveID:p.ArchiveID,KeyID:p.KeyID,AuthorityEpoch:p.AuthorityEpoch,
  BindingSHA256:p.BindingSHA256,Sequence:0,HeadSHA256:researchlog.Genesis,Revision:5}
 first:=signed(t,h,witnessPrivate)
 h.Revision=6;h.Sequence=1;h.HeadSHA256=strings.Repeat("b",64)
 next:=signed(t,h,witnessPrivate)
 checksum,err:=digest(first);if err!=nil{t.Fatal(err)}
 ledger:=&memoryLedger{current:first}
 floor:=&memoryFloor{current:Commitment{Revision:5,WitnessSHA256:checksum}}
 guard,err:=New(p,ledger,floor);if err!=nil{t.Fatal(err)}
 return guard,ledger,floor,first,next,witnessPrivate
}
func TestReadAdvanceRestartAndRollbackRefusal(t *testing.T) {
 g,l,f,first,next,_:=setup(t);ctx:=context.Background()
 if got,err:=g.ReadHighWater(ctx,g.pin.ArchiveID);err!=nil||got.Head.Sequence!=0{t.Fatalf("initial %v %+v",err,got.Head)}
 ok,err:=g.Advance(ctx,first,next);if err!=nil||!ok{t.Fatalf("advance ok=%v err=%v",ok,err)}
 if l.calls!=1||f.calls!=1{t.Fatalf("writes ledger=%d floor=%d",l.calls,f.calls)}
 reopened,err:=New(g.pin,l,f);if err!=nil{t.Fatal(err)}
 if got,err:=reopened.ReadHighWater(ctx,g.pin.ArchiveID);err!=nil||got.Head.Revision!=6{t.Fatalf("restart %v %+v",err,got.Head)}
 l.mu.Lock();l.current=first;l.mu.Unlock()
 if _,err:=reopened.ReadHighWater(ctx,g.pin.ArchiveID);!errors.Is(err,ErrUntrusted){t.Fatalf("ledger rollback accepted %v",err)}
 l.mu.Lock();l.current=next;l.mu.Unlock()
 f.mu.Lock();f.current.Revision=5;f.mu.Unlock()
 if _,err:=reopened.ReadHighWater(ctx,g.pin.ArchiveID);!errors.Is(err,ErrUntrusted){t.Fatalf("floor rollback accepted %v",err)}
}
func TestPreflightRefusalsAndNoWrites(t *testing.T) {
 g,l,f,first,next,private:=setup(t);ctx:=context.Background()
 if _,err:=g.ReadHighWater(ctx,strings.Repeat("d",64));!errors.Is(err,ErrUntrusted){t.Fatal("foreign archive accepted")}
 if _,err:=g.ReadHighWater(nil,g.pin.ArchiveID);!errors.Is(err,ErrUntrusted){t.Fatal("nil context accepted")}
 tampered:=next;tampered.SignatureHex=strings.Repeat("0",128)
 if ok,err:=g.Advance(ctx,first,tampered);ok||!errors.Is(err,ErrUntrusted){t.Fatalf("forgery ok=%v err=%v",ok,err)}
 skipped:=next;skipped.Head.Revision=7;skipped=signed(t,skipped.Head,private)
 if ok,err:=g.Advance(ctx,first,skipped);ok||!errors.Is(err,ErrUntrusted){t.Fatalf("skip accepted %v %v",ok,err)}
 wrongIdentity:=next;wrongIdentity.Head.BindingSHA256=strings.Repeat("d",64);wrongIdentity=signed(t,wrongIdentity.Head,private)
 if ok,err:=g.Advance(ctx,first,wrongIdentity);ok||!errors.Is(err,ErrUntrusted){t.Fatalf("identity substitution %v %v",ok,err)}
 if ok,err:=g.Advance(ctx,next,next);ok||err!=nil{t.Fatalf("stale expected got %v %v",ok,err)}
 if l.calls!=0||f.calls!=0{t.Fatalf("preflight wrote: %d %d",l.calls,f.calls)}
 f.outage=true
 if _,err:=g.ReadHighWater(ctx,g.pin.ArchiveID);!errors.Is(err,ErrUntrusted){t.Fatalf("floor outage %v",err)}
 if _,err:=New(g.pin,nil,f);!errors.Is(err,ErrUntrusted){t.Fatal("missing ledger accepted")}
 if _,err:=New(g.pin,l,nil);!errors.Is(err,ErrUntrusted){t.Fatal("missing floor accepted")}
}
func TestIndeterminateAndConflictingWritesNeverReplayed(t *testing.T) {
 t.Run("conflict",func(t *testing.T){
  g,l,f,first,next,_:=setup(t);l.conflict=true
  if ok,err:=g.Advance(context.Background(),first,next);ok||err!=nil{t.Fatalf("conflict %v %v",ok,err)}
  if l.calls!=1||f.calls!=0{t.Fatal("unexpected floor write or replay")}
 })
 t.Run("uncertain ledger commit",func(t *testing.T){
  g,l,f,first,next,_:=setup(t);l.ambiguous=true
  if ok,err:=g.Advance(context.Background(),first,next);ok||!errors.Is(err,ErrUntrusted){t.Fatalf("uncertain %v %v",ok,err)}
  if l.calls!=1||f.calls!=0{t.Fatal("uncertain commit was replayed")}
  if _,err:=g.ReadHighWater(context.Background(),g.pin.ArchiveID);!errors.Is(err,ErrUntrusted){t.Fatalf("mismatched floor ignored %v",err)}
 })
 t.Run("uncertain floor commit",func(t *testing.T){
  g,l,f,first,next,_:=setup(t);f.broken=true
  if ok,err:=g.Advance(context.Background(),first,next);ok||!errors.Is(err,ErrUntrusted){t.Fatalf("uncertain %v %v",ok,err)}
  if l.calls!=1||f.calls!=1{t.Fatal("ambiguous floor was retried")}
  if _,err:=g.ReadHighWater(context.Background(),g.pin.ArchiveID);!errors.Is(err,ErrUntrusted){t.Fatalf("inconsistent state read %v",err)}
 })
}
func TestConcurrentSamePredecessorOneWinner(t *testing.T) {
 g,l,f,first,next,_:=setup(t)
 var wg sync.WaitGroup;outcomes:=make(chan bool,2)
 for i:=0;i<2;i++{wg.Add(1);go func(){defer wg.Done();ok,_:=g.Advance(context.Background(),first,next);outcomes<-ok}()}
 wg.Wait();close(outcomes)
 successes:=0;for ok:=range outcomes{if ok{successes++}}
 if successes!=1{t.Fatalf("expected one signed successor success, got %d",successes)}
 if l.calls<1||l.calls>2||f.calls!=1{t.Fatalf("ledger=%d floor=%d",l.calls,f.calls)}
}
