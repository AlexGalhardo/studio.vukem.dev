package studio

import (
	"fmt"
	"strconv"
	"strings"
)

// Cue is one caption. End is exclusive of the next cue and must fall before
// the video ends.
type Cue struct {
	Start float64
	End   float64
	Text  string
}

// CuesFromShots uses the plan cards as captions for a silent cut.
func CuesFromShots(shots []Shot) []Cue {
	out := make([]Cue, 0, len(shots))

	for _, shot := range shots {
		text := strings.TrimSpace(shot.Text)
		if text == "" {
			continue
		}

		out = append(out, Cue{Start: shot.Start, End: shot.End, Text: text})
	}

	return out
}

// CuesFromWords groups word times into lines of about six words.
func CuesFromWords(words []Word) []Cue {
	var out []Cue

	for i := 0; i < len(words); {
		j := i + 6
		if j > len(words) {
			j = len(words)
		}

		var text strings.Builder

		for k := i; k < j; k++ {
			if k > i {
				text.WriteByte(' ')
			}

			text.WriteString(words[k].Text)
		}

		out = append(out, Cue{Start: words[i].Start, End: words[j-1].End, Text: text.String()})
		i = j
	}

	return out
}

// WriteSRT formats cues as a SubRip file.
func WriteSRT(cues []Cue) string {
	var b strings.Builder

	for i, cue := range cues {
		if i > 0 {
			b.WriteByte('\n')
		}

		fmt.Fprintf(&b, "%d\n%s --> %s\n%s\n", i+1, srtTime(cue.Start), srtTime(cue.End), cue.Text)
	}

	return b.String()
}

func srtTime(sec float64) string {
	if sec < 0 {
		sec = 0
	}

	ms := int(sec*1000 + 0.5)
	h := ms / 3600000
	ms -= h * 3600000
	m := ms / 60000
	ms -= m * 60000
	s := ms / 1000
	ms -= s * 1000

	return fmt.Sprintf("%02d:%02d:%02d,%03d", h, m, s, ms)
}

// ParseSRT reads a SubRip file written by WriteSRT.
func ParseSRT(s string) ([]Cue, error) {
	blocks := strings.Split(strings.ReplaceAll(s, "\r\n", "\n"), "\n\n")
	var out []Cue

	for _, block := range blocks {
		block = strings.TrimSpace(block)
		if block == "" {
			continue
		}

		lines := strings.Split(block, "\n")
		if len(lines) < 3 {
			return nil, fmt.Errorf("studio: caption cue is incomplete")
		}

		times := strings.Split(lines[1], " --> ")
		if len(times) != 2 {
			return nil, fmt.Errorf("studio: caption cue has no time range")
		}

		start, err := parseSRTTime(times[0])
		if err != nil {
			return nil, err
		}

		end, err := parseSRTTime(times[1])
		if err != nil {
			return nil, err
		}

		out = append(out, Cue{Start: start, End: end, Text: strings.Join(lines[2:], " ")})
	}

	return out, nil
}

func parseSRTTime(s string) (float64, error) {
	s = strings.TrimSpace(s)
	parts := strings.Split(s, ":")

	if len(parts) != 3 {
		return 0, fmt.Errorf("studio: bad caption time %q", s)
	}

	secParts := strings.Split(parts[2], ",")
	if len(secParts) != 2 {
		return 0, fmt.Errorf("studio: bad caption time %q", s)
	}

	h, err1 := strconv.Atoi(parts[0])
	m, err2 := strconv.Atoi(parts[1])
	sec, err3 := strconv.Atoi(secParts[0])
	ms, err4 := strconv.Atoi(secParts[1])

	if err1 != nil || err2 != nil || err3 != nil || err4 != nil {
		return 0, fmt.Errorf("studio: bad caption time %q", s)
	}

	return float64(h*3600+m*60+sec) + float64(ms)/1000, nil
}

// CaptionsMatch reports whether the file cues are the cues that were burned.
func CaptionsMatch(file []Cue, burned []Cue) error {
	if len(file) != len(burned) {
		return fmt.Errorf("studio: caption file has %d cues, the burn list has %d", len(file), len(burned))
	}

	for i := range file {
		if file[i].Text != burned[i].Text {
			return fmt.Errorf("studio: caption %d text is %q, burned %q", i+1, file[i].Text, burned[i].Text)
		}

		if abs(file[i].Start-burned[i].Start) > 0.05 || abs(file[i].End-burned[i].End) > 0.05 {
			return fmt.Errorf("studio: caption %d times do not match the burn list", i+1)
		}
	}

	return nil
}

func abs(v float64) float64 {
	if v < 0 {
		return -v
	}

	return v
}
