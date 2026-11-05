// Package studio compiles a brief, plans a cut, and checks the rendered file.
package studio

import "strings"

// Status values of a video job. A file is downloadable only when the status
// is ready.
const (
	StatusQueued    = "queued"
	StatusRendering = "rendering"
	StatusReady     = "ready"
	StatusFailed    = "failed"
)

// Voice sources. None is a silent cut. TTS is the local synthesizer.
// Upload is a WAV the operator recorded.
const (
	VoiceNone   = "none"
	VoiceTTS    = "tts"
	VoiceUpload = "upload"
)

// Brief is the operator's input. The compiler and the planner both read it.
// The browser is not the gate: the server fills this from a validated request.
type Brief struct {
	Goal         string
	Audience     string
	Subject      string
	Duration     int
	Ratio        string
	StyleSkill   string
	Language     string
	Facts        []string
	Links        string
	CallToAction string
	Voice        string
	MusicLicense string
}

// Spoken reports whether the cut has a voice track.
func (b Brief) Spoken() bool { return b.Voice == VoiceTTS || b.Voice == VoiceUpload }

// SplitLines returns the non-empty trimmed lines of s.
func SplitLines(s string) []string {
	var out []string

	for line := range strings.SplitSeq(s, "\n") {
		line = strings.TrimSpace(line)
		if line != "" {
			out = append(out, line)
		}
	}

	return out
}

// Frame is the pixel size of a brief ratio.
func Frame(ratio string) (width, height int, ok bool) {
	switch ratio {
	case "9:16":
		return 1080, 1920, true
	case "1:1":
		return 1080, 1080, true
	case "4:5":
		return 1080, 1350, true
	case "16:9":
		return 1920, 1080, true
	default:
		return 0, 0, false
	}
}

// DrawFPS is the rate the style skill draws at. The encoder repeats frames
// to EncodeFPS so a player accepts a constant rate. traco-simples boils at
// 12 fps; every other style uses 30.
func DrawFPS(style string) int {
	if style == "traco-simples" {
		return 12
	}

	return EncodeFPS
}

// EncodeFPS is the constant rate written into the MP4.
const EncodeFPS = 30

// Background is a flat color for the style, as an FFmpeg lavfi value.
// traco-simples is a saturated field with no gradient.
func Background(style string) string {
	if style == "traco-simples" {
		return "0xFF5A1F"
	}

	return "0x111827"
}
