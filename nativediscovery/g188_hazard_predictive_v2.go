// RAR G188: versioned, development-only, hazard-consistent predictive scoring.
// Original frozen F36/F37/F38 observers and their historic reports remain untouched.
package nativediscovery

import (
 "errors"
 "math"
)

var errG188 = errors.New("FORGE_RAR_G188_PREDICTIVE_V2_INVALID_SOURCE")

// g188HazardStatePriorV2 produces a *pre-observation* prior using the same
// 5% template hazard as the unchanged F36/F37/F38 posterior update.
// No policy state is mutated and no hidden physical truth is accessed.
func g188HazardStatePriorV2(m f36Model, t, cue, action int, eps float64) ([4][16]float64, [4]float64, error) {
 var empty [4][16]float64
 var mixed [4]float64
 if !m.Have || (m.Kind != "compositional-issued-memory" && m.Kind != "two-bank-issued-bayes" && m.Kind != "pooled-issued-bayes") || (eps != 0 && eps != F37Epsilon) {
  return empty, mixed, errG188
 }
 sum := 0.0
 for _, weight := range m.Weights {
  if math.IsNaN(weight) || math.IsInf(weight, 0) || weight < 0 || weight > 1 {
   return empty, mixed, errG188
  }
  sum += weight
 }
 if math.Abs(sum-1) > 1e-9 {
  return empty, mixed, errG188
 }
 prior, err := f37NextPrior(m, t, cue, action, eps)
 if err != nil {
  return empty, mixed, errG188
 }
 for k := 0; k < 4; k++ {
  mass := 0.0
  for _, p := range prior[k] {
   if math.IsNaN(p) || math.IsInf(p, 0) || p < 0 || p > 1+1e-9 {
    return empty, mixed, errG188
   }
   mass += p
  }
  if math.Abs(mass-1) > 1e-9 {
   return empty, mixed, errG188
  }
  mixed[k] = .95*m.Weights[k] + .05/4
 }
 return prior, mixed, nil
}

// g188SensorProbabilityV2 sees online state and real noisy observations only.
// No clean scorer truth is accepted by this API. A caller must explicitly
// clamp for NLL (historical floor 1e-12); this function returns raw P(obs).
func g188SensorProbabilityV2(m f36Model, t, cue, action int, observed [2]int, eps float64) (float64, error) {
 if observed[0] < 0 || observed[0] > 15 || observed[1] < 0 || observed[1] > 15 {
  return 0, errG188
 }
 prior, mixed, err := g188HazardStatePriorV2(m, t, cue, action, eps)
 if err != nil {
  return 0, err
 }
 p := 0.0
 for k := 0; k < 4; k++ {
  z := 0.0
  for s := 0; s < 16; s++ {
   z += prior[k][s] * f36Likelihood(observed, s)
  }
  p += mixed[k] * z
 }
 if math.IsNaN(p) || math.IsInf(p, 0) || p < 0 || p > 1+1e-9 {
  return 0, errG188
 }
 return p, nil
}

// g188CleanProbabilityScorerOnlyV2 is SCORER/TEST ONLY. Clean physical truth
// must never be supplied to an observer, learner, policy or controller.
func g188CleanProbabilityScorerOnlyV2(m f36Model, t, cue, action, clean int, eps float64) (float64, error) {
 if clean < 0 || clean > 15 {
  return 0, errG188
 }
 prior, mixed, err := g188HazardStatePriorV2(m, t, cue, action, eps)
 if err != nil {
  return 0, err
 }
 p := 0.0
 for k := 0; k < 4; k++ {
  p += mixed[k] * prior[k][clean]
 }
 if math.IsNaN(p) || math.IsInf(p, 0) || p < 0 || p > 1+1e-9 {
  return 0, errG188
 }
 return p, nil
}
