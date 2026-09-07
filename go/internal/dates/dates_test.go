// Week-boundary and weekday tests for the date helpers — mirrors
// py/tests/test_dates.py.
package dates

import (
	"testing"
	"time"
)

func iso(s string) time.Time {
	t, _ := time.Parse("2006-01-02", s)
	return t
}

func TestMondayOf(t *testing.T) {
	cases := map[string]string{
		"2026-09-07": "2026-09-07", // Mon
		"2026-09-10": "2026-09-07", // Thu
		"2026-09-13": "2026-09-07", // Sun
	}
	for in, want := range cases {
		if got := MondayOf(iso(in)).Format("2006-01-02"); got != want {
			t.Errorf("MondayOf(%s) = %s", in, got)
		}
	}
}

func TestNextMonday(t *testing.T) {
	cases := map[string]string{
		"2026-09-07": "2026-09-07", // Mon -> same
		"2026-09-10": "2026-09-14", // Thu
		"2026-09-13": "2026-09-14", // Sun
	}
	for in, want := range cases {
		if got := NextMonday(iso(in)).Format("2006-01-02"); got != want {
			t.Errorf("NextMonday(%s) = %s", in, got)
		}
	}
}

func TestWeekdayRU(t *testing.T) {
	if got := WeekdayRU(iso("2026-09-07")); got != "понедельник" {
		t.Errorf("got %q", got)
	}
	if got := WeekdayRU(iso("2026-09-12")); got != "суббота" {
		t.Errorf("got %q", got)
	}
	if got := WeekdayRU(iso("2026-09-13")); got != "воскресенье" {
		t.Errorf("got %q", got)
	}
}

func TestRuDate(t *testing.T) {
	if got := RuDate(iso("2026-09-07")); got != "7 сентября" {
		t.Errorf("got %q", got)
	}
}
