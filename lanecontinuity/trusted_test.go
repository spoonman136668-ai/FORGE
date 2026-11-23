package lanecontinuity

import (
 "context"
 "errors"
 "testing"

 "github.com/spoonman136668-ai/forge/fsatrust"
)

func TestTrustedPairRequiresIndependentFSA(t *testing.T){
 w:=Input{Lane:Wingless,Failure:ModelQuota,QualifiedWorkAvailable:true}
 y:=Input{Lane:Yggdrasil,Failure:ModelOffline,QualifiedWorkAvailable:true}
 got,err:=InspectTrustedPair(context.Background(),nil,nil,fsatrust.Identity{},"W0001","Y0001",w,y)
 if !errors.Is(err,ErrUntrustedState)||got!=(TrustedPair{}){
  t.Fatalf("missing trust granted planning: %+v %v",got,err)
 }
}
func TestTrustedPairRejectsMalformedLaneBeforeExternalRecovery(t *testing.T){
 w:=Input{Lane:Wingless,Failure:None,QualifiedWorkAvailable:true}
 cases:=[]struct{lane Lane;experiment string}{
  {Yggdrasil,""},{Wingless,"Y0001"},{"INVALID","Y0001"},
 }
 for _,tc:=range cases{
  y:=Input{Lane:tc.lane,Failure:ModelQuota,QualifiedWorkAvailable:true}
  got,err:=InspectTrustedPair(context.Background(),nil,nil,fsatrust.Identity{},"W0001",tc.experiment,w,y)
  if !errors.Is(err,ErrInvalidInput)||got!=(TrustedPair{}){
   t.Fatalf("malformed lane yielded partial planning %+v %v",got,err)
  }
 }
}
