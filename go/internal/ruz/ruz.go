// Package ruz fetches and parses the САФУ RUZ timetable HTML (ruz.narfu.ru).
//
// No API exists — we read the pages a browser would. The rules mirror the
// Python reference: day columns are <div class="dayofweek">, each lesson a
// nested <div class="timetable_sheet ..."> (the non-_xs variant), the teacher
// is in a <nobr> inside the discipline span, room+address in the auditorium
// span. Whitespace collapsing uses strings.Fields so NBSP collapses like the
// Python \s+ (keeps JSON output byte-identical).
package ruz

import (
	"html"
	"io"
	"net/http"
	"regexp"
	"strconv"
	"strings"
	"time"

	"github.com/denizsincar29/schedule/go/internal/dates"
	"github.com/denizsincar29/schedule/go/internal/model"
)

const (
	base = "https://ruz.narfu.ru/"
	ua   = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"
)

var client = &http.Client{Timeout: 30 * time.Second}

// Un collapses every run of whitespace (incl. NBSP) to one ASCII space.
func Un(s string) string {
	return strings.Join(strings.Fields(html.UnescapeString(s)), " ")
}

func httpGet(url string) (string, error) {
	req, err := http.NewRequest("GET", url, nil)
	if err != nil {
		return "", err
	}
	req.Header.Set("User-Agent", ua)
	req.Header.Set("Referer", base)
	resp, err := client.Do(req)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()
	b, err := io.ReadAll(resp.Body)
	return string(b), err
}

var (
	reInst  = regexp.MustCompile(`<a href="\?groups&institution=(\d+)"`)
	reGroup = regexp.MustCompile(`(?s)<a[^>]*href="\?timetable&group=(\d+)"[^>]*>(.*?)</a>`)
	reTag   = regexp.MustCompile(`<[^>]+>`)
	reDay   = regexp.MustCompile(`(?s)<div class="dayofweek[^"]*">(.*?)</div>`)
	reSheet = regexp.MustCompile(`<div class="timetable_sheet([^"]*)">`)
	reDiv   = regexp.MustCompile(`<div\b|</div>`)
	reSpan  = func(class string) *regexp.Regexp {
		return regexp.MustCompile(`(?s)<span class="` + class + `">(.*?)</span>`)
	}
	reNobr  = regexp.MustCompile(`(?s)<nobr>(.*?)</nobr>`)
	reSuflx = regexp.MustCompile(`(?s)\s*\(<nobr>.*?</nobr>\)\s*$`)
	reAudB  = regexp.MustCompile(`(?s)<b>(.*?)</b>(.*)$`)
	reDash  = regexp.MustCompile(`\s*[-–—]\s*`)
	reComm  = regexp.MustCompile(`(?s)<!--.*?-->`)
)

var spanNum = reSpan("num_para")
var spanTime = reSpan("time_para")
var spanKind = reSpan("kindOfWork")
var spanDisc = reSpan("discipline")
var spanAud = reSpan("auditorium")

// FindOID scans the institute group pages for the human group name and returns
// the timetable oid plus the name as printed.
func FindOID(group string) (oid, name string, err error) {
	home, err := httpGet(base)
	if err != nil {
		return "", "", err
	}
	seen := map[string]bool{}
	var insts []string
	for _, m := range reInst.FindAllStringSubmatch(home, -1) {
		if !seen[m[1]] {
			seen[m[1]] = true
			insts = append(insts, m[1])
		}
	}
	if len(insts) == 0 {
		insts = []string{"1", "3", "4", "6", "12", "13", "15", "23", "26",
			"28", "33", "35", "36"}
	}
	want := regexp.MustCompile(`(?i)(^|\s)` + regexp.QuoteMeta(strings.TrimSpace(group)) + `($|\s)`)
	for _, i := range insts {
		page, err := httpGet(base + "?groups&institution=" + i)
		if err != nil {
			continue
		}
		for _, m := range reGroup.FindAllStringSubmatch(page, -1) {
			text := Un(reTag.ReplaceAllString(m[2], " "))
			if want.MatchString(text) {
				fields := strings.Fields(text)
				if len(fields) == 0 {
					continue
				}
				return m[1], fields[0], nil
			}
		}
	}
	return "", "", errGroupNotFound{group}
}

type errGroupNotFound struct{ group string }

func (e errGroupNotFound) Error() string {
	return "группа «" + e.group + "» не найдена ни в одном институте"
}

// Get fetches an arbitrary URL with the same UA/timeout (used for the
// employees page too).
func Get(url string) (string, error) {
	return httpGet(url)
}

// FetchGroup downloads the group's timetable page.
func FetchGroup(oid string) (string, error) {
	return httpGet(base + "?timetable&group=" + oid)
}

func splitTime(t string) (start, end string) {
	parts := reDash.Split(t, -1)
	if len(parts) != 2 {
		return t, ""
	}
	return strings.TrimSpace(parts[0]), strings.TrimSpace(parts[1])
}

// ParsePage returns the published day columns in page (chronological) order.
// A column that exists but has no classes yields a Day with empty Lessons.
func ParsePage(h string) []model.Day {
	h = reComm.ReplaceAllString(h, "")
	ms := reDay.FindAllStringSubmatchIndex(h, -1)
	var days []model.Day
	for k, idx := range ms {
		// idx: [fullStart fullEnd groupStart groupEnd]
		head := Un(h[idx[2]:idx[3]])
		parts := strings.Split(head, ",")
		if len(parts) != 2 {
			continue
		}
		dt := strings.TrimSpace(parts[1]) // weekday text is ignored; stored form
		d, err := parseDotDate(dt)        // is derived from the date itself
		if err != nil {
			continue
		}
		segStart := idx[1]
		segEnd := len(h)
		if k+1 < len(ms) {
			segEnd = ms[k+1][0]
		}
		seg := h[segStart:segEnd]
		lessons := []model.Lesson{} // empty day serializes as [] not null
		for _, lm := range reSheet.FindAllStringSubmatchIndex(seg, -1) {
			if strings.HasPrefix(seg[lm[2]:lm[3]], "_xs") {
				continue // the mobile timetable_sheet_xs column — skip
			}
			j, depth := lm[1], 1
			var closed int
			for depth > 0 && j < len(seg) {
				loc := reDiv.FindStringIndex(seg[j:])
				if loc == nil {
					break
				}
				at := j + loc[0]
				opening := seg[at:at+4] == "<div"
				if opening {
					depth++
				} else {
					depth--
				}
				j += loc[1]
				if depth == 0 {
					closed = j
					break
				}
			}
			chunk := ""
			if closed > 0 {
				chunk = seg[lm[1]:closed]
			}
			num := Un(span(chunk, spanNum))
			tm := Un(span(chunk, spanTime))
			kind := Un(span(chunk, spanKind))
			disc := span(chunk, spanDisc)
			subject := disc
			if nm := reNobr.FindStringSubmatch(disc); nm != nil {
				subject = reSuflx.ReplaceAllString(disc, "")
			}
			teacher := ""
			if nm := reNobr.FindStringSubmatch(disc); nm != nil {
				teacher = Un(nm[1])
			}
			subject = Un(subject)
			room, addr := "", ""
			if aud := span(chunk, spanAud); aud != "" {
				if bm := reAudB.FindStringSubmatch(aud); bm != nil {
					room = Un(bm[1])
					addr = strings.TrimLeft(Un(reTag.ReplaceAllString(bm[2], "")), " ,")
				}
			}
			if tm == "" {
				continue
			}
			start, end := splitTime(tm)
			lessons = append(lessons, model.Lesson{
				Num: num, TimeStart: start, TimeEnd: end, Kind: kind,
				Subject: subject, Teacher: teacher, Room: room, Addr: addr,
			})
		}
		sortLessons(lessons)
		days = append(days, model.Day{
			Date: d.Format("2006-01-02"), Weekday: dates.WeekdayRU(d),
			Lessons: lessons,
		})
	}
	return days
}

func span(chunk string, re *regexp.Regexp) string {
	if m := re.FindStringSubmatch(chunk); m != nil {
		return m[1]
	}
	return ""
}

func parseDotDate(s string) (time.Time, error) {
	p := strings.Split(s, ".")
	if len(p) != 3 {
		return time.Time{}, errBadDate
	}
	y, e1 := strconv.Atoi(p[2])
	m, e2 := strconv.Atoi(p[1])
	d, e3 := strconv.Atoi(p[0])
	if e1 != nil || e2 != nil || e3 != nil {
		return time.Time{}, errBadDate
	}
	// time.Date normalizes overflow (31.02 -> 03.03) where Python's date()
	// raises; reject any rollover so malformed columns are skipped like Python.
	if m < 1 || m > 12 || d < 1 || d > 31 {
		return time.Time{}, errBadDate
	}
	t := time.Date(y, time.Month(m), d, 0, 0, 0, 0, time.UTC)
	if t.Year() != y || int(t.Month()) != m || t.Day() != d {
		return time.Time{}, errBadDate
	}
	return t, nil
}

var errBadDate = errStr("не дата")

type errStr string

func (e errStr) Error() string { return string(e) }

func sortLessons(ls []model.Lesson) {
	// insertion sort by numeric num (tiny lists)
	for i := 1; i < len(ls); i++ {
		for j := i; j > 0 && lessonNum(ls[j-1]) > lessonNum(ls[j]); j-- {
			ls[j-1], ls[j] = ls[j], ls[j-1]
		}
	}
}

func lessonNum(l model.Lesson) int {
	n, err := strconv.Atoi(l.Num)
	if err != nil {
		return 99
	}
	return n
}
