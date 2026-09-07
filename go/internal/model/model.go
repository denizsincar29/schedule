// Package model holds the shared data model (spec/schema.json).
//
// Field order matters: it is the key order of every implementation's --json
// output. Lesson is serialized with teacher_full as a *string so an
// unresolved name renders as JSON null, exactly like the Python/Rust versions.
package model

import (
	"bytes"
	"encoding/json"
	"fmt"
)

// Lesson is one class of the timetable.
type Lesson struct {
	Num         string  `json:"num"`
	TimeStart   string  `json:"time_start"`
	TimeEnd     string  `json:"time_end"`
	Kind        string  `json:"kind"`
	Subject     string  `json:"subject"`
	Teacher     string  `json:"teacher"`
	TeacherFull *string `json:"teacher_full"`
	Room        string  `json:"room"`
	Addr        string  `json:"addr"`
}

// Day is one published day column.
type Day struct {
	Date    string   `json:"date"`
	Weekday string   `json:"weekday"`
	Lessons []Lesson `json:"lessons"`
}

// Week is the top-level --json object.
type Week struct {
	Group     string `json:"group"`
	OID       string `json:"oid"`
	WeekStart string `json:"week_start"`
	Days      []Day  `json:"days"`
}

// ToJSON renders the Week per schema.json (2-space indent, UTF-8, schema field
// order, no HTML escaping — json.dumps(ensure_ascii=False) in Python escapes
// nothing either). A trailing newline is added by the caller's fmt.Println.
func (w *Week) ToJSON() ([]byte, error) {
	var buf bytes.Buffer
	enc := json.NewEncoder(&buf)
	enc.SetEscapeHTML(false)
	enc.SetIndent("", "  ")
	if err := enc.Encode(w); err != nil {
		return nil, err
	}
	return bytes.TrimRight(buf.Bytes(), "\n"), nil
}

func (w *Week) String() string {
	b, err := w.ToJSON()
	if err != nil {
		return fmt.Sprintf("error: %v", err)
	}
	return string(b)
}
