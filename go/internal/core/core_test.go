// Core window-selection tests on frozen fixtures (no network).
package core

import (
	"os"
	"strings"
	"testing"
	"time"

	"github.com/denizsincar29/schedule/go/internal/model"
	"github.com/denizsincar29/schedule/go/internal/ruz"
)

const fixDir = "../../../spec/fixtures"

func fixtureDays(t *testing.T, name string) []model.Day {
	t.Helper()
	b, err := os.ReadFile(fixDir + "/" + name)
	if err != nil {
		t.Fatalf("read %s: %v", name, err)
	}
	return ruz.ParsePage(string(b))
}

func iso(s string) time.Time {
	t, _ := time.Parse("2006-01-02", s)
	return t
}

// The one-day fixture is 2026-09-07 (Monday). A single-day query for it must
// return that day and week_start = its Monday (the day itself).
func TestSingleDay(t *testing.T) {
	days := fixtureDays(t, "ruz_one_day.html")
	begin, picked, err := Window(days, iso("2026-09-07"), "2026-09-07", "", 0)
	if err != nil {
		t.Fatal(err)
	}
	if begin.Format("2006-01-02") != "2026-09-07" {
		t.Errorf("week_start = %s", begin)
	}
	if len(picked) != 1 || picked[0].Date != "2026-09-07" {
		t.Fatalf("picked = %+v", picked)
	}
}

// A single-day query for a date with no column returns an empty (not nil)
// days list — JSON must serialize [] not null.
func TestSingleDayNoColumn(t *testing.T) {
	days := fixtureDays(t, "ruz_one_day.html")
	_, picked, err := Window(days, iso("2026-09-06"), "2026-09-06", "", 0)
	if err != nil {
		t.Fatal(err)
	}
	if picked == nil || len(picked) != 0 {
		t.Fatalf("picked = %#v, want empty non-nil", picked)
	}
}

// Week window for the snapshot: 2026-09-07..12 must hold exactly the Mon-Sat
// days of that week (6 published columns, empty days as empty lessons).
func TestWeekWindow(t *testing.T) {
	days := fixtureDays(t, "ruz_20756_week.html")
	begin, picked, err := Window(days, iso("2026-09-10"), "", "2026-09-10", 0)
	if err != nil {
		t.Fatal(err)
	}
	if begin.Format("2006-01-02") != "2026-09-07" {
		t.Errorf("week_start = %s, want 2026-09-07", begin)
	}
	if len(picked) != 6 {
		t.Fatalf("picked = %d days, want 6", len(picked))
	}
	want := []string{
		"2026-09-07", "2026-09-08", "2026-09-09",
		"2026-09-10", "2026-09-11", "2026-09-12",
	}
	for i, wd := range want {
		if picked[i].Date != wd {
			t.Errorf("picked[%d].date = %s, want %s", i, picked[i].Date, wd)
		}
	}
	// Sanity: one of the empty columns stays lessons:[] — pick a date that the
	// site published without classes if present anywhere in the snapshot.
	anyEmpty := false
	for _, d := range days {
		if len(d.Lessons) == 0 {
			anyEmpty = true
			break
		}
	}
	if !anyEmpty {
		t.Error("snapshot has no empty day column, fixture assumption broken")
	}
}

// MakeWeek wire-up: full_names=false must not touch teacher_full.
func TestMakeWeekNoFullNames(t *testing.T) {
	days := fixtureDays(t, "ruz_one_day.html")
	w, err := MakeWeek("151318", "20756", days, iso("2026-09-07"),
		"2026-09-07", "", 0, false)
	if err != nil {
		t.Fatal(err)
	}
	if w.Group != "151318" || w.OID != "20756" {
		t.Errorf("week ids = %q %q", w.Group, w.OID)
	}
	if len(w.Days) != 1 || w.Days[0].Lessons[0].TeacherFull != nil {
		t.Errorf("unexpected full names applied")
	}
}

// Serialization must match Python json.dumps(asdict(w), ensure_ascii=False,
// indent=2): the empty window emits "days": [] and teacher_full stays null.
func TestJSONShape(t *testing.T) {
	days := fixtureDays(t, "ruz_one_day.html")
	w, err := MakeWeek("151318", "20756", days, iso("2026-09-07"),
		"2026-09-07", "", 0, false)
	if err != nil {
		t.Fatal(err)
	}
	b, err := w.ToJSON()
	if err != nil {
		t.Fatal(err)
	}
	s := string(b)
	for _, sub := range []string{
		`"group": "151318"`,
		`"oid": "20756"`,
		`"week_start": "2026-09-07"`,
		`"teacher_full": null`,
		`"time_start": "08:20"`,
		`"time_end": "09:55"`,
	} {
		if !strings.Contains(s, sub) {
			t.Errorf("JSON missing %s", sub)
		}
	}
	if !strings.Contains(s, "\n  \"days\": [") {
		t.Errorf("days not indented:\n%s", s)
	}

	// Empty window serializes days: [] — a nil Go slice would emit null.
	wEmpty, _ := MakeWeek("", "20756", []model.Day{}, iso("2026-09-07"),
		"", "2026-09-07", 0, false)
	be, err := wEmpty.ToJSON()
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(string(be), `"days": []`) {
		t.Errorf("empty days not serialized as []:\n%s", be)
	}
}
