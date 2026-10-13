package ckbcustody

import (
 "encoding/json"
 "errors"
 "strconv"
 "path/filepath"
)

// WakeBinding is the immutable provenance recorded BEFORE CKB's S14
// first-use issuer operation. Reading it can NEVER clear consumption.
type WakeBinding struct {
 WakeRunID int64
 WakeMainSHA string
 ControllerSHA string
 PermanentLedgerSHA256 string
}

// ReadS14WakeBinding requires the complete independently pinned S09-S14
// history and rereads the exact S14 record. Absence, corruption or a mutable
// GitHub wake identity fails closed rather than indicating an unused cohort.
func ReadS14WakeBinding(stateDirectory string,pins map[string]string)(WakeBinding,error){
 inventory,err:=Inspect(stateDirectory)
 if err!=nil||len(inventory.Generations)!=6||
  inventory.S14Disposition!="PERMANENT_FIRST_USE_CONSUMED_NO_REPLAY"||
  VerifyPins(inventory,pins)!=nil{return WakeBinding{},ErrUnsafe}
 doc,sha,err:=readLedger(filepath.Join(stateDirectory,"s14-first-use-consumed.v1.json"))
 if err!=nil||sha!=pins["S14"]||sha!=inventory.Generations[5].SHA256||
  !number(doc,"wake_run_id"){return WakeBinding{},ErrUnsafe}
 idText,ok:=doc["wake_run_id"].(json.Number)
 if !ok{return WakeBinding{},ErrUnsafe}
 id,err:=strconv.ParseInt(idText.String(),10,64)
 if err!=nil||id<=0{return WakeBinding{},errors.Join(ErrUnsafe,err)}
 main,ok:=doc["wake_main_sha"].(string)
 if !ok||!hexLower(main,40){return WakeBinding{},ErrUnsafe}
 ctl,ok:=doc["controller_sha"].(string)
 if !ok||!hexLower(ctl,40){return WakeBinding{},ErrUnsafe}
 return WakeBinding{WakeRunID:id,WakeMainSHA:main,ControllerSHA:ctl,
  PermanentLedgerSHA256:sha},nil
}
