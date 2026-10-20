package lcrm01

// O9 exact compiled physical-version-space memory. SOURCE-FREE engineering.
//
// Store *all* 32 physical law/port hypotheses as one query-blind compact
// bitset, and intersect precompiled public-evidence masks. Never treat a
// synthetic attestation flag as independently verified causal provenance.
// An answer is certified only if every surviving causal world agrees.

type O9CompiledPhysicalMemory struct {
    hypotheses uint32
    grounded bool
    orientation uint8
}

var o9PhysicalEvidenceMasks = func() (m [4][2]uint32) {
    for h:=uint8(0); h<32; h++ {
        orientation:=h>>4
        law:=h&15
        for cell:=uint8(0); cell<4; cell++ {
            a,b:=cell>>1,cell&1
            if orientation==1 { a,b=b,a }
            v:=o6TableValue(law,a,b)
            m[cell][v] |= uint32(1)<<h
        }
    }
    return
}()

var o9CanonicalOutputMasks = func() (m [4][2]uint16) {
    for law:=uint8(0); law<16;law++ {
        for cell:=uint8(0);cell<4;cell++ {
            v:=o6TableValue(law,cell>>1,cell&1)
            m[cell][v] |= uint16(1)<<law
        }
    }
    return
}()

func NewO9CompiledPhysicalMemory()*O9CompiledPhysicalMemory {
    return &O9CompiledPhysicalMemory{hypotheses:^uint32(0)}
}

func(o *O9CompiledPhysicalMemory)Ground(e O7Grounding)error {
    if o==nil || !e.valid() { return ErrO7Anchor }
    if o.grounded && o.orientation!=e.SemanticAPhysical { return ErrO7Conflict }
    next:=o.hypotheses
    if e.SemanticAPhysical==0 { next &= 0x0000ffff } else { next &= 0xffff0000 }
    if next==0 { return ErrO7Conflict }
    o.hypotheses=next
    o.grounded=true
    o.orientation=e.SemanticAPhysical
    return nil
}

func(o *O9CompiledPhysicalMemory)Observe(e O7PhysicalIntervention)error {
    if o==nil || !e.valid(){ return ErrO7Evidence }
    cell:=(e.P<<1)|e.Q
    next:=o.hypotheses & o9PhysicalEvidenceMasks[cell][e.Output]
    if next==0{ return ErrO7Conflict }
    o.hypotheses=next
    return nil
}

func(o *O9CompiledPhysicalMemory)PossibleSemanticTables()uint16 {
    if o==nil { return 0 }
    return uint16(o.hypotheses) | uint16(o.hypotheses>>16)
}

func(o *O9CompiledPhysicalMemory)PredictCanonical(a,b uint8)(uint8,bool,error){
    if o==nil { return 0,false,ErrO7Query }
    tables:=o.PossibleSemanticTables()
    if tables==0 {return 0,false,ErrO7Conflict}
    if a>1||b>1{return 0,false,ErrO7Query}
    cell:=(a<<1)|b
    mayZero:=tables&o9CanonicalOutputMasks[cell][0]!=0
    mayOne:=tables&o9CanonicalOutputMasks[cell][1]!=0
    if mayZero && mayOne{return 0,false,nil}
    if mayZero{return 0,true,nil}
    if mayOne{return 1,true,nil}
    return 0,false,ErrO7Conflict
}

func O9ComposeTwoHopCompiled(first,second *O9CompiledPhysicalMemory,
    a,b,c uint8)(uint8,bool,error){
    if first==nil || second==nil || a>1||b>1||c>1 {
        return 0,false,ErrO7Query
    }
    x,y:=first.PossibleSemanticTables(),second.PossibleSemanticTables()
    if x==0||y==0{return 0,false,ErrO7Conflict}
    firstCell:=(a<<1)|b
    mayZero,mayOne:=false,false
    for middle:=uint8(0);middle<2;middle++ {
        if x&o9CanonicalOutputMasks[firstCell][middle]==0{continue}
        secondCell:=(middle<<1)|c
        mayZero=mayZero || y&o9CanonicalOutputMasks[secondCell][0]!=0
        mayOne=mayOne || y&o9CanonicalOutputMasks[secondCell][1]!=0
        if mayZero && mayOne {return 0,false,nil}
    }
    if mayZero{return 0,true,nil}
    if mayOne{return 1,true,nil}
    return 0,false,ErrO7Conflict
}
