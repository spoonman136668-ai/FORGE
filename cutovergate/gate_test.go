package cutovergate

import(
 "crypto/ed25519"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "os"
 "path/filepath"
 "strings"
 "testing"

 "github.com/spoonman136668-ai/forge/ckbcustody"
 "github.com/spoonman136668-ai/forge/fsahead"
 "github.com/spoonman136668-ai/forge/fsaremote"
 "github.com/spoonman136668-ai/forge/lanetakeover"
)
func key(s string)ed25519.PrivateKey{
 h:=sha256.Sum256([]byte("TEST ONLY "+s))
 return ed25519.NewKeyFromSeed(h[:])
}
func write(t *testing.T,path string,obj any){
 t.Helper();b,e:=json.Marshal(obj);if e!=nil{t.Fatal(e)}
 if e=os.WriteFile(path,append(b,'\n'),0600);e!=nil{t.Fatal(e)}
}
func signCustody(t *testing.T,c lanetakeover.Custody,k ed25519.PrivateKey)lanetakeover.SignedCustody{
 t.Helper();data,e:=json.Marshal(c);if e!=nil{t.Fatal(e)}
 sig:=ed25519.Sign(k,append([]byte("FORGE_EXISTING_LANE_CUSTODY_V1\n"),data...))
 return lanetakeover.SignedCustody{Custody:c,SignatureHex:hex.EncodeToString(sig)}
}
func signJoin(t *testing.T,c JointObservation,k ed25519.PrivateKey)SignedJoint{
 t.Helper();data,e:=json.Marshal(c);if e!=nil{t.Fatal(e)}
 sig:=ed25519.Sign(k,append([]byte(domain),data...))
 return SignedJoint{Observation:c,SignatureHex:hex.EncodeToString(sig)}
}
func ckbState(t *testing.T)(string,map[string]string){
 t.Helper();root:=t.TempDir()
 specs:=[]struct{generation,name,schema string}{
 {"S09","s09-first-use-consumed.v1.json","ckb.r216-s21-s09-first-use-permanent-ledger.v1"},
 {"S10","s10-first-use-consumed.v1.json","ckb.r216-s26-s10-first-use-permanent-ledger.v1"},
 {"S11","s11-first-use-consumed.v1.json","ckb.r216-s33-s11-first-use-permanent-ledger.v1"},
 {"S12","s12-first-use-consumed.v1.json","ckb.r216-s44-s12-first-use-permanent-ledger.v1"},
 {"S13","s13-first-use-consumed.v1.json","ckb.r216-s52-s13-first-use-permanent-ledger.v1"},
 {"S14","s14-first-use-consumed.v1.json","ckb.r216-s71-s14-first-use-permanent-ledger.v1"},
 }
 pins:=map[string]string{}
 prior:=map[string]string{}
 for _,s:=range specs{
  doc:=map[string]any{"generation":s.generation,"schema":s.schema,"replay_authorized":false}
  if s.generation=="S09"{doc["consumption"]="IRREVERSIBLE_FIRST_USE_INTENT_CONSUMED";doc["scientific_acceptance"]=false
  }else{doc["state"]="IRREVERSIBLE_FIRST_USE_INTENT_CONSUMED";doc["scientific_accepted"]=false}
  if s.generation=="S12"{
   doc["prereg_git_blob"]="220cffa155d1277715078b55ffacd057b8229737"
   doc["production_authority"]=false;doc["broker_access"]=false;doc["ktrade_access"]=false
  }
  if s.generation=="S13"{doc["prereg_git_blob"]="645700167176f176073a411b154a697554cdf1db"}
  if s.generation=="S14"{
   doc["prereg_git_blob"]="05d2bf3bf1f488b605b54037a94b9ca3cffc0e9c"
   doc["scientific_result"]="UNOBSERVED";doc["wake_run_id"]=uint64(38281455598)
   doc["wake_main_sha"]=strings.Repeat("a",40)
   doc["controller_sha"]=strings.Repeat("b",40)
   doc["production_authority"]=false;doc["broker_access"]=false
   doc["ktrade_access"]=false;doc["accepted_ref_mutation"]=false
   doc["prior_first_use_sha256"]=prior
  }
  path:=filepath.Join(root,s.name);write(t,path,doc)
  raw,e:=os.ReadFile(path);if e!=nil{t.Fatal(e)}
  d:=sha256.Sum256(raw);hash:=hex.EncodeToString(d[:])
  pins[s.generation]=hash
  if s.generation!="S14"{prior[s.name]=hash}
 }
 return root,pins
}
func fixture(t *testing.T)Input{
 t.Helper()
 oldRoot,pins:=ckbState(t)
 inventory,e:=ckbcustody.Inspect(oldRoot);if e!=nil{t.Fatal(e)}
 legacyKey:=key("legacy collector")
 forgeKey:=key("forge original grant")
 witnessKey:=key("fsa witness")
 authorityKey:=key("fsa authority")
 lanecustody:=[]lanetakeover.SignedCustody{}
 plan:=lanetakeover.Plan{TrustedCollectorKey:legacyKey.Public().(ed25519.PublicKey),
  MinimumObservationSequence:17}
 for i,lane:=range []string{"Wingless","Yggdrasil"}{
  e:=lanetakeover.ExpectedLane{Lane:lane,SourceRepo:"spoonman136668-ai/"+lane,
   SourceCommitSHA:strings.Repeat(string(rune('a'+i)),40),
   ExistingQueueID:"legacy-queue-"+lane,ExistingLaneID:"legacy-lane-"+lane,
   LegacyAuthorityID:"sole-ckb-plane-owner"}
  if i==0{plan.Wingless=e}else{plan.Yggdrasil=e}
  custody:=lanetakeover.Custody{
   Schema:lanetakeover.Schema,Lane:lane,SourceRepo:e.SourceRepo,
   SourceCommitSHA:e.SourceCommitSHA,ExistingQueueID:e.ExistingQueueID,
   ExistingLaneID:e.ExistingLaneID,LegacyAuthorityID:e.LegacyAuthorityID,
   LegacyJournalHeadSHA256:strings.Repeat(string(rune('c'+i)),64),
   LegacyConsumedLedgerSHA256:strings.Repeat(string(rune('e'+i)),64),
   LegacyFrozenWorkSHA256:strings.Repeat(string(rune('1'+i)),64),
   LastLegacyOwnerReleaseSHA256:strings.Repeat(string(rune('3'+i)),64),
   ObservationSequence:17,ActiveLeaseCount:0,UncertainDispatchCount:0,
  }
  lanecustody=append(lanecustody,signCustody(t,custody,legacyKey))
 }
 custodyResult,e:=lanetakeover.Preflight(plan,lanecustody);if e!=nil{t.Fatal(e)}
 join:=JointObservation{Schema:Schema,
  InventorySHA256:inventory.InventorySHA256,
  S14LedgerSHA256:inventory.Generations[5].SHA256,
  WinglessCustodySHA256:custodyResult.WinglessCustodySHA256,
  YggdrasilCustodySHA256:custodyResult.YggdrasilCustodySHA256,
  ObservedAtUnix:1300,LegacyAuthorityID:"sole-ckb-plane-owner",
  OriginalReplayAuthorized:false}
 anchor:=fsahead.Anchor{ArchiveID:strings.Repeat("a",64),
  KeyID:"authority-r1",PublicKey:authorityKey.Public().(ed25519.PublicKey),
  AuthorityEpoch:7,Sequence:1,HeadSHA256:strings.Repeat("9",64)}
 pin:=fsaremote.Pin{ArchiveID:anchor.ArchiveID,KeyID:anchor.KeyID,
  PublicKey:anchor.PublicKey,AuthorityEpoch:anchor.AuthorityEpoch,
  BindingSHA256:strings.Repeat("b",64),WitnessPublicKey:witnessKey.Public().(ed25519.PublicKey),
  MinimumRevision:10}
 head:=fsaremote.WitnessHead{Schema:fsaremote.WitnessSchema,
  Domain:fsaremote.WitnessDomain,ArchiveID:anchor.ArchiveID,
  KeyID:anchor.KeyID,AuthorityEpoch:anchor.AuthorityEpoch,
  BindingSHA256:pin.BindingSHA256,Sequence:anchor.Sequence,HeadSHA256:anchor.HeadSHA256,Revision:11}
 body,e:=json.Marshal(head);if e!=nil{t.Fatal(e)}
 sig:=ed25519.Sign(witnessKey,append([]byte("FORGE-FSA-INDEPENDENT-HIGHWATER-V1\n"),body...))
 newDir:=filepath.Join(t.TempDir(),"forge-firstuse")
 if e=os.Mkdir(newDir,0700);e!=nil{t.Fatal(e)}
 return Input{
  LegacyStateDirectory:oldRoot,LegacySHA256Pins:pins,LegacyPlan:plan,
  LegacyLaneCustody:lanecustody,LegacyJoin:signJoin(t,join,legacyKey),
  NowUnix:1301,FSAAnchor:anchor,FSAPin:pin,
  FSAWitness:fsaremote.SignedWitness{Head:head,SignatureHex:hex.EncodeToString(sig)},
  ForgeOriginalLedgerDirectory:newDir,ForgeOriginalGrantPublicKey:forgeKey.Public().(ed25519.PublicKey),
 }
}
func TestSignedCKBCustodyAndIndependentFSAAreNotCutover(t *testing.T){
 in:=fixture(t)
 report,e:=Assess(in);if e!=nil{t.Fatal(e)}
 if report.Mode!=Status||report.CutoverAuthorized||report.ScienceActivated||
  report.OriginalReplayAuthorized||report.ForgeOriginalReservationCount!=0||
  report.LegacyInventorySHA256==""||len(report.Pending)!=6{
  t.Fatal("advisory-only report violated",report)
 }
 if _,e=os.Stat(filepath.Join(in.ForgeOriginalLedgerDirectory,"00000000000000000001.json"));!os.IsNotExist(e){
  t.Fatal("read-only evaluator wrote original reservation")
 }
}
func TestCorruptOrMissingLegacyCustodyAlwaysBlocks(t *testing.T){
 tests:=map[string]func(*Input){
  "S14 missing even if old issuer failed":func(i *Input){_ = os.Remove(filepath.Join(i.LegacyStateDirectory,"s14-first-use-consumed.v1.json"))},
  "S14 pinned digest drift":func(i *Input){i.LegacySHA256Pins["S14"]=strings.Repeat("f",64)},
  "old lease active":func(i *Input){i.LegacyLaneCustody[0].Custody.ActiveLeaseCount=1},
  "changed queue":func(i *Input){i.LegacyLaneCustody[0].Custody.ExistingQueueID="replacement-queue"},
  "swapped CKB release hash":func(i *Input){i.LegacyJoin.Observation.WinglessCustodySHA256=strings.Repeat("0",64)},
  "expired independent join":func(i *Input){i.NowUnix=1602},
  "reused trust roots":func(i *Input){i.ForgeOriginalGrantPublicKey=i.FSAPin.WitnessPublicKey},
  "FSA witness revision rollback":func(i *Input){i.FSAPin.MinimumRevision=12},
  "witness forgery":func(i *Input){i.FSAWitness.Head.BindingSHA256=strings.Repeat("c",64)},
  "FORGE first-use archive nonempty":func(i *Input){_ = os.WriteFile(filepath.Join(i.ForgeOriginalLedgerDirectory,"00000000000000000001.json"),[]byte("not-authenticated"),0600)},
 }
 for name,change:=range tests{t.Run(name,func(t *testing.T){
  in:=fixture(t);change(&in)
  if result,e:=Assess(in);e==nil{t.Fatalf("unsafe cutover observation accepted: %+v",result)}
 })}
}
