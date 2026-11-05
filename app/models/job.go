package models

import "github.com/AlexGalhardo/vukem/orm"

// Job is one video, from the brief through the checked MP4.
// A download is offered only when Status is ready.
type Job struct {
	orm.Model

	UserID          int64  `json:"user_id"`
	Status          string `json:"status"`
	Goal            string `json:"goal"`
	Audience        string `json:"audience"`
	Subject         string `json:"subject"`
	Duration        int    `json:"duration"`
	Ratio           string `json:"ratio"`
	StyleSkill      string `json:"style_skill"`
	Language        string `json:"language"`
	Facts           string `json:"facts"`
	Links           string `json:"links"`
	CallToAction    string `json:"call_to_action"`
	Voice           string `json:"voice"`
	MusicLicense    string `json:"music_license"`
	Prompt          string `json:"prompt"`
	ModelID         string `json:"model_id"`
	PlanJSON        string `json:"plan_json"`
	RawModel        string `json:"raw_model"`
	Script          string `json:"script"`
	Failure         string `json:"failure"`
	SidecarJSON     string `json:"sidecar_json"`
	PackPlatform    string `json:"pack_platform"`
	PackTitle       string `json:"pack_title"`
	PackDescription string `json:"pack_description"`
	PackHashtags    string `json:"pack_hashtags"`
}
