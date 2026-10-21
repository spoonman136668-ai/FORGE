package pkg

import (
  "encoding/json"
  "errors"
  "fmt"
  "net/http"
  "os"
  "path/filepath"
  "strings"
  "testing"
  "time"
)

// RC2-Q transient test; must not be committed to K-Terminal sources.
// K-Terminal's built-in PAPER transport is used unchanged. The HTTP fixture
// deliberately rejects *all* requests; this test must never contact a broker.
func TestRC2QNativePaperOneOrderReceiptAndDashboardPublication(t *testing.T) {
  h, n, pm, _ := trancheAdapterFixture(t)
  ctrl, err := NewTrancheController(t.TempDir(),
    TrancheScope{"PAPER", "account", lookupPortfolio, "BTC-USDC", "20-40-40"})
  if err != nil {t.Fatal(err)}
  h.tranches=ctrl
  n.Signal.Environment="PAPER"
  n.Snapshot.Environment="PAPER"
  n.Authorize=func()error{return errors.New("PAPER_CALL_TO_LIVE_AUTHORIZATION")}
  var postHTTP int
  aom:=nativeQuoteRecoveryFixture(t,n,lookupRoundTripFunc(
    func(req *http.Request)(*http.Response,error) {
      postHTTP++
      return nil,fmt.Errorf("unexpected external request in native PAPER mode")
    }))
  aom.auth.paper=true
  h.advancedOrderManager=aom
  var requestID string
  var readyAt, resultAt time.Time
  var requestReady, resultEvidence int
  n.Record=func(e NativeOrderEvidence)error{
    switch e.State {
    case "PAPER_ORDER_READY":
      requestReady++
      readyAt=time.Now()
      var req AdvancedOrderRequest
      if err:=json.Unmarshal(e.Request,&req);err!=nil{return err}
      requestID=req.ClientOrderID
      if req.ProductID!=n.Signal.ProductID || req.Side!=OrderSideBuy ||
         req.OrderConfiguration.LimitLimitGTC==nil ||
         !req.OrderConfiguration.LimitLimitGTC.PostOnly {
        return fmt.Errorf("paper body violated native BUY contract")
      }
    case "RESULT":
      resultEvidence++
      resultAt=time.Now()
    }
    return nil
  }
  n.timing=&nativeConstructionTiming{}
  receiptRoot:=t.TempDir()
  before:=pm.Snapshot()
  entryStart:=time.Now()
  result,err:=h.ExecuteNativeSignal(n,receiptRoot)
  returnedAt:=time.Now()
  if err!=nil||result==nil||n.Requests!=1||!n.ResultRecorded||n.EvidenceFailed {
    t.Fatalf("PAPER_NATIVE_ACK_DENIED err=%v requests=%d result_recorded=%v",err,n.Requests,n.ResultRecorded)
  }
  if requestReady!=1||resultEvidence!=1||requestID==""||postHTTP!=0 {
    t.Fatalf("PAPER_SYNTHETIC_TRANSPORT_NOT_ISOLATED ready=%d result=%d http=%d",requestReady,resultEvidence,postHTTP)
  }
  if readyAt.Before(entryStart)||resultAt.Before(readyAt)||returnedAt.Before(resultAt) {
    t.Fatal("PAPER_EVENT_CLOCK_ORDER_INVALID")
  }
  // The *application* contract is a validated preview, not a synthetic
  // filled/working order. Never reinterpret the transport's paper- ID as
  // an accepted exchange or paper-engine order.
  paperResult,ok:=result.(map[string]interface{})
  if !ok || paperResult["status"]!="PAPER_ORDER_READY" ||
     paperResult["client_order_id"]!=requestID {
    t.Fatal("PAPER_READY_PREVIEW_CONTRACT_NOT_PRESERVED")
  }
  // The display update below is an explicit test-only injected observation.
  // No production event publisher is claimed for this preview.
  expectedOrderID:="paper-"+requestID
  receiptName:=nativeReceiptKey(n.Signal)+".json"
  receiptInfo,e:=os.Stat(filepath.Join(receiptRoot,receiptName))
  if e!=nil||receiptInfo.Size()==0 {t.Fatal("PAPER_RECEIPT_NOT_DURABLE")}
  if len(ctrl.state.Reservations)!=0 {
    t.Fatal("PAPER_TRANSPORT_UNEXPECTED_LIVE_RESERVATION")
  }
  postAckPosition:=pm.Snapshot()
  if postAckPosition.Quantity!=before.Quantity||
     postAckPosition.CostBasis!=before.CostBasis {
    t.Fatal("PAPER_ACK_INVENTED_FILL_OR_COST_BASIS")
  }
  duplicateStart:=time.Now()
  duplicate,dupErr:=h.ExecuteNativeSignal(n,receiptRoot)
  dupDuration:=time.Since(duplicateStart)
  dupMap,duplicateOK:=duplicate.(map[string]any)
  if dupErr!=nil||!duplicateOK||dupMap["status"]!="DUPLICATE_NO_REPLAY"||
     n.Requests!=1||postHTTP!=0 {
    t.Fatalf("PAPER_DUPLICATE_REEXECUTED status=%v err=%v requests=%d",dupMap["status"],dupErr,n.Requests)
  }
  uiStart:=time.Now()
  aom.ObserveDashboardOrder(UserOrderUpdate{
    OrderID:expectedOrderID,ClientOrderID:requestID,ProductID:n.Signal.ProductID,
    Side:"BUY",Status:"OPEN",LimitPrice:76500,
    LeavesQuantity:0.0001,EventTime:time.Now(),
  })
  rows:=aom.dashboardOrderSnapshot(n.Signal.ProductID)
  model:=DashboardUIModel{}
  applyDashboardOrders(&model,&DashboardSnapshot{
    ProductID:n.Signal.ProductID,PriceIncrement:0.01,OrderEvidence:rows,
  })
  uiModelUs:=time.Since(uiStart).Microseconds()
  if len(rows)!=1||len(model.OrderRows)!=1 {t.Fatal("PAPER_UI_MODEL_MISSING_ORDER")}
  writeStart:=time.Now()
  uiFile:=filepath.Join(t.TempDir(),"paper-dashboard-model.json")
  if err:=writeDashboardUIModel(uiFile,model);err!=nil {t.Fatal(err)}
  uiWriteUs:=time.Since(writeStart).Microseconds()
  if info,e:=os.Stat(uiFile);e!=nil||info.Size()==0 {
    t.Fatal("PAPER_UI_MODEL_NOT_PUBLISHED")
  }
  // This is a manually injected display observation, not an automatic fill
  // produced by the PAPER engine. It must never be labeled an accounting fill.
  fillModelStart:=time.Now()
  aom.ObserveDashboardOrder(UserOrderUpdate{
    OrderID:expectedOrderID,ClientOrderID:requestID,
    ProductID:n.Signal.ProductID,Side:"BUY",Status:"FILLED",
    LimitPrice:76500,CumulativeQuantity:0.0001,LeavesQuantity:0,
    EventTime:time.Now().Add(time.Millisecond),
  })
  filledRows:=aom.dashboardOrderSnapshot(n.Signal.ProductID)
  fillModelUs:=time.Since(fillModelStart).Microseconds()
  if len(filledRows)!=0 {t.Fatal("PAPER_DISPLAY_TERMINAL_FILL_STILL_WORKING")}
  finalPosition:=pm.Snapshot()
  if finalPosition.Quantity!=before.Quantity||finalPosition.CostBasis!=before.CostBasis {
    t.Fatal("PAPER_DISPLAY_EVENT_INVENTED_FINANCIAL_ACCOUNTING")
  }
  trace:=n.timing.snapshot("RC2Q",nil,true)
  var receiptSyncUs,trancheSyncUs,evidenceSyncUs int64
  for _,s:=range trace.Spans {
    duration:=int64(s.DurationMS*1000)
    switch s.Stage {
    case "receipt.required_sync":receiptSyncUs+=duration
    case "tranche.required_sync":trancheSyncUs+=duration
    case "evidence.required_sync":evidenceSyncUs+=duration
    }
  }
  // No IDs, order payloads, financial/account values, file paths or secrets
  // may be emitted in a public FORGE Actions log.
  t.Logf("RC2Q_BOUNDARY admission_to_ready_us=%d ready_to_result_us=%d result_to_return_us=%d total_submission_us=%d receipt_sync_us=%d tranche_sync_us=%d evidence_sync_us=%d duplicate_us=%d ui_model_us=%d ui_publish_atomic_us=%d injected_display_fill_us=%d network_calls=%d paper_reservations=%d requests=%d receipts=%d",
    readyAt.Sub(entryStart).Microseconds(),resultAt.Sub(readyAt).Microseconds(),
    returnedAt.Sub(resultAt).Microseconds(),returnedAt.Sub(entryStart).Microseconds(),
    receiptSyncUs,trancheSyncUs,evidenceSyncUs,
    dupDuration.Microseconds(),uiModelUs,uiWriteUs,fillModelUs,
    postHTTP,len(ctrl.state.Reservations),n.Requests,requestReady)
  if strings.TrimSpace(requestID)=="" {t.Fatal("PAPER_PREVIEW_CLIENT_ID_EMPTY")}
}
