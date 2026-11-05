package studio

import "strings"

// Compile builds the one prompt stored on the job. The skill text is the
// visual law. Facts are constraints, not suggestions. The model is told the
// frame size, the rates, and the file name, and it is not asked to browse.
func Compile(b Brief, skillText string) string {
	width, height, _ := Frame(b.Ratio)

	var doc strings.Builder

	doc.WriteString("You are writing a scene plan for one short video. Follow the skill as visual law. Do not invent a second palette.\n\n")
	doc.WriteString("Skill id: " + b.StyleSkill + "\n")
	doc.WriteString("Skill file:\n")
	doc.WriteString(skillText)
	doc.WriteString("\n\n")
	doc.WriteString("Goal: " + b.Goal + "\n")
	doc.WriteString("Audience: " + b.Audience + "\n")
	doc.WriteString("Subject: " + b.Subject + "\n")
	doc.WriteString("Spoken language: " + b.Language + "\n")
	doc.WriteString("Duration: " + itoa(b.Duration) + " seconds\n")
	doc.WriteString("Aspect ratio: " + b.Ratio + "\n")
	doc.WriteString("Frame size: " + itoa(width) + "x" + itoa(height) + "\n")
	doc.WriteString("Draw rate: " + itoa(DrawFPS(b.StyleSkill)) + " fps\n")
	doc.WriteString("Encode rate: " + itoa(EncodeFPS) + " fps\n")
	doc.WriteString("Target file: output.mp4\n")

	if strings.TrimSpace(b.CallToAction) != "" {
		doc.WriteString("Call to action (last card): " + strings.TrimSpace(b.CallToAction) + "\n")
	}

	if strings.TrimSpace(b.Links) != "" {
		doc.WriteString("Reference links (do not fetch them): " + strings.TrimSpace(b.Links) + "\n")
	}

	if b.Spoken() {
		doc.WriteString("Voice: yes\n")
	} else {
		doc.WriteString("Voice: no. The file has no audio stream.\n")
	}

	doc.WriteString("\nMust-keep facts (constraints; copy each one verbatim; do not invent a replacement):\n")

	if len(b.Facts) == 0 {
		doc.WriteString("- (none)\n")
	} else {
		for _, fact := range b.Facts {
			doc.WriteString("- " + fact + "\n")
		}
	}

	doc.WriteString("\nDo not browse the web.\n")

	return doc.String()
}

func itoa(n int) string {
	if n == 0 {
		return "0"
	}

	var digits [12]byte

	i := len(digits)
	neg := n < 0

	if neg {
		n = -n
	}

	for n > 0 {
		i--
		digits[i] = byte('0' + n%10)
		n /= 10
	}

	if neg {
		i--
		digits[i] = '-'
	}

	return string(digits[i:])
}
