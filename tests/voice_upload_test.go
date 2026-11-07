package tests

import (
	"context"
	"encoding/binary"
	"os"
	"path/filepath"
	"testing"

	"github.com/AlexGalhardo/vukem-studio/app/studio"
)

// lyingWAV declares declared data bytes at rate Hz but carries extra bytes more.
func lyingWAV(rate uint32, declared, extra int) []byte {
	h := make([]byte, 44)
	copy(h, "RIFF")
	binary.LittleEndian.PutUint32(h[4:], uint32(36+declared))
	copy(h[8:], "WAVEfmt ")
	binary.LittleEndian.PutUint32(h[16:], 16)
	binary.LittleEndian.PutUint16(h[20:], 1)
	binary.LittleEndian.PutUint16(h[22:], 1)
	binary.LittleEndian.PutUint32(h[24:], rate)
	binary.LittleEndian.PutUint32(h[28:], rate*2)
	binary.LittleEndian.PutUint16(h[32:], 2)
	binary.LittleEndian.PutUint16(h[34:], 16)
	copy(h[36:], "data")
	binary.LittleEndian.PutUint32(h[40:], uint32(declared))

	return append(h, make([]byte, extra)...)
}

func TestDecodeWAVHonorsDeclaredSize(t *testing.T) {
	path := filepath.Join(t.TempDir(), "upload.wav")
	if err := os.WriteFile(path, lyingWAV(8000, 1000, 5000), 0o644); err != nil {
		t.Fatal(err)
	}

	samples, _, err := studio.DecodeWAV(path)
	if err != nil {
		t.Fatal(err)
	}

	if len(samples) != 500 {
		t.Fatalf("decoded %d samples, the header declares 500", len(samples))
	}
}

// A header that declares 5 s at 1 Hz in a file with trailing bytes made the
// resampler ask for huge slices (fatal out-of-memory at 300 s). Only the
// declared samples may be used, so the voice stays 5 s and the run finishes.
func TestRunUsesOnlyDeclaredVoiceSamples(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "upload.wav")

	// 5 declared samples at 1 Hz (5 s), then 4000 more samples.
	if err := os.WriteFile(path, lyingWAV(1, 10, 8000), 0o644); err != nil {
		t.Fatal(err)
	}

	st := studio.State{ID: 1, VoiceFile: path, Brief: studio.Brief{
		Goal: "g", Audience: "a", Subject: "s", Duration: 5, Ratio: "9:16",
		StyleSkill: "traco-simples", Language: "en", Voice: studio.VoiceUpload,
	}}

	var saved studio.State

	run := studio.Runner{Root: dir, Save: func(_ context.Context, s studio.State) error { saved = s; return nil }}
	if err := studio.Run(context.Background(), st, run); err != nil {
		t.Fatal(err)
	}

	if saved.Status == studio.StatusRendering || saved.Status == "" {
		t.Fatalf("status %q: the run did not finish", saved.Status)
	}
}
