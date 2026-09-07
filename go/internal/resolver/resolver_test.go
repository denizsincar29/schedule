// Resolver tests against the employees fixture (no network).
// The fixture deliberately holds two Абрамовых with different initials so we
// can assert the ambiguity rule — mirrors py/tests/test_resolver.py.
package resolver

import (
	"os"
	"testing"

	"github.com/denizsincar29/schedule/go/internal/ruz"
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

func TestShortOf(t *testing.T) {
	if got := ShortOf("Абрамова Любовь Валерьевна"); got != "Абрамова Л.В." {
		t.Errorf("short = %q", got)
	}
	if got := ShortOf("Деменков Максим Евгеньевич"); got != "Деменков М.Е." {
		t.Errorf("short = %q", got)
	}
}

func TestBuildIndex(t *testing.T) {
	idx := BuildIndex(readFixture(t, "employees_frag.html"))
	cases := map[string]string{
		"Абрамова Л.В.":  "Абрамова Любовь Валерьевна",
		"Абрамова М.А.":  "Абрамова Марина Алексеевна",
		"Деменков М.Е.":  "Деменков Максим Евгеньевич",
		"Деменкова Е.А.": "Деменкова Екатерина Алексеевна",
		"Шурыкина Л.С.":  "Шурыкина Людмила Сергеевна",
	}
	for short, full := range cases {
		if got, ok := idx[short]; !ok || got != full {
			t.Errorf("idx[%q] = %q, want %q", short, got, full)
		}
	}
}

func TestApplyFullNames(t *testing.T) {
	days := ruz.ParsePage(readFixture(t, "ruz_one_day.html"))
	idx := map[string]string{"Абрамова Л.В.": "Абрамова Любовь Валерьевна"}
	ApplyFullNames(days, idx)
	if days[0].Lessons[0].TeacherFull == nil ||
		*days[0].Lessons[0].TeacherFull != "Абрамова Любовь Валерьевна" {
		t.Errorf("teacher_full = %v", days[0].Lessons[0].TeacherFull)
	}
}

func TestUnresolvedStaysNil(t *testing.T) {
	days := ruz.ParsePage(readFixture(t, "ruz_one_day.html"))
	ApplyFullNames(days, map[string]string{"Кто-то И.К.": "Кто-то Имя Кто-тович"})
	if days[0].Lessons[0].TeacherFull != nil {
		t.Errorf("teacher_full = %v, want nil", *days[0].Lessons[0].TeacherFull)
	}
}
