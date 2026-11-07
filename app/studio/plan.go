package studio

import (
	"encoding/json"
	"errors"
	"fmt"
	"math"
	"regexp"
	"strings"
)

// Scene is one card of the plan.
type Scene struct {
	Title   string  `json:"title"`
	Text    string  `json:"text"`
	Seconds float64 `json:"seconds"`
	Color   string  `json:"color"`
}

// ScenePlan is the structured output the model must return.
type ScenePlan struct {
	Title       string  `json:"title"`
	Description string  `json:"description"`
	Scenes      []Scene `json:"scenes"`
}

// Plan limits.
const (
	MaxScenes    = 40
	MaxSceneText = 200
	MaxSceneSecs = 60.0
	MinSceneSecs = 0.5
)

var (
	hexColor = regexp.MustCompile(`^#[0-9a-fA-F]{6}$`)

	// ErrBadPlan wraps every plan validation failure.
	ErrBadPlan = errors.New("studio: invalid scene plan")
)

// ParsePlan extracts and validates the plan in a model reply. The reply may
// wrap the JSON in a code fence or prose; only the outermost object counts.
func ParsePlan(raw string, wantSeconds int) (ScenePlan, error) {
	var plan ScenePlan

	start, end := strings.Index(raw, "{"), strings.LastIndex(raw, "}")
	if start < 0 || end <= start {
		return plan, fmt.Errorf("%w: no JSON object in the reply", ErrBadPlan)
	}

	dec := json.NewDecoder(strings.NewReader(raw[start : end+1]))
	dec.DisallowUnknownFields()

	if err := dec.Decode(&plan); err != nil {
		return ScenePlan{}, fmt.Errorf("%w: %s", ErrBadPlan, err)
	}

	return plan, plan.Validate(wantSeconds)
}

// Validate checks the plan against the brief's duration (10 percent or one
// second of slack, whichever is larger).
func (p *ScenePlan) Validate(wantSeconds int) error {
	if strings.TrimSpace(p.Title) == "" {
		return fmt.Errorf("%w: title is empty", ErrBadPlan)
	}

	if n := len(p.Scenes); n == 0 || n > MaxScenes {
		return fmt.Errorf("%w: %d scenes, want 1 to %d", ErrBadPlan, n, MaxScenes)
	}

	var total float64

	for i := range p.Scenes {
		s := &p.Scenes[i]

		if strings.TrimSpace(s.Text) == "" && strings.TrimSpace(s.Title) == "" {
			return fmt.Errorf("%w: scene %d has no text", ErrBadPlan, i+1)
		}

		if len([]rune(s.Text)) > MaxSceneText || len([]rune(s.Title)) > MaxSceneText {
			return fmt.Errorf("%w: scene %d text is over %d characters", ErrBadPlan, i+1, MaxSceneText)
		}

		if math.IsNaN(s.Seconds) || s.Seconds < MinSceneSecs || s.Seconds > MaxSceneSecs {
			return fmt.Errorf("%w: scene %d seconds %.2f out of range", ErrBadPlan, i+1, s.Seconds)
		}

		if !hexColor.MatchString(s.Color) {
			s.Color = palette[i%len(palette)]
		}

		total += s.Seconds
	}

	slack := math.Max(1, float64(wantSeconds)*0.1)
	if math.Abs(total-float64(wantSeconds)) > slack {
		return fmt.Errorf("%w: scenes last %.1fs, brief wants %ds", ErrBadPlan, total, wantSeconds)
	}

	return nil
}

// TotalSeconds sums the scene durations.
func (p ScenePlan) TotalSeconds() float64 {
	var t float64
	for _, s := range p.Scenes {
		t += s.Seconds
	}

	return t
}

var palette = []string{"#1f2937", "#7c2d12", "#134e4a", "#4c1d95", "#831843", "#1e3a8a"}
