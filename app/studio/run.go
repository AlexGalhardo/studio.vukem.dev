package studio

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"math"
	"os"
	"path/filepath"
	"strings"
)

// State is the job row the worker updates. The HTTP layer persists it.
type State struct {
	ID        int64
	Brief     Brief
	Prompt    string
	ModelID   string
	Status    string
	Failure   string
	Script    string
	PlanJSON  string
	RawModel  string
	Sidecar   string
	VoiceFile string
}

// Runner is the worker's view of the process: where files go, who plans,
// who encodes.
type Runner struct {
	Root     string
	Planner  Planner
	Renderer Renderer
	Save     func(context.Context, State) error
}

// Run moves a job from queued to ready or failed. A business failure is
// stored on the row and returned as nil so the queue does not retry it into
// a second file. The previous ready file stays in place until a new file passes.
func Run(ctx context.Context, st State, run Runner) error {
	if run.Planner == nil {
		run.Planner = LocalPlanner{}
	}

	if run.Renderer == nil {
		run.Renderer = FFmpegRenderer{}
	}

	st.Status = StatusRendering
	st.Failure = ""

	if err := run.save(ctx, st); err != nil {
		return err
	}

	dir := filepath.Join(run.Root, fmt.Sprintf("%d", st.ID))
	if err := os.MkdirAll(dir, 0o755); err != nil {
		return err
	}

	plan, raw, err := run.Planner.Plan(ctx, st.Prompt, st.Brief)
	st.RawModel = raw
	st.ModelID = run.Planner.ID()

	if errors.Is(err, ErrNoKey) || errors.Is(err, ErrModelCall) || errors.Is(err, ErrOverCost) {
		return run.fail(ctx, st, dir, err.Error())
	}

	if err != nil {
		return run.fail(ctx, st, dir, "the model output is not a scene plan")
	}

	plan, err = ParsePlan(raw)
	if err != nil {
		return run.fail(ctx, st, dir, "the model output is not a scene plan")
	}

	st.PlanJSON = raw
	st.Script = plan.Script

	if math.Abs(plan.Duration-float64(st.Brief.Duration)) > 0.5 {
		return run.fail(ctx, st, dir, "the plan duration does not fit the brief")
	}

	width, height, _ := Frame(st.Brief.Ratio)
	if plan.Width != width || plan.Height != height {
		return run.fail(ctx, st, dir, "the plan frame does not match the brief")
	}

	for _, fact := range st.Brief.Facts {
		if !strings.Contains(plan.Script, fact) {
			return run.fail(ctx, st, dir, "must-keep fact missing from the script: "+fact)
		}
	}

	var (
		wavPath string
		bed     bool
		timer   string
		cues    []Cue
	)

	if st.Brief.Spoken() {
		var words []Word

		wavPath, bed, timer, words, err = prepareVoice(ctx, dir, st, plan)
		if err != nil {
			return run.fail(ctx, st, dir, err.Error())
		}

		cues = CuesFromWords(words)
	} else {
		cues = CuesFromShots(plan.Shots)
	}

	if len(cues) == 0 {
		return run.fail(ctx, st, dir, "the plan has no captions")
	}

	srt := WriteSRT(cues)
	if err := os.WriteFile(filepath.Join(dir, captionName), []byte(srt), 0o644); err != nil {
		return err
	}

	if err := os.WriteFile(filepath.Join(dir, "composition.html"), []byte(composition(st, plan)), 0o644); err != nil {
		return err
	}

	req := RenderRequest{
		Dir:      dir,
		Width:    plan.Width,
		Height:   plan.Height,
		Duration: plan.Duration,
		Color:    Background(st.Brief.StyleSkill),
		WAV:      wavPath,
		SRT:      filepath.Join(dir, captionName),
	}

	if err := run.Renderer.Render(ctx, req); err != nil {
		return run.fail(ctx, st, dir, err.Error())
	}

	report, err := CheckFile(ctx, QAInput{
		Path:     req.PendingPath(),
		Plan:     plan,
		Brief:    st.Brief,
		Cues:     cues,
		HasVoice: st.Brief.Spoken(),
		HasBed:   bed,
	})
	if err != nil {
		return run.fail(ctx, st, dir, err.Error())
	}

	if !report.OK {
		return run.fail(ctx, st, dir, firstFailure(report))
	}

	final := filepath.Join(dir, finalName)
	if err := os.Rename(req.PendingPath(), final); err != nil {
		return run.fail(ctx, st, dir, err.Error())
	}

	side := Sidecar{
		Renderer:        run.Renderer.Name(),
		RendererVersion: run.Renderer.Version(ctx),
		FFmpegVersion:   FFmpegVersion(ctx),
		SkillID:         st.Brief.StyleSkill,
		Prompt:          st.Prompt,
		ModelID:         st.ModelID,
		DrawFPS:         plan.FPS,
		EncodeFPS:       EncodeFPS,
		MusicLicense:    strings.TrimSpace(st.Brief.MusicLicense),
		MusicBed:        bed,
		WordTimer:       timer,
		Script:          plan.Script,
		CaptionsSHA256:  sha256Hex([]byte(srt)),
		Report:          report,
	}

	body, err := json.MarshalIndent(side, "", "  ")
	if err != nil {
		return err
	}

	if err := os.WriteFile(filepath.Join(dir, "sidecar.json"), body, 0o644); err != nil {
		return err
	}

	st.Sidecar = string(body)
	st.Status = StatusReady
	st.Failure = ""

	return run.save(ctx, st)
}

// Sidecar is the JSON file stored next to a ready MP4.
type Sidecar struct {
	Renderer        string `json:"renderer"`
	RendererVersion string `json:"renderer_version"`
	FFmpegVersion   string `json:"ffmpeg_version"`
	SkillID         string `json:"skill_id"`
	Prompt          string `json:"prompt"`
	ModelID         string `json:"model_id"`
	DrawFPS         int    `json:"draw_fps"`
	EncodeFPS       int    `json:"encode_fps"`
	MusicLicense    string `json:"music_license,omitempty"`
	MusicBed        bool   `json:"music_bed"`
	WordTimer       string `json:"word_timer,omitempty"`
	Script          string `json:"script"`
	CaptionsSHA256  string `json:"captions_sha256,omitempty"`
	Report          Report `json:"report"`
}

func (run Runner) save(ctx context.Context, st State) error {
	if run.Save == nil {
		return nil
	}

	return run.Save(ctx, st)
}

func (run Runner) fail(ctx context.Context, st State, dir, msg string) error {
	_ = os.Remove(filepath.Join(dir, pendingName))

	if _, err := os.Stat(filepath.Join(dir, finalName)); err == nil {
		st.Status = StatusReady
		st.Failure = "The new render failed and the previous file is still ready. " + msg
	} else {
		st.Status = StatusFailed
		st.Failure = msg
	}

	if err := run.save(ctx, st); err != nil {
		return err
	}

	return nil
}

func firstFailure(report Report) string {
	for _, check := range report.Checks {
		if !check.OK {
			return check.Name + ": " + check.Detail
		}
	}

	return "the file failed the check"
}

func prepareVoice(ctx context.Context, dir string, st State, plan Plan) (wav string, bed bool, timer string, words []Word, err error) {
	var samples []float64

	switch st.Brief.Voice {
	case VoiceUpload:
		if st.VoiceFile == "" {
			return "", false, "", nil, fmt.Errorf("upload a WAV recording")
		}

		duration, err := MediaDuration(ctx, st.VoiceFile)
		if err != nil {
			return "", false, "", nil, err
		}

		if math.Abs(duration-float64(st.Brief.Duration)) > 0.5 {
			return "", false, "", nil, fmt.Errorf("the voice track does not fit the requested duration")
		}

		decoded, rate, err := DecodeWAV(st.VoiceFile)
		if err != nil {
			decoded, err = DecodeMono(ctx, st.VoiceFile)
			rate = sampleRate
		}

		if err != nil {
			return "", false, "", nil, err
		}

		// ffprobe measured the header; the samples we hold decide the real length,
		// and resample sizes its output from it.
		if rate > 0 && math.Abs(float64(len(decoded))/float64(rate)-float64(st.Brief.Duration)) > 0.5 {
			return "", false, "", nil, fmt.Errorf("the voice track does not fit the requested duration")
		}

		if rate != sampleRate && rate > 0 {
			decoded = resample(decoded, rate, sampleRate)
		}

		samples = decoded
	default:
		samples = Synthesize(plan.Script, float64(st.Brief.Duration), sampleRate)
	}

	words, timer = AlignWords(samples, sampleRate, plan.Script, plan.Duration)
	mixed, bed := Mix(samples, sampleRate, st.Brief.MusicLicense)

	rawPath := filepath.Join(dir, "voice-raw.wav")
	if err := WriteWAV(rawPath, mixed, sampleRate); err != nil {
		return "", false, "", nil, err
	}

	normPath := filepath.Join(dir, "voice.wav")
	if err := Loudnorm(ctx, rawPath, normPath); err != nil {
		return "", false, "", nil, err
	}

	_ = os.Remove(rawPath)

	return normPath, bed, timer, words, nil
}

func resample(in []float64, from, to int) []float64 {
	if from == to || len(in) == 0 {
		return in
	}

	outLen := int(float64(len(in)) * float64(to) / float64(from))
	if outLen < 1 {
		outLen = 1
	}

	out := make([]float64, outLen)

	for i := range out {
		src := float64(i) * float64(from) / float64(to)
		j := int(src)

		if j >= len(in) {
			j = len(in) - 1
		}

		out[i] = in[j]
	}

	return out
}

func composition(st State, plan Plan) string {
	width, height, _ := Frame(st.Brief.Ratio)
	var b strings.Builder

	fmt.Fprintf(&b, "<!doctype html><html><head><meta charset=\"utf-8\"><title>%s</title>\n", escape(st.Brief.Subject))
	fmt.Fprintf(&b, "<style>html,body{margin:0;background:#%s;color:#fff;font-family:sans-serif}main{width:%dpx;height:%dpx;display:flex;align-items:center;justify-content:center;text-align:center;padding:48px}</style></head>\n", strings.TrimPrefix(Background(st.Brief.StyleSkill), "0x"), width, height)
	b.WriteString("<body><main><p>")
	b.WriteString(escape(plan.Script))
	b.WriteString("</p></main></body></html>\n")

	return b.String()
}

func escape(s string) string {
	r := strings.NewReplacer("&", "&amp;", "<", "&lt;", ">", "&gt;")

	return r.Replace(s)
}

func sha256Hex(b []byte) string {
	sum := sha256.Sum256(b)

	return hex.EncodeToString(sum[:])
}
