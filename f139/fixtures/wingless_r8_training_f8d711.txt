package outcome

import (
    "errors"

    r1 "github.com/spoonman136668-ai/Wingless/research/native/itd02/r1"
)

// PublicConsequence is the observed result of the learner's actually selected
// action. It deliberately carries no source-private state or environment info.
type PublicConsequence struct {
    After r1.PublicGrid
    Reward float64
    Terminal bool
    Truncated bool
}

// PublicEnvironment is supplied by a separately authorized source owner.
// The model chooses its own action; the environment returns the actual public
// consequence. Implementations MUST NOT grant protected first-use implicitly.
type PublicEnvironment interface {
    ResetPublic() (r1.PublicGrid, error)
    StepPublic(action int) (PublicConsequence, error)
}

type TrainingSession struct {
    Learner *Selected
    MinimumSelectedSamples uint32
    MaximumEpisodeSteps uint32
    // Process-local fail-closed custody. Cross-process reconciliation belongs
    // to the original source owner and is NOT implemented by these flags.
    quarantined bool
    checkpointUnconfirmed bool
}

// EpisodeResult is a development-only observation, not an accepted scientific
// outcome. Each accepted feedback event is reflected in the native checkpoint.
type EpisodeResult struct {
    Steps uint32
    CumulativeReward float64
    Terminal bool
    Truncated bool
    NativeUpdates uint64
}

// RunEpisode runs the existing native R8 selected-action learner against one
// source-owner-operated PUBLIC episode. No LLM, optimizer, scheduler or newly
// introduced policy substitutes for its trained native action decisions.
//
// If StepPublic fails or a returned public consequence is invalid, this method
// fails CLOSED with the original selected action still armed. It never retries
// an ambiguous source step, fabricates a terminal, or advances learned state
// from an unobserved transition. The caller must reconcile source custody.
func (s *TrainingSession) RunEpisode(env PublicEnvironment) (EpisodeResult, []byte, error) {
    var zero EpisodeResult
    if s == nil { return zero, nil, errors.New("OUTCOME_SELF_TRAINING_NIL_SESSION") }
    if s.quarantined || s.checkpointUnconfirmed {
        return zero, nil, errors.New("OUTCOME_SELF_TRAINING_SOURCE_CUSTODY_UNCONFIRMED")
    }
    if s.Learner == nil || s.Learner.Policy == nil ||
        s.Learner.Rewards == nil || env == nil ||
        s.MinimumSelectedSamples < 2 || s.MaximumEpisodeSteps < 1 ||
        s.MaximumEpisodeSteps > 4096 ||
        !s.Learner.Policy.Healthy() || !s.Learner.Rewards.Valid() ||
        s.Learner.Policy.Armed || s.Learner.Policy.EpisodeSteps != 0 &&
            !s.Learner.Rewards.Closed {
        return zero, nil, errors.New("OUTCOME_SELF_TRAINING_NOT_AT_EPISODE_BOUNDARY")
    }
    // A new source reset is an external operation. Do not reset model history
    // before the source agrees to begin this episode.
    before, err := env.ResetPublic()
    if err != nil {
        s.quarantined = true
        return zero, nil, err
    }
    if s.Learner.Rewards.Closed {
        if err := s.Learner.BeginEpisode(); err != nil {
            s.quarantined = true
            return zero, nil, err
        }
    }
    var result EpisodeResult
    for step := uint32(0); step < s.MaximumEpisodeSteps; step++ {
        action, err := s.Learner.ChooseRewardExplore(
            before, s.MinimumSelectedSamples)
        if err != nil {
            return zero, nil, err
        }
        observed, err := env.StepPublic(action)
        if err != nil {
            // Original pending selection remains armed. No retry.
            s.quarantined = true
            return zero, nil, err
        }
        event := Event{
            ID: s.Learner.Rewards.NextID, Action: action,
            Reward: observed.Reward, Terminal: observed.Terminal,
            Truncated: observed.Truncated,
        }
        if err := s.Learner.Feedback(before, action, observed.After, event); err != nil {
            s.quarantined = true
            return zero, nil, err
        }
        result.Steps++
        result.CumulativeReward += observed.Reward
        before = observed.After
        if observed.Terminal || observed.Truncated {
            result.Terminal = observed.Terminal
            result.Truncated = observed.Truncated
            result.NativeUpdates = s.Learner.Policy.LiveSeen
            checkpoint, err := s.Learner.SnapshotSelected()
            if err != nil {
                s.quarantined = true
                return zero, nil, err
            }
            // A returned snapshot is not a durable owner-acknowledged save.
            // Do not permit another RunEpisode on this session before custody.
            s.checkpointUnconfirmed = true
            return result, checkpoint, nil
        }
    }
    // Never invent an environment termination to fit a training budget.
    s.quarantined = true
    return zero, nil, errors.New("OUTCOME_SELF_TRAINING_SOURCE_EPISODE_NOT_TERMINATED")
}

// TrainBounded drives finite source-owned episodes with native experience
// updates. The checkpoint sink must persist the exact completed-episode state
// and may reject it. Failure stops immediately; no episode is replayed.
// Source owner remains responsible for episode provenance, permissions,
// source-step identity, and durable crash/ambiguous-write reconciliation.
func (s *TrainingSession) TrainBounded(
    env PublicEnvironment, episodes uint32, save func([]byte) error,
) ([]EpisodeResult, error) {
    if episodes < 1 || episodes > 128 || save == nil {
        return nil, errors.New("OUTCOME_SELF_TRAINING_BUDGET_INVALID")
    }
    results := make([]EpisodeResult, 0, episodes)
    for i := uint32(0); i < episodes; i++ {
        result, checkpoint, err := s.RunEpisode(env)
        if err != nil {
            return results, err
        }
        if err := save(checkpoint); err != nil {
            // Ambiguous writes cannot be reconciled by retrying within the
            // session. Even a later successful write would not prove identity.
            s.quarantined = true
            return results, err
        }
        // The owner-provided callback acknowledged exactly this checkpoint.
        s.checkpointUnconfirmed = false
        results = append(results, result)
    }
    return results, nil
}
