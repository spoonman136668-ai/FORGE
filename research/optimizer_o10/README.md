# O10 public-development encoding-versus-readout diagnostic

This branch tests the **mechanism bottleneck**, not a new scientific result.
The frozen protocol was committed before any O10 model or source generation.

## What is learned

The original O9 implementation is copied byte-identically. New source-only
PUBLIC_TRAIN histories train the 57-parameter external memory and 57-parameter
GRU independently, with seed selection only on PUBLIC_SELECT. After selection,
the recurrent weights and original output head are frozen.

Linear binary probes are trained on hidden query-time state to predict
public initial cue, public accumulated action parity, and the query outcome.
A quadratic public-state probe tests a specific nonlinear readout bottleneck.
All probes are trained on PUBLIC_TRAIN and evaluated on untouched PUBLIC_DEV.
Query-current-only and hand-engineered episode-history controls are fitted on
the same public TRAIN set.

## Evidence interpretation

* Cue/parity probe gains over the matched current-only probe indicate
  **decodability of public history from the frozen learned state**, not
  necessarily causal generalization.
* Refit-readout improvements over the original end-to-end head may indicate
  an optimization or readout limitation, but probe training adds supervision
  and computational cost. Every extra cost is recorded.
* If parity is not decodable while cue is, failure occurs no later than
  parity retention or representation. Failure of a linear probe alone does
  not establish information absence.
* The original output head, the separate readout probes, and a distinct
  explicit public cue/parity control are NOT equal-supervision or
  equal-parameter comparisons. The two recurrent training architectures
  alone have matched 57 trainable parameters.
* Synthetic sources and public development cannot prove unfamiliar-source
  transfer or scientific superiority. NULL-family performance is retained.

## Disposition

Keep every positive and negative, preserve the original O9 failed and passed
qualifications, never retune the frozen DEV identity or promote a model from
these synthetic probes. Do not merge draft research into main without a
separate authority and qualification decision. Scientific first use is
untouched.
