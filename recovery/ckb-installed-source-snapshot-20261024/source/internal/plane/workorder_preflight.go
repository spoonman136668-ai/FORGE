package plane

import (
	"errors"
	"fmt"
	"strings"
)

// validateWorkOrderPreflight rejects deterministic orchestration-contract defects
// before a source work order can enter the queue. It does not inspect or change
// candidate source, authority policy, accepted refs, or runtime state.
func validateWorkOrderPreflight(w WorkOrder) error {
	uiRequired := len(w.Preserve) > 0 || w.Acceptance.Browser
	if !uiRequired {
		return nil
	}
	if w.UI.Root == "" || len(w.UI.Pages) == 0 {
		return errors.New("UI_CONTRACT_INVALID: explicit UI root and pages required for preserve/browser acceptance")
	}
	for _, name := range w.Preserve {
		if name == "element_ids" || name == "data_attributes" {
			continue
		}
		markers := w.UI.Markers[name]
		if len(markers) == 0 {
			return fmt.Errorf("UI_CONTRACT_INVALID: missing explicit markers for %s", name)
		}
		seen := map[string]bool{}
		for _, marker := range markers {
			if strings.TrimSpace(marker) == "" {
				return fmt.Errorf("UI_CONTRACT_INVALID: empty marker for %s", name)
			}
			if seen[marker] {
				return fmt.Errorf("UI_CONTRACT_INVALID: duplicate marker for %s", name)
			}
			seen[marker] = true
		}
	}
	return nil
}
