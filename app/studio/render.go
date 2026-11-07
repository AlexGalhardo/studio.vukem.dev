package studio

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"os"
	"strconv"
	"strings"
)

const (
	pendingName = "output.pending.mp4"
	finalName   = "output.mp4"
	captionName = "captions.srt"
	argsName    = "encode-args.txt"
	sampleRate  = 48000
)

// RenderRequest is one encode. Paths are absolute. The renderer writes only
// the pending file, never a second public object.
type RenderRequest struct {
	Dir      string
	Width    int
	Height   int
	Duration float64
	Color    string
	WAV      string
	SRT      string
}

// PendingPath is the file the encoder writes before the check passes.
func (r RenderRequest) PendingPath() string { return r.Dir + "/" + pendingName }

// Renderer draws and encodes one MP4.
type Renderer interface {
	Name() string
	Version(ctx context.Context) string
	Render(ctx context.Context, req RenderRequest) error
}

// FFmpegRenderer is the silent and spoken path that CI can run. It draws a
// flat field, burns captions.srt with libass, and encodes H.264 yuv420p
// with the moov atom at the front. There is no audio stream when WAV is empty.
type FFmpegRenderer struct{}

// Name is the renderer id stored in the sidecar.
func (FFmpegRenderer) Name() string { return "ffmpeg" }

// Version is the first line of `ffmpeg -version`.
func (FFmpegRenderer) Version(ctx context.Context) string { return FFmpegVersion(ctx) }

// Render encodes req. Arguments are a list, never a shell string.
func (FFmpegRenderer) Render(ctx context.Context, req RenderRequest) error {
	duration := strconv.FormatFloat(req.Duration, 'f', 3, 64)
	color := fmt.Sprintf("color=c=%s:s=%dx%d:r=%d:d=%s", req.Color, req.Width, req.Height, EncodeFPS, duration)

	args := []string{
		"-y", "-hide_banner", "-loglevel", "error",
		"-f", "lavfi", "-i", color,
	}

	if req.WAV != "" {
		args = append(args, "-i", req.WAV)
	}

	if req.SRT != "" {
		args = append(args, "-vf", "subtitles="+captionName+":force_style='FontName=DejaVu Sans,FontSize=18,PrimaryColour=&H00FFFFFF,Alignment=2'")
	}

	args = append(args, "-map", "0:v:0")

	if req.WAV != "" {
		args = append(args, "-map", "1:a:0", "-c:a", "aac", "-b:a", "160k", "-ar", strconv.Itoa(sampleRate), "-ac", "2")
	} else {
		args = append(args, "-an")
	}

	args = append(args,
		"-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
		"-movflags", "+faststart", "-threads", "2",
		pendingName,
	)

	return runEncode(ctx, "ffmpeg", args, req)
}

// HyperFramesRenderer shells out to a HyperFrames-compatible command.
// The contract is: bin <dir> <output> <width> <height> <duration> <srt>.
// CI does not ship the real CLI; STUDIO_RENDERER=hyperframes selects it.
type HyperFramesRenderer struct{ Bin string }

// Name is the renderer id.
func (HyperFramesRenderer) Name() string { return "hyperframes" }

// Version asks the binary, or reports that it is not installed.
func (h HyperFramesRenderer) Version(ctx context.Context) string {
	bin := h.bin()
	cmd, cancel := commandCtx(ctx, bin, "--version")
	defer cancel()

	out, err := cmd.CombinedOutput()

	if err != nil {
		return "hyperframes (not installed)"
	}

	line, _, _ := strings.Cut(string(out), "\n")

	return strings.TrimSpace(line)
}

// Render runs the HyperFrames command. The worker still checks the MP4.
func (h HyperFramesRenderer) Render(ctx context.Context, req RenderRequest) error {
	args := []string{
		req.Dir,
		req.PendingPath(),
		strconv.Itoa(req.Width),
		strconv.Itoa(req.Height),
		strconv.FormatFloat(req.Duration, 'f', 3, 64),
		captionName,
	}

	return runEncode(ctx, h.bin(), args, req)
}

func (h HyperFramesRenderer) bin() string {
	if h.Bin != "" {
		return h.Bin
	}

	return "hyperframes"
}

// RemotionRenderer shells out to a Remotion render command.
// The contract matches HyperFramesRenderer. It stays off unless
// STUDIO_RENDERER=remotion, because the company license is a separate decision.
type RemotionRenderer struct{ Bin string }

// Name is the renderer id.
func (RemotionRenderer) Name() string { return "remotion" }

// Version asks the binary, or reports that it is not installed.
func (r RemotionRenderer) Version(ctx context.Context) string {
	cmd, cancel := commandCtx(ctx, r.bin(), "--version")
	defer cancel()

	out, err := cmd.CombinedOutput()
	if err != nil {
		return "remotion (not installed)"
	}

	line, _, _ := strings.Cut(string(out), "\n")

	return strings.TrimSpace(line)
}

// Render runs the Remotion command.
func (r RemotionRenderer) Render(ctx context.Context, req RenderRequest) error {
	args := []string{
		req.Dir,
		req.PendingPath(),
		strconv.Itoa(req.Width),
		strconv.Itoa(req.Height),
		strconv.FormatFloat(req.Duration, 'f', 3, 64),
		captionName,
	}

	return runEncode(ctx, r.bin(), args, req)
}

func (r RemotionRenderer) bin() string {
	if r.Bin != "" {
		return r.Bin
	}

	return "remotion"
}

func runEncode(ctx context.Context, bin string, args []string, req RenderRequest) error {
	if err := os.WriteFile(req.Dir+"/"+argsName, []byte(strings.Join(append([]string{bin}, args...), "\n")), 0o644); err != nil {
		return err
	}

	cmd, cancel := commandCtx(ctx, bin, args...)
	defer cancel()
	cmd.Dir = req.Dir

	var stderr bytes.Buffer
	cmd.Stderr = &stderr

	if err := cmd.Run(); err != nil {
		msg := strings.TrimSpace(stderr.String())
		if msg == "" {
			msg = err.Error()
		}

		return fmt.Errorf("encoder failed: %s", truncate(msg, 400))
	}

	info, err := os.Stat(req.PendingPath())
	if err != nil {
		return fmt.Errorf("encoder wrote no file: %w", err)
	}

	if info.Size() == 0 {
		return fmt.Errorf("encoder wrote an empty file")
	}

	return nil
}

// FFmpegVersion is the first line of `ffmpeg -version`.
func FFmpegVersion(ctx context.Context) string {
	cmd, cancel := commandCtx(ctx, "ffmpeg", "-version")
	defer cancel()

	out, err := cmd.Output()
	if err != nil {
		return "unknown"
	}

	line, _, _ := strings.Cut(string(out), "\n")

	return strings.TrimSpace(line)
}

// Loudnorm writes a stereo 48 kHz WAV at about -14 LUFS and a true peak
// under -2 dBTP, leaving headroom for the AAC encoder.
func Loudnorm(ctx context.Context, inPath, outPath string) error {
	measured, err := measureLoudness(ctx, inPath)
	if err != nil {
		return err
	}

	filter := fmt.Sprintf(
		"loudnorm=I=-14:TP=-2.0:LRA=11:measured_I=%s:measured_TP=%s:measured_LRA=%s:measured_thresh=%s:offset=%s:linear=true",
		measured.InputI, measured.InputTP, measured.InputLRA, measured.InputThresh, measured.Offset,
	)

	return runFFmpeg(ctx, "-y", "-hide_banner", "-loglevel", "error",
		"-i", inPath, "-af", filter, "-ar", strconv.Itoa(sampleRate), "-ac", "2", "-c:a", "pcm_s16le", outPath)
}

type loudnessJSON struct {
	InputI      string `json:"input_i"`
	InputTP     string `json:"input_tp"`
	InputLRA    string `json:"input_lra"`
	InputThresh string `json:"input_thresh"`
	Offset      string `json:"target_offset"`
}

func measureLoudness(ctx context.Context, path string) (loudnessJSON, error) {
	cmd, cancel := commandCtx(ctx, "ffmpeg", "-hide_banner", "-i", path, "-af", "loudnorm=print_format=json", "-f", "null", "-")
	defer cancel()

	out, err := cmd.CombinedOutput()
	if err != nil && !bytes.Contains(out, []byte("input_i")) {
		return loudnessJSON{}, fmt.Errorf("loudness measure: %w", err)
	}

	raw := jsonObject(out)

	var measured loudnessJSON
	if err := json.Unmarshal(raw, &measured); err != nil {
		return loudnessJSON{}, fmt.Errorf("loudness measure: %w", err)
	}

	for _, value := range []string{measured.InputI, measured.InputTP, measured.InputLRA, measured.InputThresh, measured.Offset} {
		if _, err := strconv.ParseFloat(value, 64); err != nil {
			return loudnessJSON{}, fmt.Errorf("loudness measure: bad number %q", value)
		}
	}

	return measured, nil
}

// MeasureLoudness returns integrated LUFS and true peak in dBTP.
func MeasureLoudness(ctx context.Context, path string) (integrated, truePeak float64, err error) {
	measured, err := measureLoudness(ctx, path)
	if err != nil {
		return 0, 0, err
	}

	integrated, err = strconv.ParseFloat(measured.InputI, 64)
	if err != nil {
		return 0, 0, err
	}

	truePeak, err = strconv.ParseFloat(measured.InputTP, 64)

	return integrated, truePeak, err
}

// DecodeMono decodes path to 48 kHz mono float samples.
func DecodeMono(ctx context.Context, path string) ([]float64, error) {
	cmd, cancel := commandCtx(ctx, "ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", strconv.Itoa(sampleRate), "-f", "f32le", "pipe:1")
	defer cancel()

	out, err := cmd.Output()
	if err != nil {
		return nil, err
	}

	if len(out)%4 != 0 {
		return nil, fmt.Errorf("studio: odd pcm length")
	}

	samples := make([]float64, len(out)/4)

	for i := range samples {
		samples[i] = float64(bytesToFloat32(out[i*4 : i*4+4]))
	}

	return samples, nil
}

func jsonObject(out []byte) []byte {
	start := bytes.IndexByte(out, '{')
	end := bytes.LastIndexByte(out, '}')

	if start < 0 || end < start {
		return nil
	}

	return out[start : end+1]
}

func runFFmpeg(ctx context.Context, args ...string) error {
	cmd, cancel := commandCtx(ctx, "ffmpeg", args...)
	defer cancel()

	var stderr bytes.Buffer
	cmd.Stderr = &stderr

	if err := cmd.Run(); err != nil {
		return fmt.Errorf("ffmpeg: %s", truncate(strings.TrimSpace(stderr.String()), 400))
	}

	return nil
}

func truncate(s string, n int) string {
	if len(s) <= n {
		return s
	}

	return s[:n]
}
