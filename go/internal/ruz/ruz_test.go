// Parser tests against the frozen spec/fixtures snapshots (no network).
// Fixture paths are relative to this package dir (go/internal/ruz -> repo root).
package ruz

import (
	"os"
	"regexp"
	"testing"
)

const fixDir = "../../../spec/fixtures"

func readFixture(t *testing.T, name string) string {
	t.Helper()
	b, err := os.ReadFile(fixDir + "/" + name)
	if err != nil {
		t.Fatalf("read %s: %v", name, err)
	}
	return string(b)
}

var timeRE = regexp.MustCompile(`^([01]\d|2[0-3]):[0-5]\d$`)

func TestOneDay(t *testing.T) {
	days := ParsePage(readFixture(t, "ruz_one_day.html"))
	if len(days) != 1 {
		t.Fatalf("want 1 day, got %d", len(days))
	}
	day := days[0]
	if day.Date != "2026-09-07" {
		t.Errorf("date = %q", day.Date)
	}
	if day.Weekday != "понедельник" {
		t.Errorf("weekday = %q", day.Weekday)
	}
}

func TestTwoLessonsSorted(t *testing.T) {
	days := ParsePage(readFixture(t, "ruz_one_day.html"))
	got := []string{}
	for _, l := range days[0].Lessons {
		got = append(got, l.Num)
	}
	want := []string{"1", "2"}
	if len(got) != len(want) {
		t.Fatalf("lessons nums = %v", got)
	}
	for i := range want {
		if got[i] != want[i] {
			t.Errorf("lesson %d num = %q, want %q", i, got[i], want[i])
		}
	}
}

func TestLessonFields(t *testing.T) {
	days := ParsePage(readFixture(t, "ruz_one_day.html"))
	l := days[0].Lessons[0]
	if l.TimeStart != "08:20" || l.TimeEnd != "09:55" {
		t.Errorf("time = %q..%q", l.TimeStart, l.TimeEnd)
	}
	if l.Kind != "Лекция" {
		t.Errorf("kind = %q", l.Kind)
	}
	if l.Teacher != "Абрамова Л.В." {
		t.Errorf("teacher = %q", l.Teacher)
	}
	if l.TeacherFull != nil {
		t.Errorf("teacher_full = %v, want nil", *l.TeacherFull)
	}
	if l.Room != "ауд. 44" {
		t.Errorf("room = %q", l.Room)
	}
	if l.Addr != "наб. Северной Двины, д. 2" {
		t.Errorf("addr = %q", l.Addr)
	}
	if !contains(l.Subject, "машинного и глубокого обучения") {
		t.Errorf("subject = %q", l.Subject)
	}
}

func TestTimesAreClean(t *testing.T) {
	days := ParsePage(readFixture(t, "ruz_one_day.html"))
	for _, l := range days[0].Lessons {
		if !timeRE.MatchString(l.TimeStart) || !timeRE.MatchString(l.TimeEnd) {
			t.Errorf("dirty time %q..%q", l.TimeStart, l.TimeEnd)
		}
	}
}

func TestEmptyDayColumn(t *testing.T) {
	days := ParsePage(readFixture(t, "ruz_empty_day.html"))
	if len(days) != 1 {
		t.Fatalf("want 1 day, got %d", len(days))
	}
	if days[0].Date != "2026-09-08" {
		t.Errorf("date = %q", days[0].Date)
	}
	if len(days[0].Lessons) != 0 {
		t.Errorf("lessons = %v, want empty", days[0].Lessons)
	}
}

func TestWeekSnapshot(t *testing.T) {
	days := ParsePage(readFixture(t, "ruz_20756_week.html"))
	if len(days) != 36 {
		t.Fatalf("snapshot size = %d, want 36", len(days))
	}
	prev := ""
	for _, d := range days {
		if d.Date < prev {
			t.Errorf("dates not sorted at %q after %q", d.Date, prev)
		}
		prev = d.Date
	}
}

func TestNoEmptyTimes(t *testing.T) {
	days := ParsePage(readFixture(t, "ruz_20756_week.html"))
	for _, d := range days {
		for _, l := range d.Lessons {
			if l.TimeStart == "" || l.TimeEnd == "" || l.Kind == "" || l.Subject == "" {
				t.Errorf("empty field in %s lesson %q", d.Date, l.Num)
			}
		}
	}
}

func contains(s, sub string) bool {
	return regexp.MustCompile(regexp.QuoteMeta(sub)).MatchString(s)
}
