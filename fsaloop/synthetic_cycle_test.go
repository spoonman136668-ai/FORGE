// This is a source-only, synthetic FSA lifecycle exercise. It does NOT
// provision an independent authority, dispatch workers or conduct real science.
// NEVER use these in-process trust fixtures as deployment credentials/authority.
package fsaloop_test

import (
	"bytes"
	"context"
	"crypto/ed25519"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/spoonman136668-ai/forge/eligibility"
	"github.com/spoonman136668-ai/forge/fsaadmission"
	"github.com/spoonman136668-ai/forge/fsahead"
	"github.com/spoonman136668-ai/forge/fsaintent"
	"github.com/spoonman136668-ai/forge/fsatrust"
	"github.com/spoonman136668-ai/forge/privatearchive"
	"github.com/spoonman136668-ai/forge/researchlog"
	"github.com/spoonman136668-ai/forge/startrecovery"
)

type syntheticAuthority struct {
	anchor fsahead.Anchor
	casCount int
}

func (s *syntheticAuthority) ReadAnchor(context.Context) (fsahead.Anchor, error) {
	a := s.anchor
	a.PublicKey = append(ed25519.PublicKey(nil), a.PublicKey...)
	return a, nil
}
func (s *syntheticAuthority) ConfirmArchiveBinding(_ context.Context, id string) (bool,error) {
	return id == s.anchor.ArchiveID, nil
}
func (s *syntheticAuthority) CompareAndSwap(_ context.Context, prev, next fsahead.Anchor) (bool,error) {
	if prev.Sequence != s.anchor.Sequence || prev.HeadSHA256 != s.anchor.HeadSHA256 ||
		prev.ArchiveID != s.anchor.ArchiveID || !bytes.Equal(prev.PublicKey,s.anchor.PublicKey) {
		return false,nil
	}
	s.anchor=next
	s.casCount++
	return true,nil
}
func repeat(char string,n int)string {return strings.Repeat(char,n)}
func freeze(t *testing.T,lane,id,src,prereg,cohort,protocol string,budget uint64) (eligibility.Frozen,string) {
	t.Helper()
	p:=eligibility.Frozen{
		Schema:eligibility.Schema,Lane:lane,CandidateID:id,
		SourceSHA:repeat(src,40),PreregSHA256:repeat(prereg,64),
		CohortSHA256:repeat(cohort,64),ProtocolSHA256:repeat(protocol,64),
		BudgetUnits:budget,SeedIDs:[]string{lane+":seed_"+id},
	}
	pin,err:=eligibility.Fingerprint(p)
	if err!=nil {t.Fatal(err)}
	return p,pin
}
func scientificEvent(p eligibility.Frozen,pin string,kind researchlog.Kind,run uint64,original,outcome string) researchlog.Event {
	e:=researchlog.Event{
		Lane:p.Lane,Generation:3,ExperimentID:p.CandidateID,Kind:kind,
		SourceCommitSHA:p.SourceSHA,PreregSHA256:p.PreregSHA256,CohortSHA256:p.CohortSHA256,
		RunID:run,
	}
	switch kind {
	case researchlog.Hypothesis:
		e.PreregSHA256="";e.CohortSHA256="";e.RunID=0
		e.Note="Synthetic question only, no real scientific experiment"
	case researchlog.Preregister:
		e.RunID=0
	case researchlog.SourceQualified:
		e.RunID=0;e.WitnessSHA256=pin
	case researchlog.PrimaryStarted:
		e.WitnessSHA256=repeat("d",64)
	case researchlog.PrimaryTerminal:
		e.WitnessSHA256=repeat("e",64);e.OriginalEvidenceSHA256=original;e.Outcome=outcome
	case researchlog.IndependentReview:
		e.WitnessSHA256=repeat("f",64);e.OriginalEvidenceSHA256=original;e.Outcome=outcome
		e.Note="Synthetic review preserves the original outcome"
	case researchlog.FinalArchive:
		e.WitnessSHA256=repeat("1",64);e.OriginalEvidenceSHA256=original;e.Outcome=outcome
		e.Note="Synthetic original archived without replay"
	}
	return e
}
func addEvent(t *testing.T,store *privatearchive.Store,e researchlog.Event){
	t.Helper()
	if _,err:=store.AppendEvent(e);err!=nil {t.Fatalf("%s/%s %s: %v",e.Lane,e.ExperimentID,e.Kind,err)}
}
func addIntent(t *testing.T,j fsaintent.Journal,i fsaintent.Intent,s fsaintent.Stage,receipt string)fsaintent.Journal{
	t.Helper()
	out,err:=fsaintent.Append(j,i,s,receipt)
	if err!=nil{t.Fatalf("intent %s/%s %s: %v",i.Lane,i.CandidateID,s,err)}
	return out
}
func intentOf(p eligibility.Frozen,pin string,run uint64)fsaintent.Intent{
	return fsaintent.Intent{
		Lane:p.Lane,CandidateID:p.CandidateID,Generation:3,RunID:run,
		FrozenSHA256:pin,CohortSHA256:p.CohortSHA256,
		SourceSHA:p.SourceSHA,PreregSHA256:p.PreregSHA256,BudgetUnits:p.BudgetUnits,
	}
}
func intentHead(j fsaintent.Journal)fsaintent.TrustedHead{
	return fsaintent.TrustedHead{Sequence:uint64(len(j.Entries)),
		SHA256:j.Entries[len(j.Entries)-1].RecordSHA256,
		IndependentlyAuthenticated:true} // SYNTHETIC fixture, not real trust.
}
func checkDecision(t *testing.T,j fsaintent.Journal,i fsaintent.Intent,want fsaintent.Decision){
	t.Helper()
	got,err:=fsaintent.Inspect(j,intentHead(j),i.Lane,i.CandidateID)
	if err!=nil||got!=want{t.Fatalf("%s/%s: want %s, got %s: %v",i.Lane,i.CandidateID,want,got,err)}
}
func signSynthetic(t *testing.T,old fsahead.Anchor,sk ed25519.PrivateKey,sequence uint64,sha string)fsahead.SignedHead{
	t.Helper()
	p:=fsahead.Payload{
		Schema:fsahead.Schema,Domain:fsahead.Domain,ArchiveID:old.ArchiveID,
		KeyID:old.KeyID,AuthorityEpoch:old.AuthorityEpoch,
		ParentSequence:old.Sequence,ParentHeadSHA256:old.HeadSHA256,
		Sequence:sequence,HeadSHA256:sha,
	}
	raw,err:=json.Marshal(p);if err!=nil{t.Fatal(err)}
	msg:=append([]byte("FORGE-FSA-ARCHIVE-HEAD-SIGNATURE-V1\n"),raw...)
	return fsahead.SignedHead{Payload:p,SignatureHex:hex.EncodeToString(ed25519.Sign(sk,msg))}
}
func advanceSynthetic(t *testing.T,backend *syntheticAuthority,archive *privatearchive.Store,id fsatrust.Identity,sk ed25519.PrivateKey){
	t.Helper()
	j,err:=archive.Load();if err!=nil{t.Fatal(err)}
	head:=j.Entries[len(j.Entries)-1]
	certificate:=signSynthetic(t,backend.anchor,sk,head.Sequence,head.RecordSHA256)
	if _,err:=fsatrust.Advance(context.Background(),backend,archive,id,certificate);err!=nil{t.Fatal(err)}
	recovered,err:=fsatrust.Recover(context.Background(),backend,archive,id)
	if err!=nil||recovered.Sequence!=head.Sequence||recovered.HeadSHA256!=head.RecordSHA256{
		t.Fatalf("synthetic checkpoint recovery: %v",err)
	}
}
func ledger(t *testing.T,consumed []string,starts []eligibility.StartRecord)(eligibility.LedgerSnapshot,string){
	t.Helper()
	x:=eligibility.LedgerSnapshot{
		Schema:"forge.eligibility.ledger-snapshot.v1",Scope:"ALL_LANES",Generation:3,
		ConsumedCohorts:consumed,ActiveCohorts:[]string{},Starts:starts,
	}
	pin,err:=eligibility.LedgerFingerprint(x);if err!=nil{t.Fatal(err)}
	return x,pin
}
func preflight(t *testing.T,backend *syntheticAuthority,archive *privatearchive.Store,id fsatrust.Identity,
	p eligibility.Frozen,pin string,l eligibility.LedgerSnapshot,ledgerPin string) {
	t.Helper()
	decision,err:=fsaadmission.AssessArchived(context.Background(),backend,archive,id,
		fsaadmission.Evidence{
			Frozen:p,FrozenPinSHA256:pin,Ledger:l,LedgerPinSHA256:ledgerPin,
			LedgerGeneration:3,CompleteAllLanes:true,ExperimentGeneration:3,
		})
	if err!=nil||decision!=fsaadmission.PreflightOnly{
		t.Fatalf("synthetic %s preflight: got %s, %v",p.Lane,decision,err)
	}
	if _,err:=fsaadmission.AssessArchived(context.Background(),nil,archive,id,
		fsaadmission.Evidence{Frozen:p});err==nil{
		t.Fatal("missing external authority was silently admitted")
	}
}

func TestSyntheticTwoLaneLifecycleRecoveryAndSuccessorPreparation(t *testing.T){
	// All evidence, keys and the fake authority live in a test temporary dir
	// and in-process memory. None are independent deployment credentials.
	root:=filepath.Join(t.TempDir(),privatearchive.FolderName)
	archive,err:=privatearchive.Initialize(root);if err!=nil{t.Fatal(err)}
	seed:=sha256.Sum256([]byte("TEST ONLY deterministic FORGE mock signer, never deploy"))
	priv:=ed25519.NewKeyFromSeed(seed[:])
	pub:=priv.Public().(ed25519.PublicKey)
	a:=fsahead.Anchor{ArchiveID:repeat("a",64),KeyID:"FORGE_SYNTHETIC_TEST_ONLY",
		PublicKey:pub,AuthorityEpoch:1,Sequence:0,HeadSHA256:researchlog.Genesis}
	backend:=&syntheticAuthority{anchor:a}
	identity:=fsatrust.Identity{ArchiveID:a.ArchiveID,KeyID:a.KeyID,
		PublicKey:append(ed25519.PublicKey(nil),pub...),AuthorityEpoch:1}
	w,wp:=freeze(t,"Wingless","W_001","a","1","5","9",10)
	y,yp:=freeze(t,"Yggdrasil","Y_001","b","2","6","a",11)
	for _,c:=range []struct{p eligibility.Frozen;pin string}{{w,wp},{y,yp}}{
		for _,stage:=range []researchlog.Kind{
			researchlog.Hypothesis,researchlog.Preregister,researchlog.SourceQualified,
		}{addEvent(t,archive,scientificEvent(c.p,c.pin,stage,0,"",""))}
	}
	advanceSynthetic(t,backend,archive,identity,priv)
	l,lp:=ledger(t,[]string{},[]eligibility.StartRecord{})
	preflight(t,backend,archive,identity,w,wp,l,lp)
	preflight(t,backend,archive,identity,y,yp,l,lp)
	intents:=fsaintent.New()
	wi,yi:=intentOf(w,wp,8001),intentOf(y,yp,8002)
	intents=addIntent(t,intents,wi,fsaintent.Prepared,"")
	intents=addIntent(t,intents,yi,fsaintent.Prepared,"")
	checkDecision(t,intents,wi,fsaintent.PreparedOnly)
	// A shared cohort or run ID across independent lanes must never proceed.
	collision:=yi;collision.CandidateID="Y_COLLISION";collision.CohortSHA256=wi.CohortSHA256
	if _,err:=fsaintent.Append(intents,collision,fsaintent.Prepared,"");err==nil{t.Fatal("cross-lane cohort collision accepted")}
	collision=yi;collision.CandidateID="Y_OTHER";collision.RunID=wi.RunID
	if _,err:=fsaintent.Append(intents,collision,fsaintent.Prepared,"");err==nil{t.Fatal("cross-lane run ID collision accepted")}
	for _,cycle:=range []struct{
		p eligibility.Frozen;pin string;i fsaintent.Intent;outcome string
	}{{w,wp,wi,"SUPPORTED"},{y,yp,yi,"NEGATIVE"}}{
		intents=addIntent(t,intents,cycle.i,fsaintent.DispatchRisk,"")
		checkDecision(t,intents,cycle.i,fsaintent.NoRedispatchUnknown)
		if _,err:=fsaintent.Append(intents,cycle.i,fsaintent.DispatchRisk,"");err==nil{
			t.Fatal("uncertain dispatch allowed to replay")
		}
		addEvent(t,archive,scientificEvent(cycle.p,cycle.pin,researchlog.PrimaryStarted,cycle.i.RunID,"",""))
		intents=addIntent(t,intents,cycle.i,fsaintent.StartObserved,repeat("d",64))
		checkDecision(t,intents,cycle.i,fsaintent.NoRedispatchStarted)
		raw:=[]byte("SYNTHETIC ONLY; "+cycle.p.Lane+" outcome="+cycle.outcome+"; no scientific process ran")
		original,err:=archive.SaveOriginal(raw);if err!=nil{t.Fatal(err)}
		for _,stage:=range []researchlog.Kind{
			researchlog.PrimaryTerminal,researchlog.IndependentReview,researchlog.FinalArchive,
		}{addEvent(t,archive,scientificEvent(cycle.p,cycle.pin,stage,cycle.i.RunID,original,cycle.outcome))}
		intents=addIntent(t,intents,cycle.i,fsaintent.TerminalObserved,repeat("e",64))
		checkDecision(t,intents,cycle.i,fsaintent.NoRedispatchTerminal)
		if _,err:=fsaintent.Append(intents,cycle.i,fsaintent.DispatchRisk,"");err==nil{
			t.Fatal("terminal primary allowed to replay")
		}
	}
	advanceSynthetic(t,backend,archive,identity,priv)
	reopened,err:=privatearchive.Open(root);if err!=nil{t.Fatal(err)}
	journal,err:=reopened.Load();if err!=nil{t.Fatal(err)}
	for _,c:=range []struct{i fsaintent.Intent;want string}{{wi,"SUPPORTED"},{yi,"NEGATIVE"}}{
		found:=false
		for _,row:=range journal.Entries{
			if row.Event.Lane==c.i.Lane&&row.Event.ExperimentID==c.i.CandidateID&&
				row.Event.Kind==researchlog.FinalArchive {
				found=true
				if row.Event.Outcome!=c.want{t.Fatal("negative/supported classification drifted")}
				if _,err:=reopened.ReadOriginal(row.Event.OriginalEvidenceSHA256);err!=nil{t.Fatal("original lost",err)}
			}
		}
		if !found{t.Fatalf("%s missing final archive",c.i.Lane)}
	}
	// Prepare both next candidates with fresh disjoint cohorts and a snapshot
	// that retains BOTH prior lanes. This is NOT automatic candidate selection.
	w2,w2p:=freeze(t,"Wingless","W_002","c","3","7","b",12)
	y2,y2p:=freeze(t,"Yggdrasil","Y_002","d","4","8","c",13)
	for _,c:=range []struct{p eligibility.Frozen;pin string}{{w2,w2p},{y2,y2p}}{
		for _,stage:=range []researchlog.Kind{
			researchlog.Hypothesis,researchlog.Preregister,researchlog.SourceQualified,
		}{addEvent(t,archive,scientificEvent(c.p,c.pin,stage,0,"",""))}
	}
	advanceSynthetic(t,backend,archive,identity,priv)
	complete,pin:=ledger(t,[]string{w.CohortSHA256,y.CohortSHA256},
		[]eligibility.StartRecord{{FrozenSHA256:wp,State:"TERMINAL"},{FrozenSHA256:yp,State:"TERMINAL"}})
	preflight(t,backend,archive,identity,w2,w2p,complete,pin)
	preflight(t,backend,archive,identity,y2,y2p,complete,pin)
	w2i,y2i:=intentOf(w2,w2p,8003),intentOf(y2,y2p,8004)
	intents=addIntent(t,intents,w2i,fsaintent.Prepared,"")
	intents=addIntent(t,intents,y2i,fsaintent.Prepared,"")
	checkDecision(t,intents,w2i,fsaintent.PreparedOnly)
	checkDecision(t,intents,y2i,fsaintent.PreparedOnly)
	// The predecessor's cohort remains consumed even if a new candidate
	// changes its ID, source or budget.
	duplicate:=w2;duplicate.CohortSHA256=w.CohortSHA256
	duplicatedPin,err:=eligibility.Fingerprint(duplicate);if err!=nil{t.Fatal(err)}
	bad:=fsaadmission.Evidence{
		Frozen:duplicate,FrozenPinSHA256:duplicatedPin,
		Ledger:complete,LedgerPinSHA256:pin,LedgerGeneration:3,CompleteAllLanes:true,
		ExperimentGeneration:3,
	}
	if decision,err:=fsaadmission.AssessArchived(context.Background(),backend,archive,identity,bad);
		err==nil||decision!=""{t.Fatal("historically consumed cohort accepted")}
	latest,err:=fsatrust.Recover(context.Background(),backend,archive,identity)
	if err!=nil{t.Fatal(err)}
	if d,err:=startrecovery.Inspect(reloaded(t,reopened),startrecovery.TrustedHead{
		Sequence:latest.Sequence,SHA256:latest.HeadSHA256,IndependentlyAuthenticated:true,
	},w2.Lane,w2.CandidateID);err!=nil||d!=startrecovery.NoPriorStart{
		t.Fatalf("successor start reconciliation: %s %v",d,err)
	}
	// Negative fault injection: independently pinned head and raw originals
	// MUST reject deletion without silently recovering or replaying science.
	for _,row:=range journal.Entries{
		if row.Event.Kind==researchlog.FinalArchive&&row.Event.Lane=="Yggdrasil"{
			if err:=os.Remove(filepath.Join(root,"originals",row.Event.OriginalEvidenceSHA256+".raw"));err!=nil{t.Fatal(err)}
			break
		}
	}
	if _,err:=fsatrust.Recover(context.Background(),backend,reopened,identity);err==nil{
		t.Fatal("lost negative original was not detected")
	}
	if backend.casCount!=3{t.Fatalf("unexpected synthetic checkpoint count=%d",backend.casCount)}
}
func reloaded(t *testing.T,s *privatearchive.Store)researchlog.Journal{
	t.Helper();j,err:=s.Load();if err!=nil{t.Fatal(err)};return j
}
