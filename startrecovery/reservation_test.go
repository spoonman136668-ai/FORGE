package startrecovery

import (
 "context"
 "errors"
 "testing"
)
type syntheticReservationReader struct{
 status Status
 err error
 readCount int
 reserveCount int
}
func (s *syntheticReservationReader) Read(_ context.Context,i Intent)(Observation,error){
 s.readCount++;return Observation{Intent:i,Status:s.status,IndependentlyAuthenticated:true},s.err
}
func (s *syntheticReservationReader) ReserveOnce(context.Context,Intent)(bool,error){
 s.reserveCount++;return false,errors.New("must never reserve through preflight")
}
func TestReservationReadOnlyAndFailClosed(t *testing.T){
 for _,tc:=range []struct{status Status;want Recovery}{
  {NoReservation,RequestIndependentReservation},
  {Reserved,HoldNoReplay},
  {Dispatched,HoldNoReplay},
  {Completed,HoldNoReplay},
  {Uncertain,HoldNoReplay},
 }{
  r:=&syntheticReservationReader{status:tc.status}
  got,err:=ConsiderReservation(context.Background(),r,fixedIntent())
  if err!=nil||got!=tc.want||r.readCount!=1||r.reserveCount!=0{
   t.Fatalf("%s => %s %v read=%d reserve=%d",tc.status,got,err,r.readCount,r.reserveCount)
  }
 }
}
func TestReservationFailureNeverReplays(t *testing.T){
 for _,errRead:=range []error{errors.New("outage"),context.DeadlineExceeded}{
  r:=&syntheticReservationReader{status:NoReservation,err:errRead}
  got,err:=ConsiderReservation(context.Background(),r,fixedIntent())
  if got!=""||!errors.Is(err,ErrReservationIndeterminate)||r.reserveCount!=0{
   t.Fatalf("read failure allowed reservation: %s %v",got,err)
  }
 }
 got,err:=ConsiderReservation(context.Background(),nil,fixedIntent())
 if got!=""||!errors.Is(err,ErrReservationUnavailable){t.Fatalf("missing authority allowed progression: %s %v",got,err)}
}

func TestInvalidIntentNeverReachesAuthority(t *testing.T){
 reader:=&syntheticReservationReader{status:NoReservation}
 invalid:=fixedIntent()
 invalid.NonceSHA256=""
 got,err:=ConsiderReservation(context.Background(),reader,invalid)
 if got!=""||!errors.Is(err,ErrInvalidIntent)||reader.readCount!=0||reader.reserveCount!=0 {
  t.Fatalf("invalid intent reached authority: %s %v reads=%d reserve=%d",got,err,reader.readCount,reader.reserveCount)
 }
}

type wrongIntentReader struct{syntheticReservationReader}
func (s *wrongIntentReader) Read(_ context.Context, i Intent)(Observation,error){
 s.readCount++
 i.ExperimentID="OTHER"
 return Observation{Intent:i,Status:NoReservation,IndependentlyAuthenticated:true},nil
}
func TestCrossExperimentReadObservationCannotAuthorizeReservation(t *testing.T){
 r:=&wrongIntentReader{}
 got,err:=ConsiderReservation(context.Background(),r,fixedIntent())
 if got!=""||!errors.Is(err,ErrInvalidIntent)||r.reserveCount!=0{
  t.Fatalf("cross experiment status accepted: %s %v",got,err)
 }
}

type unauthenticatedReader struct{syntheticReservationReader}
func (s *unauthenticatedReader) Read(_ context.Context,i Intent)(Observation,error){
 s.readCount++
 return Observation{Intent:i,Status:NoReservation,IndependentlyAuthenticated:false},nil
}
func TestUnauthenticatedReservationReadFailsClosed(t *testing.T){
 r:=&unauthenticatedReader{}
 got,err:=ConsiderReservation(context.Background(),r,fixedIntent())
 if got!=""||!errors.Is(err,ErrInvalidIntent)||r.reserveCount!=0 {
  t.Fatalf("unauthenticated observation admitted: %s %v",got,err)
 }
}
