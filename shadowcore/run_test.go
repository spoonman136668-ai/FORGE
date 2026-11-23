package shadowcore
import(
 "context"
 "errors"
 "strings"
 "testing"
 "time"
 "github.com/spoonman136668-ai/forge/researchstate"
)
type sourceFunc func()(researchstate.Journal,error)
func(f sourceFunc)Load()(researchstate.Journal,error){return f()}
func seeded(t *testing.T)researchstate.Journal{
 t.Helper();j:=researchstate.New()
 for _,lane:=range []string{"Wingless","Yggdrasil"}{
  h,_:=researchstate.Head(j)
  var err error
  j,err=researchstate.Append(j,researchstate.Event{Lane:lane,ExperimentID:"existing",FrozenSHA256:strings.Repeat("a",64),To:researchstate.Proposed},h)
  if err!=nil{t.Fatal(err)}
 }
 return j
}
func TestShadowRunObservesBothExistingLanesWithoutDispatch(t *testing.T){
 j:=seeded(t);ctx,cancel:=context.WithCancel(context.Background())
 count:=0
 err:=Run(ctx,sourceFunc(func()(researchstate.Journal,error){return j,nil}),time.Second,func(s Sample)error{
  count++;if s.Status!="INACTIVE_SHADOW_NO_SCIENCE_AUTHORITY"||s.Progress.Wingless.RecordedOriginals!=1||s.Progress.Yggdrasil.RecordedOriginals!=1||s.Progress.GenuineAutonomousCyclesVerified{t.Fatal(s)}
  cancel();return nil
 })
 if err!=nil||count!=1{t.Fatal(err,count)}
}
func TestShadowRejectsInvalidInputAndArchive(t *testing.T){
 ctx:=context.Background()
 if err:=Run(ctx,sourceFunc(func()(researchstate.Journal,error){return researchstate.New(),nil}),time.Second,func(Sample)error{return nil});!errors.Is(err,ErrUnsafe){t.Fatal("empty archive accepted",err)}
 if err:=Run(ctx,sourceFunc(func()(researchstate.Journal,error){return seeded(t),nil}),time.Millisecond,func(Sample)error{return nil});!errors.Is(err,ErrUnsafe){t.Fatal("unsafe poll interval accepted",err)}
}
