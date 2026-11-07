package studio

import (
	"fmt"
	"strings"
)

// FPS is the frame rate every render uses; the prompt states it.
const FPS = 30

// Compile builds the one prompt a job stores and sends. The skill is the
// visual law, must-keep facts are quoted as constraints, and the frame size
// and duration are stated so the plan fits the render.
func Compile(b Brief, sk Skill, width int) (string, error) {
	w, h, err := Frame(b.Ratio, width)
	if err != nil {
		return "", err
	}

	var p strings.Builder

	p.WriteString("You write the scene plan for a short silent video. Answer with one JSON object and nothing else.\n\n")
	fmt.Fprintf(&p, "## Brief\n- Goal: %s\n- Audience: %s\n- Subject: %s\n- Spoken language of on-screen text: %s\n", b.Goal, b.Audience, b.Subject, b.Language)

	if b.CTA != "" {
		fmt.Fprintf(&p, "- Call to action (last scene): %s\n", b.CTA)
	}

	fmt.Fprintf(&p, "\n## Output file\n- Frame: %dx%d (%s) at %d fps\n- Total duration: %d seconds; scene seconds must add up to it\n", w, h, b.Ratio, FPS, b.Duration)

	if facts := Lines(b.Facts); len(facts) > 0 {
		p.WriteString("\n## Must-keep facts (constraints: use them verbatim, never contradict them, never add claims beyond them)\n")

		for _, f := range facts {
			fmt.Fprintf(&p, "- %s\n", f)
		}
	}

	if links := Lines(b.Links); len(links) > 0 {
		p.WriteString("\n## Reference links (you cannot browse them; cite them only if the brief needs it)\n")

		for _, l := range links {
			fmt.Fprintf(&p, "- %s\n", l)
		}
	}

	body := sk.Body
	if len(body) > maxSkillBody {
		body = body[:maxSkillBody]
	}

	fmt.Fprintf(&p, "\n## Style skill: %s\nFollow this skill. Do not invent a second visual system.\n\n%s\n", sk.ID, body)

	p.WriteString(`
## JSON shape
{"title": "string", "description": "string", "scenes": [{"title": "string", "text": "string", "seconds": number, "color": "#RRGGBB"}]}
`)

	return p.String(), nil
}
