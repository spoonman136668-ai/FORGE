package nrm1e

import (
    "errors"
    "math"
)

// NativePublicGrid is a source-pinned wire-shape mirror of
// Wingless research/native/itd02/r1/policy.go at
// 01ca1471b60616fe323dae2ecbc0f16d053b38f3 (blob 8d1845d82dd8578a709b00e8841bdc5edc8dbc10).
// This is ONLY an offline compatibility contract; it does not import or run
// native Wingless or its original MiniGrid source.
type NativePublicGrid struct {
    X int `json:"x"`
    Y int `json:"y"`
    GoalX int `json:"goal_x"`
    GoalY int `json:"goal_y"`
    Direction int `json:"direction"`
    FrontBlocked bool `json:"front_blocked"`
}

// NativePublicConsequence mirrors Wingless's separately source-owner-operated
// public outcome. Its StepPublic call is NOT implemented or dispatched here.
type NativePublicConsequence struct {
    After NativePublicGrid `json:"after"`
    Reward float64 `json:"reward"`
    Terminal bool `json:"terminal"`
    Truncated bool `json:"truncated"`
}

func allowedNativeGrid(g NativePublicGrid) bool {
    return g.X>=0 && g.X<=64 && g.Y>=0 && g.Y<=64 &&
        g.GoalX>=0 && g.GoalX<=64 && g.GoalY>=0 && g.GoalY<=64 &&
        g.Direction>=0 && g.Direction<=3
}

// EncodeNativeGrid is a bijection over the source-public grid domain: no
// location, goal, orientation, or front-obstacle bit may be silently removed.
func EncodeNativeGrid(g NativePublicGrid) ([6]float64,error) {
    if !allowedNativeGrid(g) { return [6]float64{},errors.New("INVALID_NATIVE_PUBLIC_GRID") }
    blocked:=0.
    if g.FrontBlocked { blocked=1 }
    return [6]float64{float64(g.X),float64(g.Y),float64(g.GoalX),float64(g.GoalY),float64(g.Direction),blocked},nil
}

func DecodeNativeGrid(v [6]float64) (NativePublicGrid,error) {
    for _,x:=range v {
        if math.IsNaN(x)||math.IsInf(x,0)||x!=math.Trunc(x) {
            return NativePublicGrid{},errors.New("NONCANONICAL_PUBLIC_GRID")
        }
    }
    if v[5]!=0 && v[5]!=1 {return NativePublicGrid{},errors.New("NONCANONICAL_BLOCKED_BIT")}
    g:=NativePublicGrid{
        X:int(v[0]),Y:int(v[1]),GoalX:int(v[2]),GoalY:int(v[3]),
        Direction:int(v[4]),FrontBlocked:v[5]==1,
    }
    if !allowedNativeGrid(g) {return NativePublicGrid{},errors.New("PUBLIC_GRID_OUT_OF_RANGE")}
    return g,nil
}

// ConvertObservedPublic accepts the native learner's already-selected action
// and the source owner's already-returned public consequence. It does not
// choose actions, step environments, or synthesize success or termination.
func ConvertObservedPublic(before NativePublicGrid, action int, consequence NativePublicConsequence) (Event,error) {
    if action<0 || action>2 {return Event{},errors.New("INVALID_PUBLIC_ACTION")}
    beforeData,err:=EncodeNativeGrid(before)
    if err!=nil {return Event{},err}
    afterData,err:=EncodeNativeGrid(consequence.After)
    if err!=nil {return Event{},err}
    event:=Event{
        Before:beforeData,After:afterData,Action:uint8(action),
        Reward:consequence.Reward,Terminal:consequence.Terminal,
        Truncated:consequence.Truncated,
    }
    // The retention kernel's reward range is intentionally narrower than
    // Wingless's generic reward interface. Fail closed on unmatched units;
    // the source owner must explicitly qualify any reward rescaling.
    if !valid(event) {return Event{},errors.New("REWARD_UNIT_OR_EVENT_INVALID")}
    return event,nil
}

// DecodeObservedPublic restores every input field for a strict round-trip.
// It is intended for source-free adapter compatibility/property tests only.
func DecodeObservedPublic(event Event) (NativePublicGrid,int,NativePublicConsequence,error) {
    if !valid(event) {return NativePublicGrid{},0,NativePublicConsequence{},errors.New("INVALID_PUBLIC_EVENT")}
    before,err:=DecodeNativeGrid(event.Before)
    if err!=nil {return NativePublicGrid{},0,NativePublicConsequence{},err}
    after,err:=DecodeNativeGrid(event.After)
    if err!=nil {return NativePublicGrid{},0,NativePublicConsequence{},err}
    return before,int(event.Action),NativePublicConsequence{
        After:after,Reward:event.Reward,Terminal:event.Terminal,
        Truncated:event.Truncated,
    },nil
}
