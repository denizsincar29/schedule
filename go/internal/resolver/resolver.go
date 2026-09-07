// Package resolver resolves timetable short names («Абрамова Л.В.») to full
// names from the official САФУ staff list (narfu.ru/sveden/employees).
//
// The rules mirror the Python reference (py/schedule/resolver.py): every
// teacher is marked with microdata itemprop="fio", each full name is folded to
// the short form the timetable uses, and only unambiguous matches survive —
// two teachers sharing the same initials stay unresolved rather than guessed.
//
// The parsed index is cached in the platform user cache dir under
// narfu_schedule/employees_index.json for 30 days — the same file Python and
// Rust use. Failures never propagate: on any network/parse error we return
// what we have ({} or the stale cache) so the caller keeps the short names.
package resolver

import (
	"encoding/json"
	"os"
	"path/filepath"
	"regexp"
	"strings"
	"time"

	"github.com/denizsincar29/schedule/go/internal/model"
	"github.com/denizsincar29/schedule/go/internal/ruz"
)

const (
	employeesURL = "https://narfu.ru/sveden/employees/"
	dirName      = "narfu_schedule"
	fileName     = "employees_index.json"
	ttl          = 30 * 24 * time.Hour
)

var reFio = regexp.MustCompile(`(?s)itemprop="fio">(.*?)</td>`)

// CachePath returns narfu_schedule/employees_index.json under the platform
// user cache dir (XDG on unix, ~/Library/Caches on darwin, LocalAppData on
// windows) — mirrors Python's cache_path().
func CachePath() (string, error) {
	base, err := os.UserCacheDir()
	if err != nil {
		return "", err
	}
	return filepath.Join(base, dirName, fileName), nil
}

// ShortOf folds a full name («Абрамова Любовь Валерьевна») to the timetable
// short form («Абрамова Л.В.»).
func ShortOf(full string) string {
	parts := strings.Fields(full)
	if len(parts) < 2 {
		return full
	}
	var b strings.Builder
	b.WriteString(parts[0])
	b.WriteByte(' ')
	for _, p := range parts[1:] {
		r := []rune(p)
		if len(r) > 0 {
			b.WriteRune(r[0])
			b.WriteByte('.')
		}
	}
	return b.String()
}

// BuildIndex parses the staff page HTML into a {short: full} map keeping only
// unambiguous matches.
func BuildIndex(h string) map[string]string {
	seen := map[string][]string{}
	for _, m := range reFio.FindAllStringSubmatch(h, -1) {
		full := ruz.Un(m[1])
		if len(strings.Fields(full)) < 2 {
			continue
		}
		s := ShortOf(full)
		seen[s] = append(seen[s], full)
	}
	out := map[string]string{}
	for s, fs := range seen {
		if len(fs) == 1 {
			out[s] = fs[0]
		}
	}
	return out
}

// LoadIndex returns the short→full map, fetching/refreshing the cache when
// needed. Network/parse failures degrade to the stale cache or {}.
func LoadIndex() map[string]string {
	path, perr := CachePath()
	idx := map[string]string(nil)
	if perr == nil {
		if b, err := os.ReadFile(path); err == nil {
			var m map[string]string
			if json.Unmarshal(b, &m) == nil {
				if st, err := os.Stat(path); err == nil && time.Since(st.ModTime()) < ttl {
					return m
				}
				idx = m // stale fallback
			}
		}
	}
	h, err := ruz.Get(employeesURL)
	if err != nil {
		if idx != nil {
			return idx
		}
		return map[string]string{}
	}
	out := BuildIndex(h)
	if perr == nil {
		writeCache(path, out)
	}
	return out
}

func writeCache(path string, idx map[string]string) {
	b, err := json.MarshalIndent(idx, "", " ")
	if err != nil {
		return
	}
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return
	}
	_ = os.WriteFile(path, b, 0o644)
}

// ApplyFullNames annotates each lesson's TeacherFull in place when it resolves.
func ApplyFullNames(days []model.Day, index map[string]string) {
	if len(index) == 0 {
		return
	}
	for di := range days {
		for li := range days[di].Lessons {
			full, ok := index[days[di].Lessons[li].Teacher]
			if ok && full != "" {
				v := full
				days[di].Lessons[li].TeacherFull = &v
			}
		}
	}
}
