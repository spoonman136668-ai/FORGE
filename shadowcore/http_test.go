package shadowcore

import (
 "context"
 "net/http"
 "net/http/httptest"
 "strings"
 "testing"
 "time"
)
func TestStatusServiceFailsClosedBeforeObservation(t *testing.T){
 s:=&StatusServer{}
 req:=httptest.NewRequest(http.MethodGet,"/status",nil)
 rec:=httptest.NewRecorder()
 s.ServeHTTP(rec,req)
 if rec.Code!=http.StatusServiceUnavailable{t.Fatalf("unverified state exposed: %d",rec.Code)}
 s.Record(Sample{Sequence:1,Status:"INACTIVE_SHADOW_NO_SCIENCE_AUTHORITY"})
 rec=httptest.NewRecorder();s.ServeHTTP(rec,req)
 if rec.Code!=http.StatusOK||!strings.Contains(rec.Body.String(),"INACTIVE_SHADOW"){t.Fatalf("status missing %d %s",rec.Code,rec.Body.String())}
 for _,method:=range []string{"POST","PUT","DELETE"}{
  rec=httptest.NewRecorder();s.ServeHTTP(rec,httptest.NewRequest(method,"/status",nil))
  if rec.Code==http.StatusOK{t.Fatal("mutation route accepted")}
 }
}
func TestStatusServiceNeverListensExternally(t *testing.T){
 ctx,cancel:=context.WithCancel(context.Background());defer cancel()
 for _,address:=range []string{":0","0.0.0.0:0","[::]:0","localhost:0","example.com:80"}{
  if err:=RunStatus(ctx,nil,time.Second,address);err==nil{t.Fatal("external bind accepted",address)}
 }
}
