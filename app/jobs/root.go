package jobs

import "os"

func mkdirTemp() (string, error) {
	return os.MkdirTemp("", "studio-renders-")
}
