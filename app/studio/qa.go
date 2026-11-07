package studio

import (
	"context"
	"encoding/binary"
	"encoding/json"
	"fmt"
	"io"
	"math"
	"os"
	"strconv"
	"strings"
)

// Check is one QA row stored in the sidecar.
type Check struct {
	Name   string `json:"name"`
	OK     bool   `json:"ok"`
	Detail string `json:"detail"`
}

// Report is the check report. OK is true only when every check passed.
type Report struct {
	OK     bool    `json:"ok"`
	Checks []Check `json:"checks"`
}

// QAInput is the file and the plan the worker compares it to.
type QAInput struct {
	Path     string
	Plan     Plan
	Brief    Brief
	Cues     []Cue
	HasVoice bool
	HasBed   bool
}

// CheckFile runs the QA page rules. A failed check leaves the job unready.
func CheckFile(ctx context.Context, in QAInput) (Report, error) {
	var checks []Check

	add := func(name string, ok bool, detail string) {
		checks = append(checks, Check{Name: name, OK: ok, Detail: detail})
	}

	info, err := os.Stat(in.Path)
	if err != nil || info.Size() == 0 {
		add("file", false, "the encoder wrote no file")

		return Report{Checks: checks}, nil
	}

	probe, err := Inspect(ctx, in.Path)
	if err != nil {
		add("ffprobe", false, err.Error())

		return Report{Checks: checks}, nil
	}

	video, audio := splitStreams(probe)
	if video == nil {
		add("video", false, "ffprobe found no video stream")
	} else {
		add("codec", video.CodecName == "h264", "codec "+video.CodecName)
		add("pix_fmt", video.PixFmt == "yuv420p", "pixel format "+video.PixFmt)
		add("frame", video.Width == in.Plan.Width && video.Height == in.Plan.Height,
			fmt.Sprintf("%dx%d", video.Width, video.Height))

		got, _ := strconv.ParseFloat(probe.Format.Duration, 64)
		if got == 0 {
			got, _ = strconv.ParseFloat(video.Duration, 64)
		}

		delta := math.Abs(got - in.Plan.Duration)
		add("duration", delta <= 0.5, fmt.Sprintf("%.3fs", got))
	}

	fast, err := FastStart(in.Path)
	if err != nil {
		add("faststart", false, err.Error())
	} else {
		add("faststart", fast, "moov atom before mdat")
	}

	if in.HasVoice {
		if audio == nil {
			add("audio", false, "the brief asked for a voice and the file has no audio stream")
		} else {
			rate, _ := strconv.Atoi(audio.SampleRate)
			add("audio", audio.CodecName == "aac" && rate == sampleRate && audio.Channels == 2,
				fmt.Sprintf("%s %s Hz %d ch", audio.CodecName, audio.SampleRate, audio.Channels))

			integrated, peak, err := MeasureLoudness(ctx, in.Path)
			if err != nil {
				add("loudness", false, err.Error())
			} else {
				ok := math.Abs(integrated-(-14)) <= 2 && peak <= -1.5
				add("loudness", ok, fmt.Sprintf("%.2f LUFS, %.2f dBTP", integrated, peak))
			}
		}
	} else if audio != nil {
		add("silent", false, "a silent cut must not have an audio stream")
	} else {
		add("silent", true, "no audio stream")
	}

	if len(in.Cues) > 0 {
		body, err := os.ReadFile(dirOf(in.Path) + "/" + captionName)
		if err != nil {
			add("captions", false, err.Error())
		} else {
			parsed, err := ParseSRT(string(body))
			if err != nil {
				add("captions", false, err.Error())
			} else if err := CaptionsMatch(parsed, in.Cues); err != nil {
				add("captions", false, err.Error())
			} else if parsed[len(parsed)-1].End >= in.Plan.Duration {
				add("captions", false, "the last cue does not end before the video")
			} else if !burnClaimed(dirOf(in.Path)) {
				add("captions", false, "the encoder was not given the caption file")
			} else {
				add("captions", true, fmt.Sprintf("%d cues", len(parsed)))
			}
		}
	}

	for _, fact := range in.Brief.Facts {
		if !strings.Contains(in.Plan.Script, fact) {
			add("fact", false, "missing from the script: "+fact)
		} else {
			add("fact", true, fact)
		}
	}

	report := Report{OK: true, Checks: checks}
	for _, check := range checks {
		if !check.OK {
			report.OK = false
			break
		}
	}

	return report, nil
}

func dirOf(path string) string {
	i := strings.LastIndex(path, "/")
	if i < 0 {
		return "."
	}

	return path[:i]
}

func burnClaimed(dir string) bool {
	body, err := os.ReadFile(dir + "/" + argsName)
	if err != nil {
		return false
	}

	return strings.Contains(string(body), captionName)
}

// MediaInfo is the ffprobe JSON we read.
type MediaInfo struct {
	Streams []Stream `json:"streams"`
	Format  struct {
		Duration string `json:"duration"`
	} `json:"format"`
}

// Stream is one elementary stream.
type Stream struct {
	CodecType  string `json:"codec_type"`
	CodecName  string `json:"codec_name"`
	Width      int    `json:"width"`
	Height     int    `json:"height"`
	PixFmt     string `json:"pix_fmt"`
	Duration   string `json:"duration"`
	SampleRate string `json:"sample_rate"`
	Channels   int    `json:"channels"`
}

// Inspect runs ffprobe and decodes the JSON.
func Inspect(ctx context.Context, path string) (MediaInfo, error) {
	cmd, cancel := commandCtx(ctx, "ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format", path)
	defer cancel()

	out, err := cmd.Output()
	if err != nil {
		return MediaInfo{}, fmt.Errorf("ffprobe: %w", err)
	}

	var probe MediaInfo
	if err := json.Unmarshal(out, &probe); err != nil {
		return MediaInfo{}, err
	}

	return probe, nil
}

func splitStreams(probe MediaInfo) (video, audio *Stream) {
	for i := range probe.Streams {
		switch probe.Streams[i].CodecType {
		case "video":
			if video == nil {
				video = &probe.Streams[i]
			}
		case "audio":
			if audio == nil {
				audio = &probe.Streams[i]
			}
		}
	}

	return video, audio
}

// FastStart reports whether the moov atom precedes mdat.
func FastStart(path string) (bool, error) {
	f, err := os.Open(path)
	if err != nil {
		return false, err
	}

	defer f.Close()

	var moov, mdat int64 = -1, -1
	var pos int64

	for {
		var hdr [8]byte
		if _, err := io.ReadFull(f, hdr[:]); err != nil {
			break
		}

		size := int64(binary.BigEndian.Uint32(hdr[0:4]))
		kind := string(hdr[4:8])
		header := int64(8)

		if size == 1 {
			var ext [8]byte
			if _, err := io.ReadFull(f, ext[:]); err != nil {
				return false, err
			}

			size = int64(binary.BigEndian.Uint64(ext[:]))
			header = 16
		}

		if size == 0 {
			break
		}

		if size < header {
			return false, fmt.Errorf("studio: bad mp4 atom %s", kind)
		}

		switch kind {
		case "moov":
			if moov < 0 {
				moov = pos
			}
		case "mdat":
			if mdat < 0 {
				mdat = pos
			}
		}

		pos += size
		if _, err := f.Seek(pos, io.SeekStart); err != nil {
			return false, err
		}

		if moov >= 0 && mdat >= 0 {
			return moov < mdat, nil
		}
	}

	if moov < 0 || mdat < 0 {
		return false, fmt.Errorf("studio: mp4 is missing moov or mdat")
	}

	return moov < mdat, nil
}

// MediaDuration is the container duration in seconds.
func MediaDuration(ctx context.Context, path string) (float64, error) {
	probe, err := Inspect(ctx, path)
	if err != nil {
		return 0, err
	}

	return strconv.ParseFloat(probe.Format.Duration, 64)
}
