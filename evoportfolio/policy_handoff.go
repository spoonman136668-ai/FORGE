package evoportfolio

// OptimizedHandoff is an immutable association between training-only policy
// replay and a separately frozen diverse portfolio. Neither grants dispatch.
type OptimizedHandoff struct {
 Policy PolicyReplay `json:"policy"`
 Portfolio Handoff `json:"portfolio"`
 Next Progression `json:"next"`
 DispatchAuthorized bool `json:"dispatch_authorized"`
}

// PlanAfterReplay is the read-only integration boundary for Wingless/Yggdrasil.
// Historical policy improvement cannot silently alter the already-frozen
// candidate portfolio, its scientific budget, or its selected finalists.
func PlanAfterReplay(history PolicyFreeze,historyPin string,
 portfolio Frozen,portfolioPin string)(OptimizedHandoff,error){
 var zero OptimizedHandoff
 policy,err:=ReplayFrozenPolicies(history,historyPin)
 if err!=nil{return zero,err}
 if history.Lane!=portfolio.Lane{return zero,ErrFrozen}
 handoff,err:=BuildHandoff(portfolio,portfolioPin)
 if err!=nil{return zero,err}
 next,err:=NextAdvisory(handoff,nil)
 if err!=nil{return zero,err}
 if next.DispatchAuthorized||handoff.DispatchAuthorized||policy.DispatchAuthorized{
  return zero,ErrFrozen
 }
 return OptimizedHandoff{Policy:policy,Portfolio:handoff,Next:next},nil
}
