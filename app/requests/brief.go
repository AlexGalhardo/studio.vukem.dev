package requests

import (
	"mime/multipart"

	"github.com/AlexGalhardo/vukem/z"

	"github.com/AlexGalhardo/vukem-studio/app/studio"
)

// Brief is the dashboard form. The server rejects it when a field is empty
// or the style id is not a kit under .agents/skills.
type Brief struct {
	Goal         string                `json:"goal"           form:"goal"`
	Audience     string                `json:"audience"       form:"audience"`
	Subject      string                `json:"subject"        form:"subject"`
	Duration     int                   `json:"duration"       form:"duration"`
	Ratio        string                `json:"ratio"          form:"ratio"`
	StyleSkill   string                `json:"style_skill"    form:"style_skill"`
	Language     string                `json:"language"       form:"language"`
	Facts        string                `json:"facts"          form:"facts"`
	Links        string                `json:"links"          form:"links"`
	CallToAction string                `json:"call_to_action" form:"call_to_action"`
	Voice        string                `json:"voice"          form:"voice"`
	MusicLicense string                `json:"music_license"  form:"music_license"`
	VoiceFile    *multipart.FileHeader `json:"voice_file"     form:"voice_file"`
}

// BriefSchema validates Brief. Style ids are checked against the catalog,
// not against a value the browser invented.
var BriefSchema = z.Struct[Brief](z.Shape{
	"goal":           z.String().Trim().Min(1).Max(500),
	"audience":       z.String().Trim().Min(1).Max(500),
	"subject":        z.String().Trim().Min(1).Max(500),
	"duration":       z.Int().Min(5).Max(45),
	"ratio":          z.Enum("9:16", "1:1", "4:5", "16:9"),
	"style_skill":    z.String().Trim().Refine(validStyle),
	"language":       z.String().Trim().Min(2).Max(40),
	"facts":          z.String().Trim().Max(5000).Optional().Default(""),
	"links":          z.String().Trim().Max(2000).Optional().Default(""),
	"call_to_action": z.String().Trim().Max(300).Optional().Default(""),
	"voice":          z.Enum(studio.VoiceNone, studio.VoiceTTS, studio.VoiceUpload).Default(studio.VoiceNone),
	"music_license":  z.String().Trim().Max(500).Optional().Default(""),
	"voice_file":     z.File().Optional().Types("audio/wave", "audio/wav"),
}).Refine(func(b Brief) error {
	if b.Voice == studio.VoiceUpload && b.VoiceFile == nil {
		return z.FieldError("voice_file", "Upload a WAV recording or choose text to speech.")
	}

	return nil
})

func validStyle(id string) error {
	if !studio.ValidStyle(id) {
		return z.FieldError("", "Choose a style skill that exists.")
	}

	return nil
}

// Pack is the publish-pack form. Limits come from the publication skill.
type Pack struct {
	Platform    string `json:"platform"    form:"platform"`
	Title       string `json:"title"       form:"title"`
	Description string `json:"description" form:"description"`
	Hashtags    string `json:"hashtags"    form:"hashtags"`
}

// PackSchema validates a pack against the platform ceilings. It does not post anywhere.
var PackSchema = z.Struct[Pack](z.Shape{
	"platform":    z.Enum("youtube", "shorts", "reels", "tiktok"),
	"title":       z.String().Trim().Min(1).Max(5000),
	"description": z.String().Trim().Max(5000).Optional().Default(""),
	"hashtags":    z.String().Trim().Max(2000).Optional().Default(""),
}).Refine(func(p Pack) error {
	return studio.PackError(studio.Pack{
		Platform:    p.Platform,
		Title:       p.Title,
		Description: p.Description,
		Hashtags:    p.Hashtags,
	})
})
