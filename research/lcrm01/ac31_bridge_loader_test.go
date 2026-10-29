package main

import (
 "bytes"
 "encoding/base64"
 "encoding/json"
 "strings"
 "testing"
 native "github.com/spoonman136668-ai/Wingless/research/native/itd02/dk15"
)

func mockPublic(mission string,front int)json.RawMessage{
 img:=make([][][]int,7)
 for i:=0;i<7;i++{
  img[i]=make([][]int,7)
  for j:=0;j<7;j++{img[i][j]=[]int{1,0,0}}
 }
 img[3][5]=[]int{front,0,0}
 b,_:=json.Marshal(map[string]any{"image":img,"direction":0,"mission":mission})
 return b
}
func request(t *testing.T,a **native.Actor,q Request)Reply{
 t.Helper()
 r,_:=process(a,q)
 if !r.OK{t.Fatalf("source-only bridge operation %s unexpectedly rejected: %s",q.Op,r.Error)}
 return r
}
func TestAC31ExactNativeFitVersusFullActorColdCheckpointTypes(t *testing.T){
 var original="use the key to open the door and then get to the goal"
 first:=mockPublic(original,1)
 next:=mockPublic(original,4)
 a:=native.New()
 // Train a single original source-public FIT sample without any environment.
 fit:=request(t,&a,Request{Op:"learn",Before:first,After:next,Action:5,Reward:0})
 if fit.Updates!=1{t.Fatal("source-only fitted original counter lost")}
 sourceFIT:=request(t,&a,Request{Op:"snapshot_parent"}).State
 b:=native.New()
 loaded:=request(t,&b,Request{Op:"load_parent",State:sourceFIT})
 if loaded.Updates!=1{t.Fatal("exact original FIT state not restored")}
 if request(t,&b,Request{Op:"snapshot_parent"}).State!=sourceFIT{
  t.Fatal("original frozen fit checkpoint mutated")
 }
 // The historical old checkpoint is NOT a complete DK15 actor.
 c:=native.New()
 oldReply,_:=process(&c,Request{Op:"load",State:sourceFIT})
 if oldReply.OK{t.Fatal("full actor loader improperly accepted a fit-only DK13 checkpoint")}
 // Now begin a genuine distinct mission and store original-selected feedback.
 unlock:=mockPublic("open the door",1)
 after:=mockPublic("open the door",4)
 started:=request(t,&b,Request{Op:"begin",Before:unlock})
 if started.Mode!="NATIVE_NEW_MISSION_PUBLIC_SELECTED"{t.Fatal("mission spoofed or old actor used")}
 chosen:=request(t,&b,Request{Op:"choose"})
 if chosen.Action==nil||*chosen.Action<0||*chosen.Action>6{t.Fatal("invalid native action")}
 request(t,&b,Request{Op:"commit",Action:*chosen.Action})
 feedback:=request(t,&b,Request{Op:"feedback",Action:*chosen.Action,After:after,Reward:0})
 if feedback.Live!=1||feedback.Mode!="NATIVE_NEW_MISSION_PUBLIC_SELECTED"{
  t.Fatal("actual selected consequence missing")
 }
 actorBlob:=request(t,&b,Request{Op:"snapshot"}).State
 // This is the cold-check that failed when full actor checkpoint was
 // interpreted by DK13-only loader solely because fresh Actor.Mode == "".
 d:=native.New()
 restored:=request(t,&d,Request{Op:"load",State:actorBlob})
 if restored.Live!=1||restored.Mode!="NATIVE_NEW_MISSION_PUBLIC_SELECTED"{
  t.Fatal("full native actor checkpoint not restored")
 }
 if request(t,&d,Request{Op:"snapshot"}).State!=actorBlob{
  t.Fatal("genuine source-mission actor checkpoint not byte-identical")
 }
 if request(t,&d,Request{Op:"snapshot_parent"}).State!=sourceFIT{
  t.Fatal("source-only restored new actor altered old original FIT")
 }
}
func TestAC31OriginalDoorKeyNativePathColdAndNoUnknownMissionProjection(t *testing.T){
 old:="use the key to open the door and then get to the goal"
 a:=native.New()
 started:=request(t,&a,Request{Op:"begin",Before:mockPublic(old,1)})
 if started.Mode!="ORIGINAL_DOORKEY_UNCHANGED"{t.Fatal("old DoorKey actor not used")}
 q:=request(t,&a,Request{Op:"choose"})
 if q.Action==nil{t.Fatal("old original native decision missing")}
 request(t,&a,Request{Op:"commit",Action:*q.Action})
 request(t,&a,Request{Op:"feedback",Action:*q.Action,
  After:mockPublic(old,4),Reward:0})
 data:=request(t,&a,Request{Op:"snapshot"}).State
 b:=native.New()
 request(t,&b,Request{Op:"load",State:data})
 if request(t,&b,Request{Op:"snapshot"}).State!=data{
  t.Fatal("historical native action state fails cold restore")
 }
 bad:=native.New()
 x,_:=process(&bad,Request{Op:"begin",Before:json.RawMessage(strings.Replace(
  string(mockPublic("open the door",1)), "open the door", "open the door",1))})
 if !x.OK{t.Fatal("genuine unaltered unlock mission rejected")}
 if bad.Boundary.Current.Mission!="open the door"{t.Fatal("genuine source mission rewritten")}
}
func TestAC31ForgedSourceFeedbackAndCheckpointRejected(t *testing.T){
 a:=native.New()
 source:=mockPublic("open the door",1)
 request(t,&a,Request{Op:"begin",Before:source})
 request(t,&a,Request{Op:"commit",Action:2})
 r,_:=process(&a,Request{Op:"feedback",Action:3,After:source,Reward:0})
 if r.OK{t.Fatal("wrong source-selected action accepted")}
 raw:=request(t,&a,Request{Op:"snapshot"}).State
 payload,e:=base64.StdEncoding.DecodeString(raw);if e!=nil{t.Fatal(e)}
 corrupted:=append(bytes.Clone(payload),byte(0))
 b:=native.New()
 r,_=process(&b,Request{Op:"load",State:base64.StdEncoding.EncodeToString(corrupted)})
 if r.OK{t.Fatal("corrupted full native checkpoint accepted")}
}
