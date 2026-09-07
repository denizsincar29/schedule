// Package core holds the shared orchestration used by the CLI (and future
// consumers). It keeps the window-selection semantics (spec/cli.md) in exactly
// one place so every entry point picks the same days for the same query —
// the Go mirror of py/schedule/core.py.
package core

import (
	"fmt"
	"sort"
	"time"

	"github.com/denizsincar29/schedule/go/internal/dates"
	"github.com/denizsincar29/schedule/go/internal/model"
	"github.com/denizsincar29/schedule/go/internal/resolver"
	"github.com/denizsincar29/schedule/go/internal/ruz"
)

// ResolveTarget returns (oid, group-name-as-printed) from --oid or --group
// (auto-found via FindOID).
func ResolveTarget(group, oid string) (string, string, error) {
	if oid != "" {
		return oid, group, nil
	}
	foundOID, name, err := ruz.FindOID(group)
	if err != nil {
		return "", "", err
	}
	return foundOID, name, nil
}

func parseISO(s string) (time.Time, error) {
	t, err := time.Parse("2006-01-02", s)
	if err != nil {
		return time.Time{}, fmt.Errorf("не дата YYYY-MM-DD: %s", s)
	}
	return t, nil
}

// Window returns (week_start, days in the requested window). day wins over
// start/offset, mirroring py core.window.
func Window(days []model.Day, today time.Time, day, start string, offset int) (time.Time, []model.Day, error) {
	if day != "" {
		d, err := parseISO(day)
		if err != nil {
			return time.Time{}, nil, err
		}
		picked := []model.Day{} // empty window serializes as [] not null
		for _, x := range days {
			if x.Date == day {
				picked = append(picked, x)
			}
		}
		return dates.MondayOf(d), picked, nil
	}
	begin, err := startBegin(today, start)
	if err != nil {
		return time.Time{}, nil, err
	}
	begin = dates.MondayOf(begin).AddDate(0, 0, offset*7)
	end := begin.AddDate(0, 0, 7)
	picked := []model.Day{} // empty window serializes as [] not null
	for _, x := range days {
		d, err := parseISO(x.Date)
		if err != nil {
			continue
		}
		if !d.Before(begin) && d.Before(end) {
			picked = append(picked, x)
		}
	}
	sort.Slice(picked, func(i, j int) bool { return picked[i].Date < picked[j].Date })
	return begin, picked, nil
}

func startBegin(today time.Time, start string) (time.Time, error) {
	if start != "" {
		return parseISO(start)
	}
	return dates.NextMonday(today), nil
}

// MakeWeek is the fetch-free builder: given parsed days, return the requested
// window. With fullNames the short→full pass runs against the cached/fetched
// staff index (may hit the network once per 30 days).
func MakeWeek(group, oid string, days []model.Day, today time.Time,
	day, start string, offset int, fullNames bool) (model.Week, error) {
	if fullNames {
		resolver.ApplyFullNames(days, resolver.LoadIndex())
	}
	begin, picked, err := Window(days, today, day, start, offset)
	if err != nil {
		return model.Week{}, err
	}
	return model.Week{
		Group:     group,
		OID:       oid,
		WeekStart: begin.Format("2006-01-02"),
		Days:      picked,
	}, nil
}
