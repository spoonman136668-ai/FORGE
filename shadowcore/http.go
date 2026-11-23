package shadowcore

import (
 "context"
 "encoding/json"
 "errors"
 "net"
 "net/http"
 "sync"
 "time"
)

// StatusServer exposes a read-only, loopback-only status endpoint for an
// INACTIVE shadow controller. It never exposes execution or mutation routes.
type StatusServer struct{
 mu sync.RWMutex
 sample Sample
 ready bool
}
func(s *StatusServer)Record(x Sample){
 s.mu.Lock();defer s.mu.Unlock()
 s.sample=x;s.ready=true
}
func(s *StatusServer)ServeHTTP(w http.ResponseWriter,r *http.Request){
 if r.URL.Path!="/status"||r.Method!=http.MethodGet{
  http.Error(w,"not found",http.StatusNotFound);return
 }
 w.Header().Set("Content-Type","application/json")
 w.Header().Set("Cache-Control","no-store")
 s.mu.RLock();defer s.mu.RUnlock()
 if !s.ready{
  http.Error(w,"shadow observer has no verified snapshot",http.StatusServiceUnavailable);return
 }
 _=json.NewEncoder(w).Encode(s.sample)
}
// RunStatus creates a bounded, local observer process. It binds only to a
// literal loopback address and refuses wildcard or external interfaces.
func RunStatus(ctx context.Context,source Observer,interval time.Duration,address string)error{
 host,_,err:=net.SplitHostPort(address)
 if err!=nil||(host!="127.0.0.1"&&host!="::1"){return ErrUnsafe}
 listener,err:=net.Listen("tcp",address);if err!=nil{return err}
 defer listener.Close()
 status:=&StatusServer{}
 server:=&http.Server{Handler:status,ReadHeaderTimeout:5*time.Second}
 done:=make(chan error,1)
 go func(){done<-server.Serve(listener)}()
 observerDone:=make(chan error,1)
 go func(){observerDone<-Run(ctx,source,interval,func(x Sample)error{status.Record(x);return nil})}()
 select{
 case err=<-observerDone:
 case err=<-done:
  if errors.Is(err,http.ErrServerClosed){err=nil}
 case <-ctx.Done():
  err=nil
 }
 shutdownCtx,cancel:=context.WithTimeout(context.Background(),3*time.Second)
 defer cancel()
 _=server.Shutdown(shutdownCtx)
 return err
}
