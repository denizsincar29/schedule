// Command schedule reads a САФУ group timetable from ruz.narfu.ru (no login).
//
// Go mirror of py/schedule/cli.py — the shared CLI contract in spec/cli.md.
// Plain screen-reader-friendly Russian by default; schema.json with --json.
// Exit 0 even for an empty window; non-zero on network/group failure.
package main

import (
	"errors"
	"flag"
	"fmt"
	"io"
	"os"
	"strings"
	"time"

	"github.com/denizsincar29/schedule/go/internal/core"
	"github.com/denizsincar29/schedule/go/internal/dates"
	"github.com/denizsincar29/schedule/go/internal/model"
	"github.com/denizsincar29/schedule/go/internal/ruz"
)

const prog = "schedule"

type opts struct {
	group, oid      string
	today, tomorrow bool
	start           string
	offset          int
	fullNames, json bool
}

func newFlagSet(stderr io.Writer) *flag.FlagSet {
	fs := flag.NewFlagSet(prog, flag.ContinueOnError)
	fs.SetOutput(stderr)
	fs.Usage = func() {
		fmt.Fprintf(stderr, `Использование: %s (--group ИМЯ | --oid ЧИСЛО) [--today | --tomorrow | --week] [--start ГГГГ-ММ-ДД] [--offset N] [--full-names] [--json]

Читает расписание группы САФУ с ruz.narfu.ru (без логина).
Текст по умолчанию, --json по schema.json.
`, prog)
		fs.PrintDefaults()
	}
	return fs
}

func parseArgs(args []string, stderr io.Writer) (opts, error) {
	var o opts
	fs := newFlagSet(stderr)
	fs.StringVar(&o.group, "group", "", "имя группы как на сайте, напр. 151318")
	fs.StringVar(&o.oid, "oid", "", "oid расписания (без поиска группы)")
	fs.BoolVar(&o.today, "today", false, "только на сегодня")
	fs.BoolVar(&o.tomorrow, "tomorrow", false, "только на завтра")
	fs.StringVar(&o.start, "start", "", "неделя, содержащая эту дату (с --week)")
	fs.IntVar(&o.offset, "offset", 0, "сдвиг недели на N недель (с --week)")
	fs.BoolVar(&o.fullNames, "full-names", false, "полные ФИО преподавателей из официального списка")
	fs.BoolVar(&o.json, "json", false, "вывод в формате schema.json")
	_ = fs.Bool("week", false, "вся неделя Пн–Сб (по умолчанию)")
	if err := fs.Parse(args); err != nil {
		return o, err
	}
	if fs.NArg() > 0 {
		return o, errors.New("лишние позиционные аргументы: " + strings.Join(fs.Args(), " "))
	}
	if (o.group == "") == (o.oid == "") {
		return o, errors.New("нужен ровно один из --group или --oid")
	}
	if o.today && o.tomorrow {
		return o, errors.New("--today и --tomorrow взаимоисключают друг друга")
	}
	return o, nil
}

// today returns the current local calendar date at UTC midnight.
func today() time.Time {
	now := time.Now()
	return time.Date(now.Year(), now.Month(), now.Day(), 0, 0, 0, 0, time.UTC)
}

// collapsePunct mimics py _line's re.sub(r"([.!?])\1+", r"\1") — RE2 has no
// backreferences, so fold a run of the same . ! ? into one by hand.
func collapsePunct(s string) string {
	var b strings.Builder
	var prev rune
	for i, r := range s {
		if i > 0 && (r == '.' || r == '!' || r == '?') && r == prev {
			continue
		}
		b.WriteRune(r)
		prev = r
	}
	return b.String()
}

func loc(L model.Lesson) string {
	addr := strings.TrimLeft(L.Addr, " ,")
	loc := strings.TrimRight(L.Room, " \t")
	if addr != "" {
		if loc != "" {
			return loc + ", " + addr
		}
		return addr
	}
	return loc
}

func lessonLine(L model.Lesson) string {
	t := L.Teacher
	if L.TeacherFull != nil {
		t = *L.TeacherFull
	}
	var b strings.Builder
	fmt.Fprintf(&b, "%s–%s — %s. %s", L.TimeStart, L.TimeEnd, L.Kind, L.Subject)
	if t != "" {
		b.WriteString(", " + t)
	}
	fmt.Fprintf(&b, ". %s", loc(L))
	return collapsePunct(b.String())
}

func printDay(target time.Time, w model.Week) {
	day := model.Day{}
	have := len(w.Days) > 0
	if have {
		day = w.Days[0]
	}
	if !have || len(day.Lessons) == 0 {
		fmt.Printf("%s, %s: пар нет\n", dates.WeekdayRU(target), dates.RuDate(target))
		return
	}
	fmt.Printf("%s, %s:\n", day.Weekday, dates.RuDate(target))
	for _, L := range day.Lessons {
		fmt.Println("  " + lessonLine(L))
	}
}

func printWeek(w model.Week) {
	start := parseWeekStart(w.WeekStart)
	end := start.AddDate(0, 0, 5)
	fmt.Printf("Неделя с %s по %s:\n", dates.RuDate(start), dates.RuDate(end))
	var has []model.Day
	for _, d := range w.Days {
		if len(d.Lessons) > 0 {
			has = append(has, d)
		}
	}
	if len(has) == 0 {
		fmt.Println("  на эту неделю занятий не выложено")
		return
	}
	for _, d := range has {
		dt, err := time.Parse("2006-01-02", d.Date)
		if err != nil {
			continue
		}
		fmt.Printf("\n%s, %s:\n", d.Weekday, dates.RuDate(dt))
		for _, L := range d.Lessons {
			fmt.Println("  " + lessonLine(L))
		}
	}
}

func parseWeekStart(s string) time.Time {
	t, err := time.Parse("2006-01-02", s)
	if err != nil {
		return today()
	}
	return t
}

func run(o opts, stdout, stderr io.Writer) int {
	oid, name, err := core.ResolveTarget(o.group, o.oid)
	if err != nil {
		fmt.Fprintf(stderr, "ошибка: %v\n", err)
		return 2
	}
	h, err := ruz.FetchGroup(oid)
	if err != nil {
		fmt.Fprintf(stderr, "ошибка: %v\n", err)
		return 2
	}
	days := ruz.ParsePage(h)
	t := today()
	single := o.today || o.tomorrow
	day := ""
	if single {
		day = t.Format("2006-01-02")
		if o.tomorrow {
			day = t.AddDate(0, 0, 1).Format("2006-01-02")
		}
	}
	w, err := core.MakeWeek(name, oid, days, t, day, o.start, o.offset,
		o.fullNames)
	if err != nil {
		fmt.Fprintf(stderr, "ошибка: %v\n", err)
		return 2
	}
	if o.json {
		b, jerr := w.ToJSON()
		if jerr != nil {
			fmt.Fprintf(stderr, "ошибка: %v\n", jerr)
			return 2
		}
		fmt.Fprintln(stdout, string(b))
		return 0
	}
	if single {
		target, _ := time.Parse("2006-01-02", day)
		printDay(target, w)
	} else {
		printWeek(w)
	}
	return 0
}

func main() {
	o, err := parseArgs(os.Args[1:], os.Stderr)
	if err != nil {
		if errors.Is(err, flag.ErrHelp) {
			os.Exit(0)
		}
		fmt.Fprintf(os.Stderr, "ошибка: %v\n", err)
		fmt.Fprintf(os.Stderr, "попробуйте '%s --help'\n", prog)
		os.Exit(2)
	}
	os.Exit(run(o, os.Stdout, os.Stderr))
}
