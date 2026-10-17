// Package largegraph is a public-development, label-free typed graph index.
// It does not parse language, predict answers, qualify science, or replace F95.
package largegraph

import (
	"bytes"
	"errors"
	"sort"
	"unicode/utf8"
)

const (
	MaxSourceBytes = 7_000_000
	MaxRows        = 150_000
	MaxNodes       = 50_000
	MaxRoles       = 128
	MaxFieldBytes  = 512
	MaxSteps       = 3
	MaxFrontier    = 4_096
)

var (
	ErrSource = errors.New("FORGE_F100O_SOURCE_GRAPH_UNQUALIFIED")
	ErrBudget = errors.New("FORGE_F100O_SOURCE_OR_QUERY_BUDGET_EXCEEDED")
	ErrQuery  = errors.New("FORGE_F100O_QUERY_NOT_FROZEN_TYPED_ROLES")
)

type Direction uint8

const (
	Forward Direction = 1
	Reverse Direction = 2
)

type Step struct {
	Role      string
	Direction Direction
}

type arc struct {
	role string
	dir  Direction
}

type triple struct {
	from string
	role string
	to   string
}

type Stats struct {
	SourceRows        int `json:"source_rows"`
	DistinctTriples   int `json:"distinct_triples"`
	DuplicateRows     int `json:"duplicate_rows"`
	SelfRelations     int `json:"self_relations"`
	DistinctEntities  int `json:"distinct_entities"`
	DistinctRoles     int `json:"distinct_roles"`
	SearchableArcs    int `json:"searchable_directional_arcs"`
}

type Index struct {
	graph map[string]map[arc][]string
	stats Stats
}

func validField(s string) bool {
	return len(s) > 0 && len(s) <= MaxFieldBytes &&
		utf8.ValidString(s) && !bytes.ContainsAny([]byte(s), "\x00\r\n|")
}

// Compile consumes a complete byte-bounded source file, not selected rows.
// Source triples remain case-sensitive. Search index deduplicates exact triples
// while accounting for every source row in immutable aggregate statistics.
func Compile(data []byte) (*Index, error) {
	if len(data) == 0 {
		return nil, ErrSource
	}
	if len(data) > MaxSourceBytes {
		return nil, ErrBudget
	}
	if data[len(data)-1] == '\n' {
		data = data[:len(data)-1]
	}
	// No hidden empty interior or trailing rows are accepted.
	rawRows := bytes.Split(data, []byte{'\n'})
	if len(rawRows) == 0 || len(rawRows) > MaxRows {
		return nil, ErrBudget
	}
	index := &Index{graph: make(map[string]map[arc][]string)}
	seen := make(map[triple]struct{})
	nodes := make(map[string]struct{})
	roles := make(map[string]struct{})
	st := Stats{SourceRows: len(rawRows)}
	for _, row := range rawRows {
		fields := bytes.Split(row, []byte{'|'})
		if len(fields) != 3 {
			return nil, ErrSource
		}
		from, role, to := string(fields[0]), string(fields[1]), string(fields[2])
		if !validField(from) || !validField(role) || !validField(to) {
			return nil, ErrSource
		}
		nodes[from] = struct{}{}
		nodes[to] = struct{}{}
		roles[role] = struct{}{}
		if len(nodes) > MaxNodes || len(roles) > MaxRoles {
			return nil, ErrBudget
		}
		t := triple{from: from, role: role, to: to}
		if _, present := seen[t]; present {
			st.DuplicateRows++
			continue
		}
		seen[t] = struct{}{}
		if from == to {
			st.SelfRelations++
		}
		if index.graph[from] == nil {
			index.graph[from] = make(map[arc][]string)
		}
		if index.graph[to] == nil {
			index.graph[to] = make(map[arc][]string)
		}
		index.graph[from][arc{role: role, dir: Forward}] = append(index.graph[from][arc{role: role, dir: Forward}], to)
		index.graph[to][arc{role: role, dir: Reverse}] = append(index.graph[to][arc{role: role, dir: Reverse}], from)
	}
	for _, neighbors := range index.graph {
		for key, list := range neighbors {
			sort.Strings(list)
			neighbors[key] = list
		}
	}
	st.DistinctTriples = len(seen)
	st.DistinctEntities = len(nodes)
	st.DistinctRoles = len(roles)
	st.SearchableArcs = 2 * len(seen)
	index.stats = st
	return index, nil
}

func (i *Index) Statistics() Stats {
	if i == nil {
		return Stats{}
	}
	return i.stats
}

type Resolution struct {
	Targets      []string
	Steps        int
	Candidates   int
	UniqueTarget bool
}

// Resolve interprets ONLY explicitly supplied role/direction steps.
// No answer, natural-language question, scoring, prediction, or training API.
// Exceeding a frontier budget fails the WHOLE query without truncation.
func (i *Index) Resolve(root string, steps []Step) (Resolution, error) {
	if i == nil || i.graph == nil || !validField(root) ||
		len(steps) < 1 || len(steps) > MaxSteps {
		return Resolution{}, ErrQuery
	}
	for _, s := range steps {
		if !validField(s.Role) || (s.Direction != Forward && s.Direction != Reverse) {
			return Resolution{}, ErrQuery
		}
	}
	frontier := map[string]struct{}{root: {}}
	for _, step := range steps {
		next := make(map[string]struct{})
		for from := range frontier {
			for _, to := range i.graph[from][arc{role: step.Role, dir: step.Direction}] {
				next[to] = struct{}{}
				if len(next) > MaxFrontier {
					return Resolution{}, ErrBudget
				}
			}
		}
		if len(next) == 0 {
			return Resolution{Steps: len(steps)}, nil
		}
		frontier = next
	}
	targets := make([]string, 0, len(frontier))
	for to := range frontier {
		targets = append(targets, to)
	}
	sort.Strings(targets)
	return Resolution{
		Targets: targets, Steps: len(steps), Candidates: len(targets),
		UniqueTarget: len(targets) == 1,
	}, nil
}
