package pkg

import (
    "encoding/json"
    "fmt"
    "math"
    "os"
    "path/filepath"
    "testing"
    "time"
)

// RC2-T test-only: original confirmed-order reducer and original dashboard
// publication function, on a frozen source and isolated synthetic worktree.
// There is no exchange, broker, installed trading app, or live authorization.
func TestRC2TCorrelatedSyntheticConfirmedEventAndDashboardPublication(t *testing.T) {
    root := os.Getenv("KTERM_RC2T_ROOT")
    if root == "" { t.Fatal("RC2T_ISOLATED_ROOT_REQUIRED") }
    info, err := os.Stat(root)
    if err != nil || !info.IsDir() { t.Fatal("RC2T_ROOT_INVALID") }
    prior, err := os.Getwd()
    if err != nil { t.Fatal(err) }
    if err := os.Chdir(root); err != nil { t.Fatal(err) }
    t.Cleanup(func(){ _ = os.Chdir(prior) })
    t.Setenv("K_TERMINAL_GUI_MODE","1")
    if err := os.MkdirAll(filepath.Join(root,"data"),0700);err!=nil{t.Fatal(err)}

    // Preserve two distinct accounting events; first publishes immediately,
    // second illustrates the unmodified source's 5s ticker interval. These
    // are NOT asserted to be the actual application's fully initialized
    // TerminalDashboard.Start. The periodic timing remains labeled a model.
    type record struct {
        Phase string `json:"phase"`
        AccountingStartedNs int64 `json:"accounting_started_ns"`
        AccountingCompletedNs int64 `json:"accounting_completed_ns"`
        SnapshotPreparedNs int64 `json:"snapshot_prepared_ns"`
        PublishedNs int64 `json:"published_ns"`
        ModelUpdatedAtNs int64 `json:"model_updated_at_ns"`
        ModelUpdatedAt string `json:"model_updated_at"`
        Quantity float64 `json:"quantity"`
        SourceTickerSimulated bool `json:"source_ticker_simulated"`
    }
    records:=make([]record,0,2)
    ticker:=time.NewTicker(time.Duration(defaultDashboardRefreshSeconds)*time.Second)
    defer ticker.Stop()
    for k:=0;k<2;k++{
        pm, known := coherentOrderFixture(t)
        before:=pm.Snapshot()
        update:=freshOrder(t,pm,known,fmt.Sprintf("rc2t-synthetic-%d",k),0.0004)
        begin:=time.Now()
        pm.ladderLots.HandleUserOrder(update)
        completed:=time.Now()
        after:=pm.Snapshot()
        if !after.AccountingVerified||after.BasisEstimated||
           math.Abs(after.Quantity-before.Quantity-update.CumulativeQuantity)>1e-10{
           t.Fatal("RC2T_ACCOUNTING_INTEGRITY_FAILURE")
        }
        if k==1{
            select {
            case <-ticker.C:
            case <-time.After(7*time.Second):t.Fatal("RC2T_BACKEND_TICKER_MODEL_TIMEOUT")
            }
        }
        snap:=&DashboardSnapshot{
           ProductID:"BTC-USDC",PriceIncrement:0.01,MarketValue:76500,
           LastUpdated:time.Now().UTC(),
           AvailableCash:500,TotalCash:500,Equity:500+after.Quantity*76500,
           Quantity:after.Quantity,TrackedQuantity:after.Quantity,
           CostBasis:after.CostBasis,AverageBuy:after.AverageBuy,
           RealizedPnL:after.RealizedPnL,PositionAccountingVerified:after.AccountingVerified,
           BasisVerified:!after.BasisEstimated,BasisDisplayKnown:true,
           AccountingStatus:string(after.AccountingStatus),
        }
        prepared:=time.Now()
        publishDashboardUISnapshot(snap,nil)
        published:=time.Now()
        bytes,err:=os.ReadFile(filepath.Join(root,"data","ui-dashboard.json"))
        if err!=nil || len(bytes)==0 {t.Fatal("RC2T_REAL_PUBLISHER_DID_NOT_WRITE")}
        var model DashboardUIModel
        if json.Unmarshal(bytes,&model)!=nil||
           model.UpdatedAt.IsZero()||model.ProductID!="BTC-USDC"{
           t.Fatal("RC2T_DASHBOARD_WIRE_MODEL_INVALID")
        }
        records=append(records,record{
            Phase:[]string{"immediate","five_second_ticker_model"}[k],
            AccountingStartedNs:begin.UnixNano(),
            AccountingCompletedNs:completed.UnixNano(),
            SnapshotPreparedNs:prepared.UnixNano(),
            PublishedNs:published.UnixNano(),
            ModelUpdatedAtNs:model.UpdatedAt.UnixNano(),
            ModelUpdatedAt:model.UpdatedAt.Format(time.RFC3339Nano),
            Quantity:after.Quantity,SourceTickerSimulated:k==1,
        })
        // The consumer independently correlates the current actual JSON
        // UpdatedAt timestamp, not synthetic runtime IDs or order secrets.
        t.Logf("RC2T_PHASE index=%d accounting_us=%d wait_before_publish_us=%d publish_us=%d",k,
            completed.Sub(begin).Microseconds(),
            prepared.Sub(completed).Microseconds(),
            published.Sub(prepared).Microseconds())
        if k==0 {time.Sleep(200*time.Millisecond)}
    }
    blob,err:=json.Marshal(records)
    if err!=nil {t.Fatal(err)}
    if err:=os.WriteFile(filepath.Join(root,"producer-trace.json"),blob,0600);err!=nil{t.Fatal(err)}
    t.Log("RC2T_NATIVE_REDUCER_AND_PRODUCTION_UI_PUBLISHER=PASS")
}
