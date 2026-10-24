package plane

import (
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"strings"
	"unicode/utf8"
)

const (
	externalReplaceTextMaxPayloadBytes = 64 << 10
	externalReplaceTextMaxFieldBytes   = 32 << 10
)

type externalReplaceTextPayload struct {
	Old string `json:"old"`
	New string `json:"new"`
}

func parseExternalReplaceText(op ExternalOrchestratorEdit) (externalReplaceTextPayload, error) {
	var payload externalReplaceTextPayload
	if op.Type != "replace_text" || op.Content == "" || len([]byte(op.Content)) > externalReplaceTextMaxPayloadBytes ||
		!utf8.ValidString(op.Content) || strings.HasPrefix(op.Content, "\ufeff") || strings.ContainsRune(op.Content, '\x00') {
		return payload, errors.New("EXTERNAL_REPAIR_REPLACE_PAYLOAD_INVALID")
	}
	if err := json.Unmarshal([]byte(op.Content), &payload); err != nil {
		return payload, errors.New("EXTERNAL_REPAIR_REPLACE_PAYLOAD_INVALID")
	}
	if payload.Old == "" || len([]byte(payload.Old)) > externalReplaceTextMaxFieldBytes || len([]byte(payload.New)) > externalReplaceTextMaxFieldBytes ||
		!utf8.ValidString(payload.Old) || !utf8.ValidString(payload.New) ||
		strings.ContainsRune(payload.Old, '\x00') || strings.ContainsRune(payload.New, '\x00') {
		return payload, errors.New("EXTERNAL_REPAIR_REPLACE_PAYLOAD_INVALID")
	}
	return payload, nil
}

func validateExternalReplaceText(before []byte, op ExternalOrchestratorEdit) error {
	payload, err := parseExternalReplaceText(op)
	if err != nil {
		return err
	}
	count := bytes.Count(before, []byte(payload.Old))
	if count != 1 {
		return fmt.Errorf("EXTERNAL_REPAIR_REPLACE_MATCH_COUNT: %d", count)
	}
	resultSize := len(before) - len([]byte(payload.Old)) + len([]byte(payload.New))
	if resultSize < 0 || resultSize > 4<<20 {
		return errors.New("EXTERNAL_REPAIR_REPLACE_RESULT_TOO_LARGE")
	}
	return nil
}

func applyExternalReplaceText(target string, before []byte, mode os.FileMode, op ExternalOrchestratorEdit) error {
	if err := validateExternalReplaceText(before, op); err != nil {
		return err
	}
	payload, _ := parseExternalReplaceText(op)
	after := bytes.Replace(before, []byte(payload.Old), []byte(payload.New), 1)
	if mode == 0 {
		mode = 0600
	}
	return os.WriteFile(target, after, mode)
}
