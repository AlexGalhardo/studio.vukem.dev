package studio

import (
	"encoding/binary"
	"fmt"
	"math"
	"os"
	"strings"
)

// Word is one aligned token on the voice track.
type Word struct {
	Text  string
	Start float64
	End   float64
}

// Synthesize builds a mono voice that fills duration. Each word is a tone
// burst separated by a short gap so an energy aligner can recover word times
// without a Whisper weight file.
func Synthesize(script string, durationSec float64, rate int) []float64 {
	words := strings.Fields(script)
	if len(words) == 0 {
		words = []string{"silence"}
	}

	total := int(math.Round(durationSec * float64(rate)))
	if total < len(words) {
		total = len(words)
	}

	gap := int(0.04 * float64(rate))
	if gap < 0 || gap*(len(words)-1) >= total/2 {
		gap = 0
	}

	usable := total - gap*(len(words)-1)
	lengths := distribute(usable, words)
	out := make([]float64, total)
	pos := 0

	for i, word := range words {
		n := lengths[i]
		freq := 180 + float64(len(word)%8)*20

		for s := 0; s < n && pos+s < len(out); s++ {
			t := float64(s) / float64(rate)
			env := 1.0
			attack := rate / 100

			if attack > 0 && s < attack {
				env = float64(s) / float64(attack)
			}

			out[pos+s] = env * 0.25 * math.Sin(2*math.Pi*freq*t)
		}

		pos += n
		if i != len(words)-1 {
			pos += gap
		}
	}

	return out
}

func distribute(total int, words []string) []int {
	lengths := make([]int, len(words))
	weights := make([]int, len(words))
	sum := 0

	for i, word := range words {
		weights[i] = len([]rune(word))
		if weights[i] < 1 {
			weights[i] = 1
		}

		sum += weights[i]
	}

	used := 0

	for i := range words {
		lengths[i] = total * weights[i] / sum
		if lengths[i] < 1 {
			lengths[i] = 1
		}

		used += lengths[i]
	}

	for used < total {
		lengths[len(lengths)-1]++
		used++
	}

	for used > total && lengths[len(lengths)-1] > 1 {
		lengths[len(lengths)-1]--
		used--
	}

	return lengths
}

// Mix adds a ducked 80 Hz bed when license is non-empty. An empty license
// returns the voice unchanged so the file cannot carry an unlicensed bed.
func Mix(voice []float64, rate int, license string) (mixed []float64, bed bool) {
	if strings.TrimSpace(license) == "" || len(voice) == 0 || rate <= 0 {
		return voice, false
	}

	out := make([]float64, len(voice))

	for i, sample := range voice {
		t := float64(i) / float64(rate)
		duck := 0.25

		if math.Abs(sample) < 0.02 {
			duck = 1
		}

		out[i] = sample + duck*0.05*math.Sin(2*math.Pi*80*t)
	}

	return out, true
}

// Goertzel returns the power of freq in samples. Tests use it to tell a
// licensed bed from a voice that must not contain one.
func Goertzel(samples []float64, rate int, freq float64) float64 {
	n := len(samples)
	if n == 0 || rate <= 0 || freq <= 0 {
		return 0
	}

	k := int(0.5 + float64(n)*freq/float64(rate))
	omega := 2 * math.Pi * float64(k) / float64(n)
	coeff := 2 * math.Cos(omega)

	var s0, s1, s2 float64

	for _, x := range samples {
		s0 = x + coeff*s1 - s2
		s2 = s1
		s1 = s0
	}

	return s1*s1 + s2*s2 - coeff*s1*s2
}

// AlignWords recovers one time range per word. It prefers bursts of energy
// (the local stand-in for Whisper). When the burst count does not match the
// script, it splits the duration in proportion to word length.
func AlignWords(samples []float64, rate int, script string, duration float64) ([]Word, string) {
	words := strings.Fields(script)
	if len(words) == 0 {
		return nil, ""
	}

	if bursts := energyBursts(samples, rate, duration); len(bursts) == len(words) {
		out := make([]Word, len(words))

		for i, word := range words {
			out[i] = Word{Text: word, Start: bursts[i][0], End: bursts[i][1]}
		}

		return clampWords(out, duration), "energy"
	}

	return clampWords(proportional(words, duration), duration), "proportional"
}

func energyBursts(samples []float64, rate int, duration float64) [][2]float64 {
	if rate <= 0 || len(samples) == 0 {
		return nil
	}

	window := rate / 50
	if window < 1 {
		window = 1
	}

	var rms []float64

	for i := 0; i < len(samples); i += window {
		end := i + window
		if end > len(samples) {
			end = len(samples)
		}

		var sum float64

		for _, s := range samples[i:end] {
			sum += s * s
		}

		rms = append(rms, math.Sqrt(sum/float64(end-i)))
	}

	var bursts [][2]float64

	open := false
	var start int

	for i, v := range rms {
		voiced := v > 0.02

		switch {
		case voiced && !open:
			open = true
			start = i
		case !voiced && open:
			open = false
			bursts = append(bursts, burstTimes(start, i, window, rate, duration))
		}
	}

	if open {
		bursts = append(bursts, burstTimes(start, len(rms), window, rate, duration))
	}

	return bursts
}

func burstTimes(start, end, window, rate int, duration float64) [2]float64 {
	a := float64(start*window) / float64(rate)
	b := float64(end*window) / float64(rate)

	if b > duration {
		b = duration
	}

	if b <= a {
		b = a + 0.05
	}

	return [2]float64{a, b}
}

func proportional(words []string, duration float64) []Word {
	weights := make([]int, len(words))
	sum := 0

	for i, word := range words {
		weights[i] = len([]rune(word))
		if weights[i] < 1 {
			weights[i] = 1
		}

		sum += weights[i]
	}

	out := make([]Word, len(words))
	cursor := 0.0

	for i, word := range words {
		span := duration * float64(weights[i]) / float64(sum)
		out[i] = Word{Text: word, Start: cursor, End: cursor + span}
		cursor += span
	}

	return out
}

func clampWords(words []Word, duration float64) []Word {
	limit := duration - 0.1
	if limit <= 0 {
		limit = duration
	}

	for i := range words {
		if words[i].Start < 0 {
			words[i].Start = 0
		}

		if words[i].End > limit {
			words[i].End = limit
		}

		if words[i].End <= words[i].Start {
			words[i].End = words[i].Start + 0.05
		}

		if words[i].End > limit {
			words[i].End = limit
		}
	}

	return words
}

// WriteWAV writes 16-bit mono PCM.
func WriteWAV(path string, samples []float64, rate int) error {
	f, err := os.Create(path)
	if err != nil {
		return err
	}

	defer f.Close()

	dataBytes := len(samples) * 2
	header := make([]byte, 44)
	copy(header[0:], "RIFF")
	binary.LittleEndian.PutUint32(header[4:], uint32(36+dataBytes))
	copy(header[8:], "WAVE")
	copy(header[12:], "fmt ")
	binary.LittleEndian.PutUint32(header[16:], 16)
	binary.LittleEndian.PutUint16(header[20:], 1)
	binary.LittleEndian.PutUint16(header[22:], 1)
	binary.LittleEndian.PutUint32(header[24:], uint32(rate))
	binary.LittleEndian.PutUint32(header[28:], uint32(rate*2))
	binary.LittleEndian.PutUint16(header[32:], 2)
	binary.LittleEndian.PutUint16(header[34:], 16)
	copy(header[36:], "data")
	binary.LittleEndian.PutUint32(header[40:], uint32(dataBytes))

	if _, err := f.Write(header); err != nil {
		return err
	}

	buf := make([]byte, 2)

	for _, sample := range samples {
		if sample > 1 {
			sample = 1
		}

		if sample < -1 {
			sample = -1
		}

		binary.LittleEndian.PutUint16(buf, uint16(int16(sample*32767)))

		if _, err := f.Write(buf); err != nil {
			return err
		}
	}

	return nil
}

// DecodeWAV reads 16-bit mono PCM written by WriteWAV. Other layouts return
// an error so the caller can fall back to ffmpeg.
func DecodeWAV(path string) (samples []float64, rate int, err error) {
	b, err := os.ReadFile(path)
	if err != nil {
		return nil, 0, err
	}

	if len(b) < 44 || string(b[0:4]) != "RIFF" || string(b[8:12]) != "WAVE" {
		return nil, 0, fmt.Errorf("studio: %s is not a PCM wav", path)
	}

	rate = int(binary.LittleEndian.Uint32(b[24:28]))
	channels := int(binary.LittleEndian.Uint16(b[22:24]))
	bits := int(binary.LittleEndian.Uint16(b[34:36]))

	if channels != 1 || bits != 16 || rate <= 0 {
		return nil, 0, fmt.Errorf("studio: %s is not 16-bit mono", path)
	}

	data := b[44:]
	samples = make([]float64, len(data)/2)

	for i := range samples {
		samples[i] = float64(int16(binary.LittleEndian.Uint16(data[i*2:]))) / 32767
	}

	return samples, rate, nil
}
