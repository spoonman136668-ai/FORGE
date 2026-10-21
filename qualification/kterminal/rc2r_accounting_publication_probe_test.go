package pkg

import (
 "math"
 "os"
 "path/filepath"
 "testing"
 "time"
)

// RC2-R TEST-ONLY instrumentation on frozen original K-Terminal source.
// This exercises the existing confirmed-order accounting reducer with
// synthetic authenticated-equivalent fixture observations. It does not
// invent a live/paper engine fill, alter executable accounting, or paint WPF.
func TestRC2RConfirmedOrderAccountingAndDashboardPublication(t *testing.T) {
 pm, known := coherentOrderFixture(t)
 before := pm.Snapshot()
 update := freshOrder(t,pm,known,"rc2r-fill",0.0004)
 acctStart := time.Now()
 pm.ladderLots.HandleUserOrder(update)
 acctUs := time.Since(acctStart).Microseconds()
 afterStart := time.Now()
 after := pm.Snapshot()
 snapshotUs := time.Since(afterStart).Microseconds()
 if !after.AccountingVerified || after.BasisEstimated ||
    math.Abs(after.Quantity-(before.Quantity+update.CumulativeQuantity))>1e-10 ||
    math.Abs(after.CostBasis-(before.CostBasis+update.FilledValue+update.TotalFees))>1e-6 {
   t.Fatal("RC2R_CONFIRMED_FILL_ACCOUNTING_INCOHERENT")
 }
 rereadStart := time.Now()
 pm.ladderLots.HandleUserOrder(update)
 dupUs := time.Since(rereadStart).Microseconds()
 stable := pm.Snapshot()
 if math.Abs(stable.Quantity-after.Quantity)>1e-10 ||
    math.Abs(stable.CostBasis-after.CostBasis)>1e-6 ||
    stable.AccountingRevision!=after.AccountingRevision {
   t.Fatal("RC2R_DUPLICATE_REAPPLIED_FINANCIAL_EVENT")
 }

 // A dashboard order observation and financial display snapshot are two
 // separate consumers. Their values must be attributed to the reducer.
 aom := &AdvancedOrderManager{}
 observationStart := time.Now()
 aom.ObserveDashboardOrder(update)
 orderRows := aom.dashboardOrderSnapshot(update.ProductID)
 observeUs := time.Since(observationStart).Microseconds()
 modelStart := time.Now()
 financial := &DashboardSnapshot{
    ProductID:update.ProductID,
    Quantity:after.Quantity,
    CostBasis:after.CostBasis,
    BasisVerified:!after.BasisEstimated,
    PositionAccountingVerified:after.AccountingVerified,
    Price:76500,PriceIncrement:0.01,
    OrderEvidence:orderRows,
 }
 model := buildDashboardUIModel(financial)
 modelUs := time.Since(modelStart).Microseconds()
 if model.ProductID!=update.ProductID || model.SchemaVersion!=dashboardUISnapshotSchemaVersion {
    t.Fatal("RC2R_DASHBOARD_CONTRACT_DRIFT")
 }
 file := filepath.Join(t.TempDir(),"rc2r-model.json")
 persistStart := time.Now()
 if err:=writeDashboardUIModel(file,model);err!=nil {t.Fatal(err)}
 publicationUs := time.Since(persistStart).Microseconds()
 readStart := time.Now()
 data,err:=os.ReadFile(file)
 readUs:=time.Since(readStart).Microseconds()
 if err!=nil || len(data)==0 || data[len(data)-1]!='\n' {
   t.Fatal("RC2R_ATOMIC_PUBLISHED_MODEL_UNAVAILABLE")
 }
 // The original app uses a 5s backend snapshot ticker and a 50ms WPF
 // watcher. Those scheduled waits are NOT part of the direct method times.
 t.Logf("RC2R_PHASE account_event_us=%d position_snapshot_us=%d duplicate_event_us=%d order_observe_us=%d model_build_us=%d atomic_publish_us=%d published_file_read_us=%d total_direct_us=%d order_rows=%d",
   acctUs,snapshotUs,dupUs,observeUs,modelUs,publicationUs,readUs,
   acctUs+snapshotUs+dupUs+observeUs+modelUs+publicationUs+readUs,len(orderRows))
}
