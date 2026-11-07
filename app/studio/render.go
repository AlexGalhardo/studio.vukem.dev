package studio

import (
	"bytes"
	"context"
	"encoding/binary"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"math"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"time"
)

// Sidecar is the provenance record stored next to every output.
type Sidecar struct {
	Renderer      string  `json:"renderer"`
	FFmpegVersion string  `json:"ffmpeg_version"`
	Skill         string  `json:"skill"`
	Model         string  `json:"model"`
	Prompt        string  `json:"prompt"`
	Seconds       float64 `json:"seconds"`
	Width         int     `json:"width"`
	Height        int     `json:"height"`
}

// Renderer writes an MP4 to out (atomically: a failed run leaves the old
// file) and returns its sidecar. progress receives 0..100.
type Renderer interface {
	Render(ctx context.Context, plan ScenePlan, b Brief, prompt, out string, progress func(int)) (Sidecar, error)
}

// ErrQA means the file was produced but failed a QA rule.
var ErrQA = errors.New("studio: render failed QA")

// FFmpeg renders each scene as a text card with FFmpeg, concatenates them,
// and checks the result with ffprobe. Every command is an argument list;
// scene text goes through files, never through a shell or a filter string.
type FFmpeg struct {
	Bin, Probe, Font string
	Width            int
}

// NewFFmpeg builds the renderer from cfg.
func NewFFmpeg(cfg Config) FFmpeg {
	return FFmpeg{Bin: cfg.FFmpeg, Probe: cfg.FFprobe, Font: cfg.FontFile, Width: cfg.RenderWidth}
}

// Render implements Renderer.
func (f FFmpeg) Render(ctx context.Context, plan ScenePlan, b Brief, prompt, out string, progress func(int)) (Sidecar, error) {
	w, h, err := Frame(b.Ratio, f.Width)
	if err != nil {
		return Sidecar{}, err
	}

	font, err := f.fontFile()
	if err != nil {
		return Sidecar{}, err
	}

	version, err := f.version(ctx)
	if err != nil {
		return Sidecar{}, err
	}

	if err := os.MkdirAll(filepath.Dir(out), 0o750); err != nil {
		return Sidecar{}, err
	}

	work, err := os.MkdirTemp(filepath.Dir(out), ".render-")
	if err != nil {
		return Sidecar{}, err
	}

	defer func() { _ = os.RemoveAll(work) }()

	var list strings.Builder

	for i, s := range plan.Scenes {
		clip := filepath.Join(work, fmt.Sprintf("scene-%03d.mp4", i))
		if err := f.card(ctx, s, font, w, h, work, i, clip); err != nil {
			return Sidecar{}, err
		}

		fmt.Fprintf(&list, "file '%s'\n", filepath.Base(clip))
		progress(int(float64(i+1) / float64(len(plan.Scenes)+1) * 100))
	}

	listFile := filepath.Join(work, "list.txt")
	if err := os.WriteFile(listFile, []byte(list.String()), 0o600); err != nil {
		return Sidecar{}, err
	}

	tmp := filepath.Join(work, "out.mp4")

	if err := f.run(ctx, work, f.Bin, "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", "list.txt",
		"-c", "copy", "-an", "-movflags", "+faststart", "out.mp4"); err != nil {
		return Sidecar{}, err
	}

	if err := f.QA(ctx, tmp, w, h, plan.TotalSeconds()); err != nil {
		return Sidecar{}, err
	}

	if err := os.Rename(tmp, out); err != nil {
		return Sidecar{}, err
	}

	progress(100)

	return Sidecar{
		Renderer: "ffmpeg-text-cards", FFmpegVersion: version, Skill: b.Skill, Model: b.Model,
		Prompt: prompt, Seconds: plan.TotalSeconds(), Width: w, Height: h,
	}, nil
}

// card renders one scene.
func (f FFmpeg) card(ctx context.Context, s Scene, font string, w, h int, work string, i int, clip string) error {
	titleFile := filepath.Join(work, fmt.Sprintf("title-%03d.txt", i))
	textFile := filepath.Join(work, fmt.Sprintf("text-%03d.txt", i))

	bodySize, titleSize := max(12, w/22), max(16, w/14)
	cols := max(8, w*9/10/(bodySize*6/10))

	if err := os.WriteFile(titleFile, []byte(wrap(s.Title, cols*bodySize/titleSize)), 0o600); err != nil {
		return err
	}

	if err := os.WriteFile(textFile, []byte(wrap(s.Text, cols)), 0o600); err != nil {
		return err
	}

	ff := escapeFilterValue(font)
	vf := fmt.Sprintf(
		"drawtext=fontfile=%s:textfile=%s:fontsize=%d:fontcolor=white:x=(w-text_w)/2:y=h*0.30-text_h/2,"+
			"drawtext=fontfile=%s:textfile=%s:fontsize=%d:fontcolor=white@0.92:x=(w-text_w)/2:y=h*0.52:line_spacing=%d",
		ff, filepath.Base(titleFile), titleSize, ff, filepath.Base(textFile), bodySize, bodySize/4)

	src := fmt.Sprintf("color=c=%s:s=%dx%d:r=%d:d=%.3f", "0x"+strings.TrimPrefix(s.Color, "#"), w, h, FPS, s.Seconds)

	return f.run(ctx, work, f.Bin, "-y", "-v", "error", "-f", "lavfi", "-i", src, "-vf", vf,
		"-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-r", fmt.Sprint(FPS), "-an", filepath.Base(clip))
}

// QA applies the pipeline QA rules for a silent file.
func (f FFmpeg) QA(ctx context.Context, path string, w, h int, wantSeconds float64) error {
	cmd := exec.CommandContext(ctx, f.Probe, "-v", "error", "-print_format", "json", "-show_streams", "-show_format", path)

	var stdout bytes.Buffer

	cmd.Stdout = &stdout

	if err := cmd.Run(); err != nil {
		return fmt.Errorf("%w: ffprobe cannot read the file", ErrQA)
	}

	var p struct {
		Streams []struct {
			Type   string `json:"codec_type"`
			Codec  string `json:"codec_name"`
			PixFmt string `json:"pix_fmt"`
			Width  int    `json:"width"`
			Height int    `json:"height"`
		} `json:"streams"`
		Format struct {
			Duration string `json:"duration"`
		} `json:"format"`
	}

	if err := json.Unmarshal(stdout.Bytes(), &p); err != nil {
		return fmt.Errorf("%w: ffprobe output is not JSON", ErrQA)
	}

	if len(p.Streams) != 1 || p.Streams[0].Type != "video" {
		return fmt.Errorf("%w: want exactly one video stream and no audio, got %d streams", ErrQA, len(p.Streams))
	}

	v := p.Streams[0]
	if v.Codec != "h264" || v.PixFmt != "yuv420p" {
		return fmt.Errorf("%w: codec %s pix_fmt %s, want h264 yuv420p", ErrQA, v.Codec, v.PixFmt)
	}

	if v.Width != w || v.Height != h {
		return fmt.Errorf("%w: frame %dx%d, want %dx%d", ErrQA, v.Width, v.Height, w, h)
	}

	var dur float64
	if _, err := fmt.Sscanf(p.Format.Duration, "%f", &dur); err != nil || math.Abs(dur-wantSeconds) > 0.5 {
		return fmt.Errorf("%w: duration %s, want about %.1fs", ErrQA, p.Format.Duration, wantSeconds)
	}

	if ok, err := Faststart(path); err != nil || !ok {
		return fmt.Errorf("%w: moov atom is not before mdat (no faststart)", ErrQA)
	}

	return nil
}

// Faststart reports whether the moov atom comes before mdat.
func Faststart(path string) (bool, error) {
	fh, err := os.Open(path) //nolint:gosec // path is built by the renderer
	if err != nil {
		return false, err
	}

	defer func() { _ = fh.Close() }()

	for {
		var hdr [8]byte
		if _, err := io.ReadFull(fh, hdr[:]); err != nil {
			return false, nil //nolint:nilerr // ran out of file before any moov
		}

		size := int64(binary.BigEndian.Uint32(hdr[:4]))

		switch string(hdr[4:]) {
		case "moov":
			return true, nil
		case "mdat":
			return false, nil
		}

		if size < 8 {
			return false, nil
		}

		if _, err := fh.Seek(size-8, io.SeekCurrent); err != nil {
			return false, err
		}
	}
}

func (f FFmpeg) version(ctx context.Context) (string, error) {
	out, err := exec.CommandContext(ctx, f.Bin, "-version").Output()
	if err != nil {
		return "", fmt.Errorf("ffmpeg is not available (%s): install it or set STUDIO_FFMPEG", f.Bin)
	}

	line, _, _ := strings.Cut(string(out), "\n")

	return strings.TrimSpace(line), nil
}

func (f FFmpeg) run(ctx context.Context, dir, bin string, args ...string) error {
	cmd := exec.CommandContext(ctx, bin, args...)
	cmd.Dir = dir

	var stderr bytes.Buffer

	cmd.Stderr = &stderr

	if err := cmd.Run(); err != nil {
		if ctx.Err() != nil {
			return ctx.Err()
		}

		msg := strings.TrimSpace(stderr.String())
		if len(msg) > 400 {
			msg = msg[len(msg)-400:]
		}

		return fmt.Errorf("ffmpeg failed: %w: %s", err, msg)
	}

	return nil
}

func (f FFmpeg) fontFile() (string, error) {
	candidates := []string{f.Font}
	if f.Font == "" {
		candidates = []string{
			"/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
			"/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
			`C:\Windows\Fonts\arialbd.ttf`,
			"/System/Library/Fonts/Supplemental/Arial Bold.ttf",
		}
	}

	for _, c := range candidates {
		if st, err := os.Stat(c); c != "" && err == nil && !st.IsDir() {
			return c, nil
		}
	}

	return "", fmt.Errorf("no font file found on %s: set STUDIO_FONT_FILE to a .ttf path", runtime.GOOS)
}

// escapeFilterValue quotes a path for an FFmpeg filter option value.
func escapeFilterValue(p string) string {
	p = strings.ReplaceAll(filepath.ToSlash(p), ":", `\\:`)

	return strings.ReplaceAll(p, "'", `\'`)
}

// wrap breaks s into lines of at most cols runes, on spaces where possible.
func wrap(s string, cols int) string {
	var lines []string

	cur := ""

	for _, word := range strings.Fields(s) {
		for len([]rune(word)) > cols {
			r := []rune(word)
			if cur != "" {
				lines = append(lines, cur)
				cur = ""
			}

			lines = append(lines, string(r[:cols]))
			word = string(r[cols:])
		}

		switch {
		case cur == "":
			cur = word
		case len([]rune(cur))+1+len([]rune(word)) <= cols:
			cur += " " + word
		default:
			lines = append(lines, cur)
			cur = word
		}
	}

	if cur != "" {
		lines = append(lines, cur)
	}

	return strings.Join(lines, "\n")
}

// FakeRenderer writes a placeholder file and never runs FFmpeg. Fail makes
// every render fail, for the failure-path tests.
type FakeRenderer struct{ Fail bool }

// Render implements Renderer.
func (r FakeRenderer) Render(_ context.Context, plan ScenePlan, b Brief, prompt, out string, progress func(int)) (Sidecar, error) {
	if r.Fail {
		return Sidecar{}, errors.New("fake: encoder crashed")
	}

	if err := os.MkdirAll(filepath.Dir(out), 0o750); err != nil {
		return Sidecar{}, err
	}

	tmp := out + ".tmp"
	if err := os.WriteFile(tmp, []byte("fake mp4 "+time.Now().UTC().Format(time.RFC3339Nano)), 0o600); err != nil {
		return Sidecar{}, err
	}

	if err := os.Rename(tmp, out); err != nil {
		return Sidecar{}, err
	}

	progress(100)

	return Sidecar{Renderer: "fake", Skill: b.Skill, Model: b.Model, Prompt: prompt, Seconds: plan.TotalSeconds()}, nil
}

// NewRenderer picks the renderer for cfg.
func NewRenderer(cfg Config) Renderer {
	if cfg.Provider == ProviderFake {
		return FakeRenderer{Fail: cfg.FakeRenderFail}
	}

	return NewFFmpeg(cfg)
}
