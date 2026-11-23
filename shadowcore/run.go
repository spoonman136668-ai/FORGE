package shadowcore

import (
 "context"
 "errors"
 "fmt"
 "time"
 "github.com/spoonman136668-ai/forge/researchstate"
)

// Observer is an inactive read-only source of durable scientific state.
type Observer interface { Load() (researchstate.Journal,error) }
type ArchiveObserver struct{ Root string }
func(a ArchiveObserver)Load()(researchstate.Journal,error){
 if a.Root==""{return researchstate.Journal{},ErrUnsafe}
 return researchstate.LoadArchive(a.Root)
}
type Sample struct {
 Sequence uint64 `json:"sequence"`
 Status string `json:"status"`
 Progress ProgressReport `json:"progress"`
}
// Run observes a persistent journal until cancelled. Invalid/partial/corrupt
// state fails closed; polling has no access to dispatch, reservations or
// authority mutations. The source's monotonic journal ancestry must hold.
func Run(ctx context.Context,source Observer,interval time.Duration,emit func(Sample)error)error{
 if ctx==nil||source==nil||emit==nil||interval<time.Second||interval>5*time.Minute{return ErrUnsafe}
 ticker:=time.NewTicker(interval)
 defer ticker.Stop()
 var previous researchstate.Journal
 for seq:=uint64(1);;seq++ {
  current,err:=source.Load()
  if err!=nil{return fmt.Errorf("%w: archive: %v",ErrUnsafe,err)}
  if previous.Entries!=nil {
   if len(current.Entries)<len(previous.Entries){return errors.Join(ErrUnsafe,errors.New("archive rollback"))}
   for i:=range previous.Entries{
    if previous.Entries[i]!=current.Entries[i]{return errors.Join(ErrUnsafe,errors.New("archive fork"))}
   }
  }
  report,err:=Measure(current);if err!=nil{return err}
  if err:=emit(Sample{Sequence:seq,Status:"INACTIVE_SHADOW_NO_SCIENCE_AUTHORITY",Progress:report});err!=nil{return err}
  previous=current
  select{
  case <-ctx.Done():return nil
  case <-ticker.C:
  }
 }
}
