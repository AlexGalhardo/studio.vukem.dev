package studio

import (
	"fmt"
	"strings"
)

// Aspect ratios the renderer supports, with the frame it computes from the
// configured width.
var Ratios = []string{"9:16", "1:1", "4:5", "16:9"}

// Limits shared by the schema, the compiler and the plan check.
const (
	MinDuration = 5
	MaxDuration = 300
	MaxFactLen  = 300
	MaxFacts    = 20
	MaxLinks    = 10
)

// Brief is what the operator fills in. Lists are newline-separated text.
type Brief struct {
	Goal     string `json:"goal"`
	Audience string `json:"audience"`
	Subject  string `json:"subject"`
	Duration int    `json:"duration"`
	Ratio    string `json:"ratio"`
	Skill    string `json:"skill"`
	Language string `json:"language"`
	Model    string `json:"model"`
	Facts    string `json:"facts"`
	Links    string `json:"links"`
	CTA      string `json:"cta"`
}

// Lines splits a newline-separated field, dropping blanks.
func Lines(s string) []string {
	var out []string

	for _, l := range strings.Split(strings.ReplaceAll(s, "\r\n", "\n"), "\n") {
		if l = strings.TrimSpace(l); l != "" {
			out = append(out, l)
		}
	}

	return out
}

// CheckLists validates the free-text lists, which the field schema cannot.
func (b Brief) CheckLists() map[string]string {
	errs := map[string]string{}

	facts := Lines(b.Facts)
	if len(facts) > MaxFacts {
		errs["facts"] = fmt.Sprintf("Use at most %d facts.", MaxFacts)
	}

	for _, f := range facts {
		if len([]rune(f)) > MaxFactLen {
			errs["facts"] = fmt.Sprintf("Each fact must be at most %d characters.", MaxFactLen)
		}
	}

	links := Lines(b.Links)
	if len(links) > MaxLinks {
		errs["links"] = fmt.Sprintf("Use at most %d links.", MaxLinks)
	}

	for _, l := range links {
		if !strings.HasPrefix(l, "https://") && !strings.HasPrefix(l, "http://") {
			errs["links"] = "Each link must start with http:// or https://."
		}
	}

	return errs
}

// Frame returns the pixel size of ratio at width, both even (H.264).
func Frame(ratio string, width int) (w, h int, err error) {
	var rw, rh int

	if _, err := fmt.Sscanf(ratio, "%d:%d", &rw, &rh); err != nil || rw <= 0 || rh <= 0 {
		return 0, 0, fmt.Errorf("studio: bad ratio %q", ratio)
	}

	w = width &^ 1
	h = (w * rh / rw) &^ 1

	return w, h, nil
}
