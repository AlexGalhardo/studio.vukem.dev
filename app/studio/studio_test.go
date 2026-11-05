package studio

import (
	"context"
	"math"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestCompileQuotesFactsAndFrame(t *testing.T) {
	t.Parallel()

	brief := Brief{
		Goal: "Visit the harbor", Audience: "neighbors", Subject: "Saturday market",
		Duration: 6, Ratio: "9:16", StyleSkill: "traco-simples", Language: "en",
		Facts: []string{"the harbor opens at 6"}, CallToAction: "Come early",
	}

	prompt := Compile(brief, LoadSkill(brief.StyleSkill))

	for _, want := range []string{
		"the harbor opens at 6",
		"Frame size: 1080x1920",
		"Duration: 6 seconds",
		"Skill id: traco-simples",
		"Target file: output.mp4",
		"Do not browse the web.",
		"No outline, no shadow, no gradient.",
	} {
		if !strings.Contains(prompt, want) {
			t.Errorf("prompt missing %q", want)
		}
	}
}

func TestValidStyle(t *testing.T) {
	t.Parallel()

	if !ValidStyle("traco-simples") {
		t.Fatal("traco-simples should be a style")
	}

	if ValidStyle("no-such-style") || ValidStyle("engenharia-do-projeto") || ValidStyle("../traco-simples") {
		t.Fatal("unknown or non-visual ids must be rejected")
	}
}

func TestParsePlanRejectsGarbage(t *testing.T) {
	t.Parallel()

	if _, err := ParsePlan("{"); err == nil {
		t.Fatal("invalid JSON was accepted")
	}
}

func TestCaptionsRoundTrip(t *testing.T) {
	t.Parallel()

	cues := []Cue{{Start: 0, End: 1.5, Text: "the harbor opens at 6"}}
	parsed, err := ParseSRT(WriteSRT(cues))

	if err != nil {
		t.Fatal(err)
	}

	if err := CaptionsMatch(parsed, cues); err != nil {
		t.Fatal(err)
	}

	if err := SRTError(WriteSRT(cues), 1.4); err == nil {
		t.Fatal("a cue that ends after the video was accepted")
	}
}

func TestPackLimitsMatchSkillFile(t *testing.T) {
	t.Parallel()

	doc, err := PlatformFile()
	if err != nil {
		t.Fatal(err)
	}

	text, _ := doc["limites_texto"].(map[string]any)

	cases := []struct {
		name string
		key  string
		got  int
	}{
		{"youtube", "titulo_max_caracteres", PlatformLimits["youtube"].TitleMax},
		{"youtube", "descricao_max_caracteres", PlatformLimits["youtube"].DescriptionMax},
		{"youtube", "descricao_max_bytes_api", PlatformLimits["youtube"].DescriptionBytes},
		{"youtube", "hashtags_max", PlatformLimits["youtube"].HashtagsMax},
		{"shorts", "titulo_max_caracteres", PlatformLimits["shorts"].TitleMax},
		{"reels", "legenda_max_caracteres", PlatformLimits["reels"].DescriptionMax},
		{"reels", "hashtags_max", PlatformLimits["reels"].HashtagsMax},
		{"tiktok", "legenda_max_caracteres_api", PlatformLimits["tiktok"].DescriptionMax},
	}

	for _, tc := range cases {
		raw, ok := text[tc.name].(map[string]any)[tc.key].(float64)
		if !ok || int(raw) != tc.got {
			t.Errorf("%s %s = %v, catalog has %d", tc.name, tc.key, text[tc.name].(map[string]any)[tc.key], tc.got)
		}
	}

	if text["tiktok"].(map[string]any)["hashtags_max"] != nil {
		t.Fatal("tiktok hashtags_max changed; the pack checker treats it as unlimited")
	}
}

func TestPackRejectsTitleAndHashtags(t *testing.T) {
	t.Parallel()

	long := strings.Repeat("a", 101)
	if err := PackError(Pack{Platform: "youtube", Title: long}); err == nil {
		t.Fatal("youtube title over 100 was accepted")
	}

	tags := "#one #two #three #four #five #six"
	if err := PackError(Pack{Platform: "reels", Title: "Hello", Hashtags: tags}); err == nil {
		t.Fatal("reels pack with 6 hashtags was accepted")
	}

	if err := PackError(Pack{Platform: "youtube", Title: "a < b"}); err == nil {
		t.Fatal("angle brackets were accepted")
	}
}

func TestUnlicensedBedIsAbsent(t *testing.T) {
	t.Parallel()

	voice := Synthesize("the harbor opens at six", 2, 48000)
	plain, bed := Mix(voice, 48000, "")

	if bed {
		t.Fatal("empty license still mixed a bed")
	}

	licensed, bed := Mix(voice, 48000, "Pixabay 123, free for commercial use")
	if !bed {
		t.Fatal("a license record did not add a bed")
	}

	quiet := Goertzel(plain, 48000, 80)
	busy := Goertzel(licensed, 48000, 80)

	if busy < quiet*20 {
		t.Fatalf("80 Hz power with a license (%v) is not above the voice alone (%v)", busy, quiet)
	}
}

func TestHyperFramesAdapterWritesAFile(t *testing.T) {
	t.Parallel()

	dir := t.TempDir()
	bin := filepath.Join(dir, "hyperframes")
	script := "#!/bin/sh\nout=\"$2\"\nw=\"$3\"\nh=\"$4\"\nd=\"$5\"\nexec ffmpeg -y -loglevel error -f lavfi -i \"color=c=0x2244aa:s=${w}x${h}:r=30:d=${d}\" -c:v libx264 -preset ultrafast -pix_fmt yuv420p -movflags +faststart -an \"$out\"\n"

	if err := os.WriteFile(bin, []byte(script), 0o755); err != nil {
		t.Fatal(err)
	}

	job := filepath.Join(dir, "job")
	if err := os.Mkdir(job, 0o755); err != nil {
		t.Fatal(err)
	}

	if err := os.WriteFile(filepath.Join(job, "captions.srt"), []byte("1\n00:00:00,000 --> 00:00:00,800\nHello\n"), 0o644); err != nil {
		t.Fatal(err)
	}

	err := (HyperFramesRenderer{Bin: bin}).Render(context.Background(), RenderRequest{
		Dir: job, Width: 320, Height: 568, Duration: 1, Color: "0x111827", SRT: filepath.Join(job, "captions.srt"),
	})
	if err != nil {
		t.Fatal(err)
	}

	fast, err := FastStart(filepath.Join(job, pendingName))
	if err != nil || !fast {
		t.Fatalf("faststart = %v, %v", fast, err)
	}
}

func TestLoudnormHitsTheGate(t *testing.T) {
	t.Parallel()

	dir := t.TempDir()
	raw := filepath.Join(dir, "raw.wav")
	norm := filepath.Join(dir, "norm.wav")

	if err := WriteWAV(raw, Synthesize("hello harbor", 2, 48000), 48000); err != nil {
		t.Fatal(err)
	}

	if err := Loudnorm(context.Background(), raw, norm); err != nil {
		t.Fatal(err)
	}

	integrated, peak, err := MeasureLoudness(context.Background(), norm)
	if err != nil {
		t.Fatal(err)
	}

	if math.Abs(integrated-(-14)) > 2 || peak > -1.5 {
		t.Fatalf("loudness = %.2f LUFS, %.2f dBTP", integrated, peak)
	}
}
