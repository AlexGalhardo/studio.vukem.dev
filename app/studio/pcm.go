package studio

import (
	"encoding/binary"
	"math"
)

func bytesToFloat32(b []byte) float32 {
	return math.Float32frombits(binary.LittleEndian.Uint32(b))
}
