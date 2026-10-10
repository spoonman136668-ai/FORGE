package privatearchive

import (
 "bytes"
 "os"
 "path/filepath"
 "strings"
 "sync"
 "testing"

 "github.com/spoonman136668-ai/forge/researchlog"
)

func h(s string,n int)string{return strings.Repeat(s,n)}
func newStore(t *testing.T)*Store{
 t.Helper()
 s,err:=Initialize(filepath.Join(t.TempDir(),FolderName))
 if err!=nil{t.Fatal(err)}
 return s
}
func events(lane,id,cohort string,run uint64,raw string,outcome string)[]researchlog.Event{
 src:=h("a",40);pr:=h("b",64)
 return []researchlog.Event{
  {Lane:lane,Generation:1,ExperimentID:id,Kind:researchlog.Hypothesis,SourceCommitSHA:src,Note:"Question frozen before evaluation"},
  {Lane:lane,Generation:1,ExperimentID:id,Kind:researchlog.Preregister,SourceCommitSHA:src,PreregSHA256:pr,CohortSHA256:cohort},
  {Lane:lane,Generation:1,ExperimentID:id,Kind:researchlog.SourceQualified,SourceCommitSHA:src,PreregSHA256:pr,CohortSHA256:cohort,WitnessSHA256:h("c",64)},
  {Lane:lane,Generation:1,ExperimentID:id,Kind:researchlog.PrimaryStarted,SourceCommitSHA:src,PreregSHA256:pr,CohortSHA256:cohort,WitnessSHA256:h("d",64),RunID:run},
  {Lane:lane,Generation:1,ExperimentID:id,Kind:researchlog.PrimaryTerminal,SourceCommitSHA:src,PreregSHA256:pr,CohortSHA256:cohort,WitnessSHA256:h("e",64),RunID:run,OriginalEvidenceSHA256:raw,Outcome:outcome},
  {Lane:lane,Generation:1,ExperimentID:id,Kind:researchlog.IndependentReview,SourceCommitSHA:src,PreregSHA256:pr,CohortSHA256:cohort,WitnessSHA256:h("f",64),RunID:run,OriginalEvidenceSHA256:raw,Outcome:outcome,Note:"Original result independently reviewed"},
  {Lane:lane,Generation:1,ExperimentID:id,Kind:researchlog.FinalArchive,SourceCommitSHA:src,PreregSHA256:pr,CohortSHA256:cohort,WitnessSHA256:h("1",64),RunID:run,OriginalEvidenceSHA256:raw,Outcome:outcome,Note:"Result archived without replay"},
 }
}
func push(t *testing.T,s *Store,e researchlog.Event)researchlog.Record{
 t.Helper();r,err:=s.AppendEvent(e);if err!=nil{t.Fatalf("append %s: %v",e.Kind,err)};return r
}
func TestWriteOnceNegativeOriginalAndRestart(t *testing.T){
 s:=newStore(t)
 original:=[]byte("stdout: threshold unmet\nstderr: none\nexit=0")
 raw,err:=s.SaveOriginal(original);if err!=nil{t.Fatal(err)}
 again,err:=s.SaveOriginal(original);if err!=nil||again!=raw{t.Fatal("idempotent original",err)}
 for _,e:=range events("Wingless","W01",h("2",64),123,raw,"NEGATIVE"){push(t,s,e)}
 restarted,err:=Open(s.root);if err!=nil{t.Fatal(err)}
 j,err:=restarted.Load();if err!=nil{t.Fatal(err)}
 if len(j.Entries)!=7||j.Entries[4].Event.Outcome!="NEGATIVE"||j.Entries[6].Event.OriginalEvidenceSHA256!=raw{t.Fatal("negative or original lost")}
 got,err:=restarted.ReadOriginal(raw);if err!=nil||!bytes.Equal(got,original){t.Fatal("raw evidence mismatch",err)}
 if _,err=restarted.AppendEvent(events("Wingless","W01",h("2",64),123,raw,"NEGATIVE")[3]);err==nil{t.Fatal("primary replay accepted")}
}
func TestNoPrimaryTerminalWithoutPrivateRawEvidence(t *testing.T){
 s:=newStore(t)
 ev:=events("Yggdrasil","Y01",h("3",64),324,h("f",64),"MIXED")
 for _,e:=range ev[:4]{push(t,s,e)}
 if _,err:=s.AppendEvent(ev[4]);err==nil{t.Fatal("terminal without original bytes accepted")}
 j,err:=s.Load();if err!=nil||len(j.Entries)!=4{t.Fatal("unbacked terminal mutated journal",err)}
 if _,err:=s.ReadOriginal(h("f",64));err==nil{t.Fatal("missing evidence accepted")}
}
func TestIndependentLanesAndImmutableCohortReservation(t *testing.T){
 s:=newStore(t);raw,err:=s.SaveOriginal([]byte("raw negative source"));if err!=nil{t.Fatal(err)}
 for _,e:=range events("Wingless","W01",h("2",64),121,raw,"NEGATIVE"){push(t,s,e)}
 another:=events("Yggdrasil","Y01",h("3",64),122,raw,"MIXED")
 for _,e:=range another{push(t,s,e)}
 j,err:=s.Load();if err!=nil||len(j.Entries)!=14||j.Entries[11].Event.Outcome!="MIXED"{t.Fatal("cross-lane persistence failure",err)}
 dup:=events("Yggdrasil","Y02",h("2",64),123,raw,"SUPPORTED")
 push(t,s,dup[0])
 if _,err:=s.AppendEvent(dup[1]);err==nil{t.Fatal("previously used cohort reused")}
}
func TestCorruptionGapAndIncompleteWriteFailClosed(t *testing.T){
 s:=newStore(t);raw,err:=s.SaveOriginal([]byte("raw"));if err!=nil{t.Fatal(err)}
 for _,e:=range events("Wingless","W01",h("2",64),1,raw,"INVALID"){push(t,s,e)}
 path:=filepath.Join(s.root,"records","00000008.json")
 if err=os.WriteFile(path,[]byte("{partial"),0600);err!=nil{t.Fatal(err)}
 if _,err=s.Load();err==nil{t.Fatal("interrupted write undetected")}
 if _,err=s.AppendEvent(events("Yggdrasil","Y01",h("4",64),2,raw,"MIXED")[0]);err==nil{t.Fatal("auto retry over incomplete record")}
 if err=os.Remove(path);err!=nil{t.Fatal(err)}
 path=filepath.Join(s.root,"records","00000002.json")
 if err=os.WriteFile(path,[]byte("tampered"),0600);err!=nil{t.Fatal(err)}
 if _,err=s.Load();err==nil{t.Fatal("tampering undetected")}
}
func TestConcurrentSingleSequenceWriteOnce(t *testing.T){
 s:=newStore(t)
 start:=make(chan struct{})
 var wg sync.WaitGroup
 results:=make(chan error,2)
 for _,id:=range []string{"W01","W02"}{
  wg.Add(1)
  go func(id string){defer wg.Done();<-start
   _,err:=s.AppendEvent(events("Wingless",id,h("2",64),1,h("3",64),"NEGATIVE")[0]);results<-err
  }(id)
 }
 close(start);wg.Wait();close(results)
 success:=0;fail:=0
 for err:=range results{if err==nil{success++}else{fail++}}
 if success!=1||fail!=1{t.Fatalf("concurrent sequence outcomes success=%d fail=%d",success,fail)}
 j,err:=s.Load();if err!=nil||len(j.Entries)!=1{t.Fatal("concurrent writes corrupted archive",err)}
}
func TestForeignPathsAndSymlinksRejected(t *testing.T){
 root:=filepath.Join(t.TempDir(),"KTRADE",FolderName)
 if _,err:=Initialize(root);err==nil{t.Fatal("KTRADE boundary ignored")}
 s:=newStore(t)
 if _,err:=Initialize(s.root);err==nil{t.Fatal("existing store replaced")}
 if _,err:=Open(filepath.Join(t.TempDir(),"other"));err==nil{t.Fatal("wrong root accepted")}
 target:=filepath.Join(s.root,"originals",h("a",64)+".raw")
 if err:=os.Symlink("elsewhere",target);err==nil{
  if _,err:=s.ReadOriginal(h("a",64));err==nil{t.Fatal("symlinked original accepted")}
 }
}

func TestAuthenticatedHighWaterComparisonRejectsTailRollback(t *testing.T){
 s:=newStore(t)
 raw,err:=s.SaveOriginal([]byte("original complete observation"));if err!=nil{t.Fatal(err)}
 var last researchlog.Record
 for _,e:=range events("Wingless","W03",h("6",64),333,raw,"NEGATIVE"){last=push(t,s,e)}
 if err:=s.VerifyTrustedHead(7,last.RecordSHA256);err!=nil{t.Fatal(err)}
 if err:=os.Remove(filepath.Join(s.root,"records","00000007.json"));err!=nil{t.Fatal(err)}
 // The remaining chain is structurally consistent: an external authenticated
 // high-water witness is essential for detecting valid-tail deletion.
 if err:=s.VerifyTrustedHead(7,last.RecordSHA256);err==nil{t.Fatal("valid-tail rollback accepted")}
 if err:=s.VerifyTrustedHead(0,Genesis);err==nil{t.Fatal("stale claimed head accepted")}
}
func TestParentSymlinkCannotRedirectArchive(t *testing.T){
 root:=t.TempDir();target:=filepath.Join(root,"target")
 if err:=os.Mkdir(target,0700);err!=nil{t.Fatal(err)}
 alias:=filepath.Join(root,"alias")
 if err:=os.Symlink(target,alias);err!=nil{t.Skip("symlink unavailable on this host")}
 if _,err:=Initialize(filepath.Join(alias,FolderName));err==nil{t.Fatal("parent symlink redirected store")}
}
