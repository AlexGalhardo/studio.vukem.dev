package studio

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"strings"
	"unicode/utf8"

	"github.com/AlexGalhardo/vukem/z"
)

// Pack is the text an operator copies into a platform. Nothing here is posted.
type Pack struct {
	Platform    string
	Title       string
	Description string
	Hashtags    string
}

// Limits is one platform's text ceiling from the publication skill.
// A zero max means the skill publishes no ceiling for that field.
type Limits struct {
	TitleMax         int
	DescriptionMax   int
	DescriptionBytes int
	HashtagsMax      int
	ForbidAngles     bool
}

// PlatformLimits matches video-direcao-de-arte/kit/plataformas.json
// (limites_texto, verified 2026-10-05). A test fails when the file disagrees.
var PlatformLimits = map[string]Limits{
	"youtube": {TitleMax: 100, DescriptionMax: 5000, DescriptionBytes: 5000, HashtagsMax: 60, ForbidAngles: true},
	"shorts":  {TitleMax: 100, DescriptionMax: 5000, HashtagsMax: 60, ForbidAngles: true},
	"reels":   {DescriptionMax: 2200, HashtagsMax: 5},
	"tiktok":  {DescriptionMax: 2200},
}

// Platforms are the pack targets, in the skill's order.
func Platforms() []string { return []string{"youtube", "shorts", "reels", "tiktok"} }

var hashtagRE = regexp.MustCompile(`#[\p{L}\p{N}_]+`)

// PackError checks the text against the skill limits. The path is a form field.
func PackError(p Pack) error {
	limits, ok := PlatformLimits[p.Platform]
	if !ok {
		return z.FieldError("platform", "Choose youtube, shorts, reels, or tiktok.")
	}

	if strings.TrimSpace(p.Title) == "" {
		return z.FieldError("title", "Enter a title.")
	}

	if limits.TitleMax > 0 && utf8.RuneCountInString(p.Title) > limits.TitleMax {
		return z.FieldError("title", fmt.Sprintf("The title is over the %s limit of %d characters.", p.Platform, limits.TitleMax))
	}

	if limits.ForbidAngles && (strings.Contains(p.Title, "<") || strings.Contains(p.Title, ">") || strings.Contains(p.Description, "<") || strings.Contains(p.Description, ">")) {
		return z.FieldError("title", "The title and description cannot contain < or >.")
	}

	if limits.DescriptionMax > 0 && utf8.RuneCountInString(p.Description) > limits.DescriptionMax {
		return z.FieldError("description", fmt.Sprintf("The description is over the %s limit of %d characters.", p.Platform, limits.DescriptionMax))
	}

	if limits.DescriptionBytes > 0 && len(p.Description) > limits.DescriptionBytes {
		return z.FieldError("description", fmt.Sprintf("The description is over the %s limit of %d bytes.", p.Platform, limits.DescriptionBytes))
	}

	if limits.HashtagsMax > 0 && CountHashtags(p.Title, p.Description, p.Hashtags) > limits.HashtagsMax {
		return z.FieldError("hashtags", fmt.Sprintf("%s allows %d hashtags.", p.Platform, limits.HashtagsMax))
	}

	return nil
}

// CountHashtags counts #tags in every public text field. A tag in the
// description counts as well as one in the hashtag list.
func CountHashtags(parts ...string) int {
	return len(hashtagRE.FindAllString(strings.Join(parts, " "), -1))
}

// SRTError checks that the caption file ends before the video.
func SRTError(srt string, duration float64) error {
	cues, err := ParseSRT(srt)
	if err != nil {
		return z.FieldError("description", "The caption file is not valid.")
	}

	if len(cues) == 0 {
		return z.FieldError("description", "The caption file is empty.")
	}

	if cues[len(cues)-1].End >= duration {
		return z.FieldError("description", "The last caption ends after the video.")
	}

	return nil
}

// PlatformFile is the publication skill's platform table, when the tree is present.
func PlatformFile() (map[string]any, error) {
	root, err := SkillsRoot()
	if err != nil {
		return nil, err
	}

	path := filepath.Join(root, "publicacao", "video-direcao-de-arte", "kit", "plataformas.json")

	body, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}

	var doc map[string]any
	if err := json.Unmarshal(body, &doc); err != nil {
		return nil, err
	}

	return doc, nil
}
