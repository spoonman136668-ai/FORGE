package pkg

import (
 "encoding/json"
 "fmt"
 "net/http"
 "sort"
 "testing"
 "time"
)

// RC2-P: a transient, synthetic order-creation probe installed only into a
// temporary exact-source checkout. It is never included in the shipped binary.
// Both versions execute the original native entry point, real pre-POST
// reservation/receipt path, and a deliberately intercepted fake HTTP transport.
// Broker-labelled fixture credentials do NOT reach any network.
func TestRC2PFirstNativeBuyOrderBoundaries(t *testing.T) {
 enableRetryTestTranches(t)
 h, n, pm, _ := trancheAdapterFixture(t)
 pm.ladderLots.orderManager = nil
 pm.ladderLots.mu.Lock()
 pm.ladderLots.rebuildExecutionIndexesLocked()
 pm.ladderLots.mu.Unlock()

 trace := &nativeConstructionTiming{}
 n.timing = trace
 originalRecord := n.Record
 var evidenceCalls int
 var postExecuteEvidenceUs int64
 n.Record = func(e NativeOrderEvidence) error {
   start := time.Now()
   err := originalRecord(e)
   evidenceCalls++
   postExecuteEvidenceUs += time.Since(start).Microseconds()
   return err
 }
 var postStart, postDone time.Time
 var postCount int
 var posted AdvancedOrderRequest
 h.advancedOrderManager = nativeQuoteRecoveryFixture(t,n,lookupRoundTripFunc(func(req *http.Request) (*http.Response,error) {
   switch req.URL.Path {
   case "/api/v3/brokerage/best_bid_ask":
     at := time.Now()
     return makerBookResponse(makerTestBook("76499.99","76500",n.Signal.ProductID,at),at),nil
   case "/api/v3/brokerage/time":
     return makerTimeResponse(time.Now()),nil
   case "/api/v3/brokerage/orders":
     postCount++
     if postCount!=1 {
       return nil,fmt.Errorf("synthetic initial order submitted more than once")
     }
     postStart=time.Now()
     if err:=json.NewDecoder(req.Body).Decode(&posted);err!=nil{return nil,err}
     if posted.ProductID!=n.Signal.ProductID || posted.Side!=OrderSideBuy ||
        posted.OrderConfiguration.LimitLimitGTC==nil ||
        !posted.OrderConfiguration.LimitLimitGTC.PostOnly {
       return nil,fmt.Errorf("synthetic native BUY contract changed")
     }
     // Deliberately separate controlled HTTP acknowledgment from application
     // work. No Coinbase contact and no actual order are possible here.
     time.Sleep(20*time.Millisecond)
     postDone=time.Now()
     return lookupFixtureResponse(map[string]any{
       "success":true,
       "success_response":map[string]string{
         "order_id":"rc2p-synthetic-first-order",
         "client_order_id":posted.ClientOrderID,
       },
     },http.StatusOK),nil
   default:
     return nil,fmt.Errorf("unexpected network path blocked in offline probe")
   }
 }))
 start:=time.Now()
 result,err:=h.ExecuteNativeSignal(n,t.TempDir())
 afterExecute:=time.Now()
 if err!=nil || result==nil || postCount!=1 || postStart.IsZero() || postDone.IsZero() {
   t.Fatalf("initial order not acknowledged once: err=%v posts=%d",err,postCount)
 }
 if n.Requests!=1 || !n.ResultRecorded || n.EvidenceFailed {
   t.Fatalf("native request/evidence contract failed: requests=%d recorded=%v failed=%v",
       n.Requests,n.ResultRecorded,n.EvidenceFailed)
 }
 // Post-order presentation uses real order-observation and dashboard
 // projection functions; this measures model preparation, not WPF rendering.
 presentationStart:=time.Now()
 h.advancedOrderManager.ObserveDashboardOrder(UserOrderUpdate{
   OrderID:"rc2p-synthetic-first-order",ProductID:n.Signal.ProductID,
   Side:"BUY",Status:"OPEN",LimitPrice:76500,
   LeavesQuantity:0.0001,EventTime:time.Now(),
 })
 rows:=h.advancedOrderManager.dashboardOrderSnapshot(n.Signal.ProductID)
 model:=DashboardUIModel{}
 applyDashboardOrders(&model,&DashboardSnapshot{
   ProductID:n.Signal.ProductID,PriceIncrement:0.01,OrderEvidence:rows,
 })
 presentationUs:=time.Since(presentationStart).Microseconds()
 if len(rows)!=1 || len(model.OrderRows)!=1 {
   t.Fatalf("post-ack dashboard lost accepted synthetic BUY: rows=%d model=%d",
     len(rows),len(model.OrderRows))
 }
 // The fixture observes acceptance, not a real fill or paper fill accounting.
 // Do not claim UI paint or end-to-end exchange/P&L measurements.
 snap:=trace.snapshot("RC2P",nil,true)
 sort.Slice(snap.Spans,func(i,j int)bool{return snap.Spans[i].Stage<snap.Spans[j].Stage})
 var preTransportUs int64 = postStart.Sub(start).Microseconds()
 var fakeHTTPUs int64 = postDone.Sub(postStart).Microseconds()
 var executionReturnAfterAckUs int64 = afterExecute.Sub(postDone).Microseconds()
 var nativeTotalUs int64 = afterExecute.Sub(start).Microseconds()
 var transportReadyUs int64 = -1
 if len(snap.Ready)>0 {transportReadyUs=int64(snap.Ready[0].ConstructionMS*1000)}
 t.Logf("RC2P_BOUNDARY pre_post_us=%d fake_http_ack_us=%d ack_to_execute_return_us=%d evidence_callback_us=%d post_ack_dashboard_model_us=%d initial_native_total_us=%d transport_ready_us=%d posts=%d evidence_callbacks=%d native_spans=%d",
   preTransportUs,fakeHTTPUs,executionReturnAfterAckUs,postExecuteEvidenceUs,
   presentationUs,nativeTotalUs,transportReadyUs,postCount,evidenceCalls,len(snap.Spans))
 for _,span:=range snap.Spans {
   valid:=len(span.Stage)>0
   for _,ch:=range span.Stage {
     if !((ch>='a' && ch<='z')||(ch>='A' && ch<='Z')||
       (ch>='0' && ch<='9')||ch=='.'||ch=='_'||ch=='-') {valid=false;break}
   }
   if valid && span.DurationMS>=0 {
     t.Logf("RC2P_SPAN stage=%s duration_us=%d",
       span.Stage,int64(span.DurationMS*1000))
   }
 }
}
