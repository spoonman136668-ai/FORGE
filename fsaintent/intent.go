// Package fsaintent implements the FORGE-only, deterministic one-shot primary
// intent journal and read-only replay classification. It never starts a
// worker, reserves resources, writes an external authority, or grants science
// admission. SHA-256 chaining is NOT authentication or durable storage.
package fsaintent

import (
    "crypto/sha256"
    "encoding/hex"
    "encoding/json"
    "errors"
    "fmt"
)

const (
    Schema = "forge.fsa.one-shot-intents.v1"
    MaxEntries = 2048
    genesis = "0000000000000000000000000000000000000000000000000000000000000000"
)

var ErrBlocked = errors.New("FORGE_FSA_INTENT_REPLAY_OR_AUTHORITY_BLOCKED")

type Stage string
const (
    Prepared Stage = "INTENT_PREPARED_NOT_DISPATCHED"
    // DispatchRisk MUST be durably committed by a separately authenticated
    // authority BEFORE any possible worker launch. An uncertain result can
    // never trigger automatic re-dispatch.
    DispatchRisk Stage = "DISPATCH_MAY_HAVE_OCCURRED"
    Indeterminate Stage = "START_INDETERMINATE"
    StartObserved Stage = "PRIMARY_START_WITNESSED"
    TerminalObserved Stage = "PRIMARY_TERMINAL_WITNESSED"
)

// Intent is a fully immutable logical experiment identity. Assign RunID once,
// before any dispatch attempt, to enable independent evidence correlation.
type Intent struct {
    Lane string `json:"lane"`
    CandidateID string `json:"candidate_id"`
    Generation uint64 `json:"generation"`
    RunID uint64 `json:"run_id"`
    FrozenSHA256 string `json:"frozen_sha256"`
    CohortSHA256 string `json:"cohort_sha256"`
    SourceSHA string `json:"source_sha"`
    PreregSHA256 string `json:"prereg_sha256"`
    BudgetUnits uint64 `json:"budget_units"`
}

type Record struct {
    Schema string `json:"schema"`
    Sequence uint64 `json:"sequence"`
    PreviousSHA256 string `json:"previous_sha256"`
    Intent Intent `json:"intent"`
    Stage Stage `json:"stage"`
    // For witnessed stages this is a hash of independently authenticated
    // start/terminal evidence. Its presence alone DOES NOT authenticate it.
    WitnessSHA256 string `json:"witness_sha256,omitempty"`
    RecordSHA256 string `json:"record_sha256"`
}

type Journal struct {
    Schema string `json:"schema"`
    Entries []Record `json:"entries"`
}

type TrustedHead struct {
    Sequence uint64
    SHA256 string
    IndependentlyAuthenticated bool
}

type Decision string
const (
    PreparedOnly Decision = "PREPARED_NOT_AUTHORIZED_TO_DISPATCH"
    NoRedispatchUnknown Decision = "UNCERTAIN_START_RECONCILE_NO_REDISPATCH"
    NoRedispatchStarted Decision = "START_WITNESSED_NO_REDISPATCH"
    NoRedispatchTerminal Decision = "TERMINAL_WITNESSED_NO_REDISPATCH"
)

func New() Journal { return Journal{Schema:Schema,Entries:[]Record{}} }

func lowerHex(s string,n int)bool{
    if len(s)!=n{return false}
    for _,c:=range s{if !((c>='0'&&c<='9')||(c>='a'&&c<='f')){return false}}
    return true
}
func identifier(s string)bool{
    if len(s)<3||len(s)>96{return false}
    for _,c:=range s{
        if !((c>='a'&&c<='z')||(c>='A'&&c<='Z')||(c>='0'&&c<='9')||c=='_'||c=='-'||c=='.'){return false}
    }
    return true
}
func validateIntent(i Intent)error{
    if (i.Lane!="Wingless"&&i.Lane!="Yggdrasil")||
        !identifier(i.CandidateID)||i.Generation==0||i.Generation>1000000000||
        i.RunID==0||!lowerHex(i.FrozenSHA256,64)||!lowerHex(i.CohortSHA256,64)||
        !lowerHex(i.PreregSHA256,64)||!lowerHex(i.SourceSHA,40)||
        i.BudgetUnits==0||i.BudgetUnits>1000000{
        return fmt.Errorf("%w: incomplete immutable intent",ErrBlocked)
    }
    return nil
}
func validateStage(stage Stage,witness string)error{
    switch stage{
    case Prepared,DispatchRisk,Indeterminate:
        if witness!="" {return fmt.Errorf("%w: witness not allowed before observation",ErrBlocked)}
    case StartObserved,TerminalObserved:
        if !lowerHex(witness,64) {return fmt.Errorf("%w: independently witnessed receipt missing",ErrBlocked)}
    default:return fmt.Errorf("%w: invalid lifecycle stage",ErrBlocked)
    }
    return nil
}
func digest(row Record)(string,error){
    row.RecordSHA256=""
    raw,err:=json.Marshal(row)
    if err!=nil{return "",err}
    sum:=sha256.Sum256(append([]byte("FORGE-FSA-ONE-SHOT-INTENT-RECORD-V1\n"),raw...))
    return hex.EncodeToString(sum[:]),nil
}
func advance(previous,current Stage)bool{
    switch previous{
    case Prepared:return current==DispatchRisk
    case DispatchRisk:return current==Indeterminate||current==StartObserved
    case Indeterminate:return current==StartObserved
    case StartObserved:return current==TerminalObserved
    default:return false
    }
}
func key(i Intent)string{return i.Lane+":"+i.CandidateID}

// Verify checks global hash order, immutable identities and cohorts, and the
// one-shot phase machine across BOTH lanes. It is deliberately not a witness
// verifier or a proof that the journal is physically durable/complete.
func Verify(j Journal)error{
    if j.Schema!=Schema||j.Entries==nil||len(j.Entries)>MaxEntries{
        return fmt.Errorf("%w: schema or bounds",ErrBlocked)
    }
    type phase struct{intent Intent;stage Stage}
    state:=map[string]phase{}
    cohorts:=map[string]string{}
    runIDs:=map[uint64]string{}
    prior:=genesis
    for offset,row:=range j.Entries{
        if row.Schema!=Schema||row.Sequence!=uint64(offset+1)||
            row.PreviousSHA256!=prior||!lowerHex(row.RecordSHA256,64){
            return fmt.Errorf("%w: sequence or predecessor at %d",ErrBlocked,offset+1)
        }
        if err:=validateIntent(row.Intent);err!=nil{return err}
        if err:=validateStage(row.Stage,row.WitnessSHA256);err!=nil{return err}
        hash,err:=digest(row)
        if err!=nil||hash!=row.RecordSHA256{return fmt.Errorf("%w: record hash mismatch",ErrBlocked)}
        id:=key(row.Intent)
        if previous,exists:=state[id];exists {
            if previous.intent!=row.Intent||!advance(previous.stage,row.Stage){
                return fmt.Errorf("%w: immutable identity or repeated dispatch",ErrBlocked)
            }
        }else{
            if row.Stage!=Prepared{return fmt.Errorf("%w: durable intent required before launch risk",ErrBlocked)}
            if owner,exists:=cohorts[row.Intent.CohortSHA256];exists&&owner!=id{
                return fmt.Errorf("%w: cross-lane cohort reused",ErrBlocked)
            }
            if owner,exists:=runIDs[row.Intent.RunID];exists&&owner!=id{
                return fmt.Errorf("%w: correlation run ID reused",ErrBlocked)
            }
            cohorts[row.Intent.CohortSHA256]=id
            runIDs[row.Intent.RunID]=id
        }
        state[id]=phase{intent:row.Intent,stage:row.Stage}
        prior=row.RecordSHA256
    }
    return nil
}

// Append models ONE next durable logical event, in memory ONLY. A real service
// must atomically persist/externally witness this exact record before it can
// act. In particular, an error or unknown CAS return MUST NOT be retried as
// a new dispatch and a caller MUST NOT infer worker-launch permission.
func Append(j Journal,i Intent,s Stage,witness string)(Journal,error){
    if err:=Verify(j);err!=nil{return Journal{},err}
    if len(j.Entries)>=MaxEntries{return Journal{},ErrBlocked}
    // Reject malformed or oversized caller inputs before JSON serialization,
    // hashing, allocation of the next journal, or any durable handoff.
    if err:=validateIntent(i);err!=nil{return Journal{},err}
    if err:=validateStage(s,witness);err!=nil{return Journal{},err}
    prev:=genesis
    if len(j.Entries)>0{prev=j.Entries[len(j.Entries)-1].RecordSHA256}
    record:=Record{
        Schema:Schema,Sequence:uint64(len(j.Entries)+1),
        PreviousSHA256:prev,Intent:i,Stage:s,WitnessSHA256:witness,
    }
    var err error
    record.RecordSHA256,err=digest(record)
    if err!=nil{return Journal{},err}
    next:=Journal{Schema:Schema,Entries:make([]Record,len(j.Entries)+1)}
    copy(next.Entries,j.Entries);next.Entries[len(j.Entries)]=record
    if err:=Verify(next);err!=nil{return Journal{},err}
    return next,nil
}

// Inspect is an observation-only crash/restart classifier. A verified journal
// plus an externally authenticated exact head is required; no locally
// recomputed head may stand in for independent FSA authentication.
func Inspect(j Journal,head TrustedHead,lane,candidateID string)(Decision,error){
    if !head.IndependentlyAuthenticated||head.Sequence==0||
        !lowerHex(head.SHA256,64)||!identifier(candidateID)||
        (lane!="Wingless"&&lane!="Yggdrasil"){
        return "",fmt.Errorf("%w: externally authenticated highwater required",ErrBlocked)
    }
    if err:=Verify(j);err!=nil{return "",err}
    if uint64(len(j.Entries))!=head.Sequence||
        j.Entries[len(j.Entries)-1].RecordSHA256!=head.SHA256{
        return "",fmt.Errorf("%w: stale or truncated trusted head",ErrBlocked)
    }
    var last Stage
    for _,record:=range j.Entries{
        if record.Intent.Lane==lane&&record.Intent.CandidateID==candidateID{
            last=record.Stage
        }
    }
    switch last{
    case Prepared:return PreparedOnly,nil
    case DispatchRisk,Indeterminate:return NoRedispatchUnknown,nil
    case StartObserved:return NoRedispatchStarted,nil
    case TerminalObserved:return NoRedispatchTerminal,nil
    default:return "",fmt.Errorf("%w: intent not found",ErrBlocked)
    }
}
