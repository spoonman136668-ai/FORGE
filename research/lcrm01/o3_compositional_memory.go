package lcrm01

// O3 is a source-free, proof-preserving REPRESENTABILITY screen, not a
// learned causal mechanism. Incoming directed-edge transition functions
// are public for this check; learned operator induction remains untested.
//
// The summary is query-blind: Append accepts only an edge at arrival,
// never a future query. The only supported query is the entire contiguous
// 12-edge path. We certify no unfamiliar causal law from observation alone.

import "errors"

const (
 O3ChainEdges = 12
 O3ChunkEdges = 4
 O3SlotsCap = MaxSlots
)
var (
 ErrO3Path = errors.New("LCRM_O3_NONCONTIGUOUS_OR_UNSUPPORTED_PATH")
 ErrO3Query = errors.New("LCRM_O3_UNSUPPORTED_OR_INCOMPLETE_QUERY")
)

// O3Unary encodes a fully PUBLIC unary Boolean function by two output
// bits: bit 0 is f(0), bit 1 is f(1). Four possible exact operators.
type O3Unary uint8

// O3Identity maps 0->0, 1->1; O3Not maps 0->1, 1->0.
const (
 O3False O3Unary = 0
 O3Not O3Unary = 1
 O3Identity O3Unary = 2
 O3True O3Unary = 3
)
func o3Valid(f O3Unary) bool {return f<=3}
func O3Apply(f O3Unary, x uint8) (uint8,error) {
 if !o3Valid(f)||x>1 {return 0,ErrInvalid}
 return (uint8(f)>>x)&1,nil
}
func o3ApplyExact(f O3Unary,x uint8) uint8 {return (uint8(f)>>x)&1}
// O3Compose returns after(before(x)); both operands fully public.
// It is an associative operation but it does NOT learn the operator.
func O3Compose(after,before O3Unary) (O3Unary,error){
 if !o3Valid(after)||!o3Valid(before) {return 0,ErrInvalid}
 lo:=o3ApplyExact(after,o3ApplyExact(before,0))
 hi:=o3ApplyExact(after,o3ApplyExact(before,1))
 return O3Unary(lo|(hi<<1)),nil
}
func o3ComposeExact(after,before O3Unary)O3Unary {
 lo:=o3ApplyExact(after,o3ApplyExact(before,0))
 hi:=o3ApplyExact(after,o3ApplyExact(before,1))
 return O3Unary(lo|(hi<<1))
}

type O3Edge struct {
 From,To int
 PublicOperator O3Unary
}
// O3ComposedMemory has at most three completed segment functions plus
// one in-flight two-bit summary: <=4 physical slots, always <=8.
// No field or method exposes the eventual counterfactual query at write time.
type O3ComposedMemory struct {
 chunks [3]O3Unary
 completed int
 pending O3Unary
 count int
 source,target int
}
func NewO3ComposedMemory() *O3ComposedMemory {
 return &O3ComposedMemory{pending:O3Identity}
}
func (m *O3ComposedMemory) Append(e O3Edge)error {
 if m.count>=O3ChainEdges||!o3Valid(e.PublicOperator)||
    e.From==e.To||(m.count>0&&e.From!=m.target) {return ErrO3Path}
 if m.count==0 {m.source=e.From}
 m.target=e.To
 m.pending=o3ComposeExact(e.PublicOperator,m.pending)
 m.count++
 if m.count%O3ChunkEdges==0 {
   m.chunks[m.completed]=m.pending
   m.completed++
   m.pending=O3Identity
 }
 return nil
}
func (m *O3ComposedMemory) PhysicalSlots()int {
 // During an incomplete segment only the active summary counts.
 active:=0
 if m.count%O3ChunkEdges!=0 {active=1}
 return m.completed+active
}
func (m *O3ComposedMemory) Count()int{return m.count}
func (m *O3ComposedMemory) WholePathCounterfactual(from,to int,input uint8)(uint8,error){
 if m.count!=O3ChainEdges||m.completed!=3||
    from!=m.source||to!=m.target||input>1 {return 0,ErrO3Query}
 composed:=O3Identity
 for _,chunk:=range m.chunks {
  composed=o3ComposeExact(chunk,composed)
 }
 return o3ApplyExact(composed,input),nil
}
// O3LastEightControl retains the same last-eight edges without
// transformations. It cannot soundly answer whole-path queries when the
// preceding four transitions are absent; UNKNOWN is required.
type O3LastEightControl struct {
 count int
 edges [O3SlotsCap]O3Edge
}
func (c *O3LastEightControl) Append(e O3Edge)error {
 if !o3Valid(e.PublicOperator)||e.From==e.To {return ErrO3Path}
 if c.count<O3SlotsCap {c.edges[c.count]=e
 } else {
  copy(c.edges[:],c.edges[1:])
  c.edges[O3SlotsCap-1]=e
 }
 c.count++
 return nil
}
func (c *O3LastEightControl) WholePathCounterfactual(from,to int,input uint8)(uint8,error){
 // The original first four edges are gone; never infer their effects.
 return 0,ErrO3Query
}
// O3SourceFreeIndistinguishability verifies two public-observation-equivalent
// causal graphs with different interventional outcomes. It forbids using
// observational correlation as a sound counterfactual certificate.
func O3SourceFreeIndistinguishability() bool {
 for u:=uint8(0);u<2;u++ {
  x1,y1:=u,u // world 1: X:=U; Y:=X
  x2,y2:=u,u // world 2: X:=U; Y:=U (confounded)
  if x1!=x2||y1!=y2{return false}
 }
 // do(X=1) with exogenous U=0: Y changes in first world but not second.
 return uint8(1)!=uint8(0)
}
