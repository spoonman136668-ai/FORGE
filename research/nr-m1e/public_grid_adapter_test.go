package nrm1e

import (
    "encoding/json"
    "math"
    "reflect"
    "testing"
)

func TestNativePublicGridRoundTripAllPublicFields(t *testing.T) {
    samples:=[]NativePublicGrid{
        {X:0,Y:64,GoalX:64,GoalY:0,Direction:3,FrontBlocked:true},
        {X:12,Y:15,GoalX:18,GoalY:21,Direction:1,FrontBlocked:false},
        {X:64,Y:64,GoalX:0,GoalY:0,Direction:0,FrontBlocked:true},
    }
    for _,input:=range samples {
        packed,err:=EncodeNativeGrid(input)
        if err!=nil {t.Fatal(err)}
        recovered,err:=DecodeNativeGrid(packed)
        if err!=nil {t.Fatal(err)}
        if recovered!=input {t.Fatalf("lost source-public field: in=%+v got=%+v",input,recovered)}
    }
}

func TestNativePublicConsequenceRoundTrip(t *testing.T) {
    before:=NativePublicGrid{X:1,Y:2,GoalX:10,GoalY:11,Direction:3,FrontBlocked:true}
    consequence:=NativePublicConsequence{
        After:NativePublicGrid{X:2,Y:2,GoalX:10,GoalY:11,Direction:2,FrontBlocked:false},
        Reward:0.25, Terminal:false,Truncated:true,
    }
    event,err:=ConvertObservedPublic(before,2,consequence)
    if err!=nil {t.Fatal(err)}
    b,a,c,err:=DecodeObservedPublic(event)
    if err!=nil {t.Fatal(err)}
    if b!=before || a!=2 || c!=consequence {
        t.Fatalf("lossy public transition before=%+v action=%d consequence=%+v",b,a,c)
    }
    serialized,err:=json.Marshal(consequence)
    if err!=nil {t.Fatal(err)}
    var rehydrated NativePublicConsequence
    if err:=json.Unmarshal(serialized,&rehydrated);err!=nil {t.Fatal(err)}
    if !reflect.DeepEqual(rehydrated,consequence) {t.Fatal("public outcome wire mismatch")}
}

func TestNativeGridLosslessAcrossLargeFinitePublicDomain(t *testing.T) {
    // Development contract only: exhaustive boundary axes + orientation/block bit.
    xs:=[]int{0,1,31,63,64}
    for _,x:=range xs {for _,y:=range xs {for _,gx:=range xs {for _,gy:=range xs {
        for direction:=0;direction<4;direction++ {for _,blocked:=range []bool{false,true} {
            original:=NativePublicGrid{x,y,gx,gy,direction,blocked}
            encoded,err:=EncodeNativeGrid(original);if err!=nil {t.Fatal(err)}
            actual,err:=DecodeNativeGrid(encoded);if err!=nil {t.Fatal(err)}
            if actual!=original {t.Fatalf("lost native public field %+v %+v",original,actual)}
        }}
    }}}}
}

func TestNativeAdapterFailsClosedOnInvalidPublicEvidence(t *testing.T) {
    validGrid:=NativePublicGrid{X:1,Y:2,GoalX:3,GoalY:4,Direction:1}
    event:=NativePublicConsequence{After:validGrid,Reward:0.5}
    if _,err:=ConvertObservedPublic(validGrid,3,event);err==nil {t.Fatal("invalid action accepted")}
    if _,err:=ConvertObservedPublic(validGrid,-1,event);err==nil {t.Fatal("negative action accepted")}
    event.Reward=25
    if _,err:=ConvertObservedPublic(validGrid,1,event);err==nil {t.Fatal("unqualified reward units accepted")}
    event.Reward=math.NaN()
    if _,err:=ConvertObservedPublic(validGrid,1,event);err==nil {t.Fatal("NaN reward accepted")}
    event.Reward=0.5
    bad:=validGrid;bad.GoalX=65
    if _,err:=ConvertObservedPublic(bad,1,event);err==nil {t.Fatal("hidden/out-of-range grid accepted")}
    bad=validGrid;bad.Direction=4
    if _,err:=ConvertObservedPublic(bad,1,event);err==nil {t.Fatal("non-native orientation accepted")}
    samples:=[][6]float64{
        {1,2,3,4,0,0.5},
        {1,2,3,4,4,1},
        {1,2,3,4,1,math.NaN()},
        {1,2,3,math.Inf(1),1,0},
        {1,2,-1,4,1,0},
        {1,2,1e40,4,1,0},
    }
    for _,v:=range samples {
        if _,err:=DecodeNativeGrid(v);err==nil {t.Fatalf("accepted invalid six-field public grid: %+v",v)}
    }
}
