package progression

import (
	"bufio"
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"strings"
)

// JournalRecord binds an ordered proposal to its predecessor, preserving
// duplicate-wake evidence without granting any dispatch or acceptance rights.
type JournalRecord struct {
	Schema         string `json:"schema"`
	Sequence       uint64 `json:"sequence"`
	PreviousSHA256 string `json:"previous_sha256"`
	Event          Event  `json:"event"`
	EventSHA256    string `json:"event_sha256"`
	RecordSHA256   string `json:"record_sha256"`
}

type recordPayload struct {
	Schema         string `json:"schema"`
	Sequence       uint64 `json:"sequence"`
	PreviousSHA256 string `json:"previous_sha256"`
	Event          Event  `json:"event"`
	EventSHA256    string `json:"event_sha256"`
}

func recordDigest(r JournalRecord) (string, error) {
	return digest(recordPayload{Schema: r.Schema, Sequence: r.Sequence, PreviousSHA256: r.PreviousSHA256, Event: r.Event, EventSHA256: r.EventSHA256})
}

// ProposeRecord only constructs a content-addressed audit entry. Its caller
// must neither interpret this as evidence authentication nor write to an
// authoritative journal without independent CKB acceptance.
func ProposeRecord(current State, e Event) (JournalRecord, State, bool, error) {
	if !isHash(current.LastRecordSHA256, 64) {
		return JournalRecord{}, State{}, false, errors.New("JOURNAL_TIP_INVALID")
	}
	next, changed, err := Apply(current, e)
	if err != nil {
		return JournalRecord{}, State{}, false, err
	}
	id, err := EventDigest(e)
	if err != nil {
		return JournalRecord{}, State{}, false, err
	}
	r := JournalRecord{Schema: JournalSchema, Sequence: current.Sequence + 1, PreviousSHA256: current.LastRecordSHA256, Event: e, EventSHA256: id}
	r.RecordSHA256, err = recordDigest(r)
	if err != nil {
		return JournalRecord{}, State{}, false, err
	}
	next.Sequence = r.Sequence
	next.LastRecordSHA256 = r.RecordSHA256
	return r, next, changed, nil
}

func ApplyRecord(current State, r JournalRecord) (State, bool, error) {
	if r.Schema != JournalSchema || r.Sequence != current.Sequence+1 || r.PreviousSHA256 != current.LastRecordSHA256 || !isHash(r.PreviousSHA256, 64) {
		return State{}, false, errors.New("JOURNAL_SEQUENCE_OR_PARENT_DRIFT")
	}
	eventHash, err := EventDigest(r.Event)
	if err != nil {
		return State{}, false, err
	}
	if eventHash != r.EventSHA256 {
		return State{}, false, errors.New("JOURNAL_EVENT_HASH_DRIFT")
	}
	contentHash, err := recordDigest(r)
	if err != nil {
		return State{}, false, err
	}
	if contentHash != r.RecordSHA256 {
		return State{}, false, errors.New("JOURNAL_RECORD_HASH_DRIFT")
	}
	next, changed, err := Apply(current, r.Event)
	if err != nil {
		return State{}, false, err
	}
	next.Sequence = r.Sequence
	next.LastRecordSHA256 = r.RecordSHA256
	return next, changed, nil
}

// Replay is bounded, read-only and deterministic. Its stream is never an
// authority source: all external CKB attestation checks must precede it.
// rejectDuplicateKeys prevents syntactically valid but ambiguous JSON maps from
// silently overriding signed journal fields, including nested event values.
func rejectDuplicateKeys(line []byte) error {
	decoder := json.NewDecoder(bytes.NewReader(line))
	var walk func(int) error
	walk = func(depth int) error {
		if depth > 16 {
			return errors.New("JOURNAL_JSON_DEPTH_LIMIT")
		}
		token, err := decoder.Token()
		if err != nil {
			return err
		}
		delim, ok := token.(json.Delim)
		if !ok {
			return nil
		}
		switch delim {
		case '{':
			seen := map[string]bool{}
			for decoder.More() {
				keyToken, err := decoder.Token()
				if err != nil {
					return err
				}
				key, ok := keyToken.(string)
				if !ok {
					return errors.New("JOURNAL_JSON_OBJECT_KEY_INVALID")
				}
				if seen[key] {
					return errors.New("JOURNAL_JSON_DUPLICATE_KEY")
				}
				seen[key] = true
				if err := walk(depth + 1); err != nil {
					return err
				}
			}
			end, err := decoder.Token()
			if err != nil {
				return err
			}
			if end != json.Delim('}') {
				return errors.New("JOURNAL_JSON_OBJECT_TERMINATOR")
			}
		case '[':
			for decoder.More() {
				if err := walk(depth + 1); err != nil {
					return err
				}
			}
			end, err := decoder.Token()
			if err != nil {
				return err
			}
			if end != json.Delim(']') {
				return errors.New("JOURNAL_JSON_ARRAY_TERMINATOR")
			}
		default:
			return errors.New("JOURNAL_JSON_UNEXPECTED_DELIMITER")
		}
		return nil
	}
	if err := walk(0); err != nil {
		return err
	}
	if _, err := decoder.Token(); err != io.EOF {
		return errors.New("JOURNAL_JSON_TRAILING_DATA")
	}
	return nil
}

func Replay(input io.Reader) (State, error) {
	state := NewState()
	scanner := bufio.NewScanner(input)
	scanner.Buffer(make([]byte, 4096), 65536)
	for scanner.Scan() {
		if state.Sequence >= 50000 {
			return State{}, errors.New("JOURNAL_EVENT_LIMIT")
		}
		line := scanner.Bytes()
		if len(strings.TrimSpace(string(line))) == 0 {
			return State{}, errors.New("JOURNAL_EMPTY_LINE")
		}
		if err := rejectDuplicateKeys(line); err != nil {
			return State{}, fmt.Errorf("JOURNAL_NONCANONICAL_JSON: %w", err)
		}
		dec := json.NewDecoder(strings.NewReader(string(line)))
		dec.DisallowUnknownFields()
		var record JournalRecord
		if err := dec.Decode(&record); err != nil {
			return State{}, fmt.Errorf("JOURNAL_INVALID_JSON: %w", err)
		}
		var trailing any
		if err := dec.Decode(&trailing); err != io.EOF {
			return State{}, errors.New("JOURNAL_JSON_TRAILING_DATA")
		}
		next, _, err := ApplyRecord(state, record)
		if err != nil {
			return State{}, fmt.Errorf("JOURNAL_RECORD_%d: %w", record.Sequence, err)
		}
		state = next
	}
	if err := scanner.Err(); err != nil {
		return State{}, fmt.Errorf("JOURNAL_STREAM: %w", err)
	}
	return state, nil
}
