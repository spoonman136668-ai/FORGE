package pkg

import (
    "net/http"
    "sort"
    "testing"
    "time"
)

// RC2-N transient test-only overlay. It is copied into a temporary checkout
// after source SHA verification, never committed to K-Terminal and never used
// to launch or submit a live order. The authentic 2s limit and all nine
// attempts remain unchanged.
type rc2nPhase struct {
    attempt int
    makerPosts int
    cancelUs int64
    confirmUs int64
    dispatchUs int64
    postUs int64
    postCalls int
    balanceHookUs int64
    balanceHookCalls int
    bookHookUs int64
    bookCalls int
    sinceStartUs int64
    sinceReceiptUs int64
    remainingUs int64
}

func TestRC2NNineMakerAttemptsMeasuredUnderOriginalDeadline(t *testing.T) {
    fixtureStart := time.Now()
    f := newCanceledBuyStage2Fixture(t)
    fixtureUs := time.Since(fixtureStart).Microseconds()
    receipt, err := time.Parse(time.RFC3339Nano, f.n.Signal.ReceivedAt)
    if err != nil {
        t.Fatal(err)
    }
    phases := make([]rc2nPhase, makerOnlyAttemptsBeforeFallback)
    current := 0

    // Observe synchronous native callbacks without changing return values or
    // the real retry state machine. All accounting and broker rules are intact.
    oldPost := f.post
    f.post = func(i int, req *AdvancedOrderRequest) (result *http.Response, callErr error) {
        begin := time.Now()
        result, callErr = oldPost(i, req)
        p := &phases[current]
        p.postCalls++
        p.postUs += time.Since(begin).Microseconds()
        return result, callErr
    }
    oldDispatch := f.retry.dispatch
    f.retry.dispatch = func(candidate nativeCanceledBuyCandidate, order Order) {
        begin := time.Now()
        oldDispatch(candidate, order)
        phases[current].dispatchUs += time.Since(begin).Microseconds()
    }
    oldBeforeAccounts := f.beforeAccounts
    f.beforeAccounts = func() {
        begin := time.Now()
        if oldBeforeAccounts != nil {
            oldBeforeAccounts()
        }
        phases[current].balanceHookCalls++
        phases[current].balanceHookUs += time.Since(begin).Microseconds()
    }
    oldBeforeBook := f.beforeBook
    f.beforeBook = func(i int) {
        begin := time.Now()
        if oldBeforeBook != nil {
            oldBeforeBook(i)
        }
        phases[current].bookCalls++
        phases[current].bookHookUs += time.Since(begin).Microseconds()
    }

    // Emit collected numbers even if an original assertion aborts the test.
    t.Cleanup(func() {
        t.Logf("RC2N_FIXTURE fixture_us=%d initial_age_us=%d receipt_age_us=%d original_limit_us=%d", fixtureUs,
            time.Since(f.n.Started).Microseconds(), time.Since(receipt).Microseconds(),
            nativeCanceledBuyRetryWindow.Microseconds())
        // The native runtime already records named, source-local timing
        // subspans. Read its immutable snapshot; never publish identities.
        record := f.n.timing.snapshot("RC2N", nil, true)
        type spanTotals struct { calls int; totalUs int64; peakUs int64 }
        spanStats := make(map[string]spanTotals)
        for _, v := range record.Spans {
            // Source-authored constant stage labels only, no client IDs.
            safe := true
            for _, ch := range v.Stage {
                if !((ch >= 'a' && ch <= 'z') || (ch >= 'A' && ch <= 'Z') ||
                    (ch >= '0' && ch <= '9') || ch == '_' || ch == '.' || ch == '-') {
                    safe = false
                    break
                }
            }
            if !safe || v.Stage == "" { continue }
            u := int64(v.DurationMS * 1000)
            if u < 0 { continue }
            prev := spanStats[v.Stage]
            prev.calls++
            prev.totalUs += u
            if u > prev.peakUs { prev.peakUs = u }
            spanStats[v.Stage] = prev
        }
        labels := make([]string, 0, len(spanStats))
        for k := range spanStats { labels = append(labels,k) }
        sort.Strings(labels)
        t.Logf("RC2N_NATIVE_SUMMARY span_types=%d dropped_spans=%d total_spans=%d",len(labels),record.DroppedSpans,len(record.Spans))
        for _, label := range labels {
            x := spanStats[label]
            t.Logf("RC2N_NATIVE_SPAN stage=%s calls=%d total_us=%d peak_us=%d",
                label,x.calls,x.totalUs,x.peakUs)
        }
        for _, p := range phases {
            if p.attempt == 0 {
                break
            }
            residualUs := p.confirmUs-p.dispatchUs
            if residualUs < 0 { residualUs = 0 }
            dispatchResidualUs := p.dispatchUs-p.postUs-p.balanceHookUs-p.bookHookUs
            if dispatchResidualUs < 0 { dispatchResidualUs = 0 }
            t.Logf("RC2N_PHASE attempt=%d cancel_us=%d confirm_us=%d dispatch_us=%d dispatch_residual_us=%d confirm_residual_us=%d post_us=%d post_calls=%d balance_hook_us=%d balance_hook_calls=%d book_hook_us=%d book_calls=%d after_posts=%d elapsed_from_start_us=%d elapsed_from_receipt_us=%d deadline_remaining_us=%d",
                p.attempt, p.cancelUs, p.confirmUs, p.dispatchUs, dispatchResidualUs, residualUs,
                p.postUs, p.postCalls, p.balanceHookUs, p.balanceHookCalls,
                p.bookHookUs, p.bookCalls, p.makerPosts, p.sinceStartUs,
                p.sinceReceiptUs, p.remainingUs)
        }
    })

    for i := 1; i <= makerOnlyAttemptsBeforeFallback; i++ {
        current = i-1
        p := &phases[current]
        p.attempt = i
        started := time.Now()
        cancellation := f.cancellation(i, 0)
        p.cancelUs = time.Since(started).Microseconds()
        started = time.Now()
        f.retry.confirm(cancellation)
        p.confirmUs = time.Since(started).Microseconds()
        p.makerPosts = len(f.posts)
        p.sinceStartUs = time.Since(f.n.Started).Microseconds()
        p.sinceReceiptUs = time.Since(receipt).Microseconds()
        p.remainingUs = time.Until(receipt.Add(nativeCanceledBuyRetryWindow)).Microseconds()
        if i < makerOnlyAttemptsBeforeFallback && len(f.posts) != i+1 {
            t.Fatalf("authorized maker budget truncated at %d: reports=%v", i, f.reports)
        }
    }
    if len(f.posts) != 9 || time.Since(f.n.Started) >= nativeCanceledBuyRetryWindow {
        t.Fatalf("full original native maker budget failed: posts=%d elapsed=%s reports=%v",
            len(f.posts), time.Since(f.n.Started), f.reports)
    }
    base := f.posts[0].ClientOrderID
    for i, request := range f.posts {
        if request.ClientOrderID != attemptClientOrderID(base, i+1) ||
            !request.OrderConfiguration.LimitLimitGTC.PostOnly ||
            parseOrderFloat(request.OrderConfiguration.LimitLimitGTC.BaseSize) >
                parseOrderFloat(f.posts[0].OrderConfiguration.LimitLimitGTC.BaseSize) {
            t.Fatalf("attempt identity/policy/quantity changed: %+v", request)
        }
    }
    // Original duplicate-proof idempotence and accounting reservation checks.
    f.retry.confirm(f.cancellation(1, 0))
    if len(f.posts) != 9 {
        t.Fatal("duplicate terminal proof resubmitted an old attempt")
    }
    f.h.tranches.mu.Lock()
    defer f.h.tranches.mu.Unlock()
    if len(f.h.tranches.state.Reservations) != 1 ||
        f.h.tranches.state.Reservations[f.n.Signal.EventID].ClientID != f.posts[8].ClientOrderID {
        t.Fatalf("logical event acquired duplicate reservations: %+v", f.h.tranches.state.Reservations)
    }
}
