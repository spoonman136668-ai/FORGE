package pilotf4

import (
 "errors"
 "github.com/spoonman136668-ai/forge/fsagithubcustody"
)

// CheckCustody is the explicit boundary between source-only eligibility facts
// and independently authenticated scientific first-use execution authority.
// The GitHub posture audit alone can NEVER issue scientific authorization.
func CheckCustody(r fsagithubcustody.Report)error{
 if err:=fsagithubcustody.DenyAuthority(r);err!=nil{return err}
 return errors.New("F4_EXTERNAL_CUSTODY_REQUIRED")
}
