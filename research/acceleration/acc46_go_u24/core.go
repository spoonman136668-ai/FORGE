package main

import (
 "encoding/binary"
 "hash"
)

const (
 schema="forge.acc46.original-u24.cellular-learning.nativego.v1"
 cells=64
 neighborhoods=8
 fitStates=256
 testStates=256
 episodes=256
)
var modes=[]string{"GLOBAL_FREQ","REGION_FREQ","CELL_FREQ","LOCAL_CA"}
var regimes=[]string{"UNIFORM","FOUR_REGIONS","RULE_SHIFT"}
var seeds=[]uint64{96301,96303,96307,96309,96311}

func mix(v uint64)uint64{
 v+=0x9e3779b97f4a7c15
 v=(v^(v>>30))*0xbf58476d1ce4e5b9
 v=(v^(v>>27))*0x94d049bb133111eb
 return v^(v>>31)
}
func eligible(xs []string,s string)bool{for _,v:=range xs{if v==s{return true}};return false}
func episodeBase(seed uint64,episode int)uint64{
 return mix(seed^uint64(episode)*0x9e3779b97f4a7c15^0x1dc6e99a83b2f041)
}
func fitState(base uint64,step int)uint64{
 pos:=mix(base^0x66bfa97102c3d58e^uint64(step)*0xa0761d6478bd642f)%cells
 return (uint64(1)<<pos)|(uint64(1)<<((pos+1)%cells))
}
func heldoutState(base uint64,step int)uint64{
 return mix(base^0x90a3cef1b624d578^uint64(step)*0xe7037ed1a0b428db)
}
type rules struct{Old,New [4]uint8}
func makeRules(base uint64)rules{
 var r rules
 for g:=0;g<4;g++{
  r.Old[g]=uint8(mix(base^0x8bde31f247a96055^uint64(g)*0xbf58476d1ce4e5b9))
  r.New[g]=uint8(mix(base^0x47e526b3f19a68cd^uint64(g)*0x94d049bb133111eb))
 }
 return r
}
func neighborhood(state uint64,cell int)int{
 l:=int((state>>uint((cell+cells-1)%cells))&1)
 m:=int((state>>uint(cell))&1)
 r:=int((state>>uint((cell+1)%cells))&1)
 return (l<<2)|(m<<1)|r
}
func truth(ruleset rules,mode string,step int,cell,pattern int)uint8{
 region:=cell/16
 var table uint8
 if mode=="UNIFORM"{table=ruleset.Old[0]}else if mode=="RULE_SHIFT"&&step>=fitStates/2{table=ruleset.New[region]}else{table=ruleset.Old[region]}
 return (table>>uint(pattern))&1
}
func saturate(n *uint16){if *n<^uint16(0){*n++}}
func addHash(h hash.Hash,tag byte,x uint64){
 var b [9]byte;b[0]=tag;binary.LittleEndian.PutUint64(b[1:],x);_,_=h.Write(b[:])
}
type learner struct{
 Mode string
 Global [8][2]uint16
 Region [4][8][2]uint16
 Cell [64][8][2]uint16
}
func newLearner(mode string)*learner{return &learner{Mode:mode}}
func(m *learner)Learn(cell,pattern int,outcome uint8){
 switch m.Mode{
 case "GLOBAL_FREQ":saturate(&m.Global[pattern][outcome])
 case "REGION_FREQ":saturate(&m.Region[cell/16][pattern][outcome])
 case "CELL_FREQ","LOCAL_CA":saturate(&m.Cell[cell][pattern][outcome])
 }
}
func majority(a,b uint32)uint8{if b>a{return 1};return 0}
func(m *learner)Predict(cell,pattern int)uint8{
 switch m.Mode{
 case "GLOBAL_FREQ":c:=m.Global[pattern];return majority(uint32(c[0]),uint32(c[1]))
 case "REGION_FREQ":c:=m.Region[cell/16][pattern];return majority(uint32(c[0]),uint32(c[1]))
 case "CELL_FREQ":c:=m.Cell[cell][pattern];return majority(uint32(c[0]),uint32(c[1]))
 case "LOCAL_CA":
  a:=m.Cell[cell][pattern]
  l:=m.Cell[(cell+cells-1)%cells][pattern]
  r:=m.Cell[(cell+1)%cells][pattern]
  return majority(4*uint32(a[0])+uint32(l[0])+uint32(r[0]),4*uint32(a[1])+uint32(l[1])+uint32(r[1]))
 }
 return 0
}
func(m *learner)LogicalBytes()int{
 switch m.Mode{
 case "GLOBAL_FREQ":return 32
 case "REGION_FREQ":return 128
 default:return 2048
 }
}
func(m *learner)MessageReadsPerPrediction()int{
 if m.Mode=="LOCAL_CA"{return 4}
 return 0
}
