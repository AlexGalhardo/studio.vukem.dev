package requests

import (
	"github.com/AlexGalhardo/vukem/z"

	"github.com/AlexGalhardo/vukem-studio/app/studio"
)

// VideoSchema validates the brief form. Skill and model membership depend on
// configuration, so the controller checks them against the live catalog.
var VideoSchema = z.Struct[studio.Brief](z.Shape{
	"goal":     z.String().Trim().Min(3).Max(300),
	"audience": z.String().Trim().Min(2).Max(200),
	"subject":  z.String().Trim().Min(2).Max(200),
	"duration": z.Int().Min(studio.MinDuration).Max(studio.MaxDuration),
	"ratio":    z.String().Trim().OneOf(studio.Ratios...),
	"skill":    z.String().Trim().Min(1).Max(64),
	"language": z.String().Trim().Min(2).Max(40),
	"model":    z.String().Trim().Min(1).Max(80),
	"facts":    z.String().Trim().Max(studio.MaxFacts * (studio.MaxFactLen + 1)).Optional(),
	"links":    z.String().Trim().Max(studio.MaxLinks * 500).Optional(),
	"cta":      z.String().Trim().Max(200).Optional(),
})
