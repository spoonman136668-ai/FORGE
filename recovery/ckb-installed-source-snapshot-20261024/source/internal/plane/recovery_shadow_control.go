package plane

import (
	"context"
	"errors"
	"strings"
)

func (p *Engine) SetBlockerResolverMode(ctx context.Context, mode string) (map[string]any, error) {
	p.queueMu.Lock()
	defer p.queueMu.Unlock()

	switch mode {
	case blockerResolverModeOff:
		// Emergency disable remains available without an authority recheck.
	case blockerResolverModeShadow, blockerResolverModeActive:
		if p.setting("paused") != "true" {
			if mode == blockerResolverModeActive {
				return nil, errors.New("BLOCKER_RESOLVER_ACTIVE_REQUIRES_PAUSED_CONTROLLER")
			}
			return nil, errors.New("BLOCKER_RESOLVER_SHADOW_REQUIRES_PAUSED_CONTROLLER")
		}
		if err := p.sourceAuthority(ctx); err != nil {
			return nil, err
		}
	default:
		return nil, errors.New("BLOCKER_RESOLVER_MODE_INVALID")
	}

	if err := p.setSetting(blockerResolverModeSetting, mode); err != nil {
		return nil, err
	}
	status := "MODE_" + strings.ToUpper(mode)
	if err := p.setSetting(blockerResolverStatusSetting, status); err != nil {
		return nil, err
	}
	return map[string]any{
		"mode":                mode,
		"status":              status,
		"production_accepted": false,
		"resume_authorized":   false,
	}, nil
}
