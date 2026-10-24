package plane

const (
	mindPalaceWebUIContextOperationID    = "mind-palace-context"
	mindPalaceWebUIContextQueryPattern   = "^[A-Za-z0-9][A-Za-z0-9 .,_?=-]{0,255}$"
	mindPalaceWebUIContextProjectPattern = "^[A-Za-z0-9][A-Za-z0-9 ._-]{0,79}$"
)

func mindPalaceWebUIContextValidSHA256(value string) bool {
	if len(value) != 64 {
		return false
	}
	for _, c := range value {
		if (c < '0' || c > '9') && (c < 'a' || c > 'f') {
			return false
		}
	}
	return true
}

func mindPalaceWebUIContextRegisteredOperation(registry *LocalOperationRegistry) (LocalOperation, bool) {
	if registry == nil {
		return LocalOperation{}, false
	}
	op, ok := registry.byID[mindPalaceWebUIContextOperationID]
	if !ok ||
		op.Class != "diagnostic" ||
		op.Script != "operations/Read-MindPalaceContext.ps1" ||
		!mindPalaceWebUIContextValidSHA256(op.ScriptSHA256) ||
		op.TimeoutSeconds != 60 ||
		len(op.Arguments) != 2 {
		return LocalOperation{}, false
	}
	query := op.Arguments[0]
	project := op.Arguments[1]
	if query.Name != "Query" ||
		query.Type != "string" ||
		!query.Required ||
		query.Pattern != mindPalaceWebUIContextQueryPattern ||
		query.MaxLength != 256 ||
		project.Name != "Project" ||
		project.Type != "string" ||
		project.Required ||
		project.Pattern != mindPalaceWebUIContextProjectPattern ||
		project.MaxLength != 80 {
		return LocalOperation{}, false
	}
	return op, true
}

func mindPalaceWebUIContextAvailable(registry *LocalOperationRegistry) bool {
	_, ok := mindPalaceWebUIContextRegisteredOperation(registry)
	return ok
}

func mindPalaceWebUIContextRegisteredSHA256(registry *LocalOperationRegistry) string {
	op, ok := mindPalaceWebUIContextRegisteredOperation(registry)
	if !ok {
		return ""
	}
	return op.ScriptSHA256
}

func mindPalaceWebUIContextDescriptor(scriptSHA256 string) map[string]any {
	if !mindPalaceWebUIContextValidSHA256(scriptSHA256) {
		return nil
	}
	return map[string]any{
		"provider":              "mind-palace",
		"mode":                  "on-demand",
		"action":                "local-exec",
		"operation_id":          mindPalaceWebUIContextOperationID,
		"input_sha256":          scriptSHA256,
		"generation_required":   true,
		"context_schema":        "ckb-plane.mind-palace-context.v1",
		"query_max_length":      256,
		"query_pattern":         mindPalaceWebUIContextQueryPattern,
		"query_policy":          "Summarize the task into safe retrieval terms; do not copy shell syntax, paths, URLs, credentials, or secrets.",
		"project_optional":      true,
		"project_pattern":       mindPalaceWebUIContextProjectPattern,
		"advisory_only":         true,
		"authorizes_execution":  false,
		"authorizes_acceptance": false,
		"usage_policy":          "For project, repository, prior-work, historical-decision, or authority questions, request a task-scoped Mind-Palace context pack before planning or answering when relevant context is not already present and fresh.",
	}
}
