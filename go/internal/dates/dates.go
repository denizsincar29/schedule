// Package dates provides the week/date helpers the CLI and core share.
// The timetable works in whole weeks Mon–Sat; days are ISO strings.
package dates

import (
	"fmt"
	"time"
)

var weekdayRU = []string{
	"понедельник", "вторник", "среда", "четверг", "пятница", "суббота",
	"воскресенье",
}

var monthsRU = []string{
	"января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа",
	"сентября", "октября", "ноября", "декабря",
}

// WeekdayRU returns the lowercase Russian weekday name.
// time.Weekday is Sunday-based; the RU list is Monday-based, so shift by
// (wd+6)%7 — same arithmetic as MondayOf.
func WeekdayRU(d time.Time) string {
	return weekdayRU[(int(d.Weekday())+6)%7]
}

// MondayOf returns the Monday of d's week (dates are handled at UTC midnight).
func MondayOf(d time.Time) time.Time {
	y, m, day := d.Date()
	t := time.Date(y, m, day, 0, 0, 0, 0, time.UTC)
	wd := (int(t.Weekday()) + 6) % 7 // 0 = Monday
	return t.AddDate(0, 0, -wd)
}

// NextMonday returns d itself when d is a Monday, else the next Monday.
func NextMonday(d time.Time) time.Time {
	if d.Weekday() == time.Monday {
		return MondayOf(d)
	}
	return MondayOf(d).AddDate(0, 0, 7)
}

// RuDate renders «7 сентября» for the human text output.
func RuDate(d time.Time) string {
	return fmt.Sprintf("%d %s", d.Day(), monthsRU[int(d.Month())-1])
}
