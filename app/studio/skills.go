package studio

import (
	"errors"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strings"
)

var skillID = regexp.MustCompile(`^[a-z0-9][a-z0-9-]{0,63}$`)

// Skill is a style kit under .agents/skills/<id>/SKILL.md.
type Skill struct {
	ID          string `json:"id"`
	Description string `json:"description"`
	// Body is the SKILL.md content the compiler attaches to the prompt.
	Body string `json:"-"`
}

// Skills is the catalog of style skills. A style skill is a directory named
// video-* that holds a SKILL.md, at most two levels below the skills root
// (the kits unpack as <kit>/video-<style>/SKILL.md).
type Skills struct {
	dir   string
	paths map[string]string
}

// ErrUnknownSkill is returned for an id that has no SKILL.md.
var ErrUnknownSkill = errors.New("studio: unknown skill")

// DefaultSkill is the style the FFmpeg text-card renderer can render for real.
const DefaultSkill = "video-text-cards"

// maxSkillBody caps how much of a SKILL.md goes into a prompt.
const maxSkillBody = 6000

// NewSkills indexes the skills directory: dir when set, else the nearest
// .agents/skills above the working directory (tests run from tests/).
func NewSkills(dir string) *Skills {
	if dir == "" {
		wd, _ := os.Getwd()

		for d := wd; d != "" && d != filepath.Dir(d); d = filepath.Dir(d) {
			if st, err := os.Stat(filepath.Join(d, ".agents", "skills")); err == nil && st.IsDir() {
				dir = filepath.Join(d, ".agents", "skills")

				break
			}
		}
	}

	s := &Skills{dir: dir, paths: map[string]string{}}

	kits, _ := os.ReadDir(dir)
	for _, kit := range kits {
		subs, _ := os.ReadDir(filepath.Join(dir, kit.Name()))
		for _, sub := range subs {
			id := sub.Name()
			if !sub.IsDir() || !strings.HasPrefix(id, "video-") || !skillID.MatchString(id) {
				continue
			}

			p := filepath.Join(dir, kit.Name(), id, "SKILL.md")
			if _, err := os.Stat(p); err != nil {
				continue
			}

			if _, dup := s.paths[id]; !dup {
				s.paths[id] = p
			}
		}
	}

	return s
}

// Get loads one skill. Only ids found by the index resolve, so a brief
// cannot name a path.
func (s *Skills) Get(id string) (Skill, error) {
	p, ok := s.paths[id]
	if !ok {
		return Skill{}, ErrUnknownSkill
	}

	b, err := os.ReadFile(p)
	if err != nil {
		return Skill{}, ErrUnknownSkill
	}

	body := string(b)

	return Skill{ID: id, Description: description(body), Body: body}, nil
}

// Has reports whether id is a known style skill.
func (s *Skills) Has(id string) bool { _, ok := s.paths[id]; return ok }

// List returns every skill, sorted by id.
func (s *Skills) List() []Skill {
	out := make([]Skill, 0, len(s.paths))

	for id := range s.paths {
		if sk, err := s.Get(id); err == nil {
			out = append(out, sk)
		}
	}

	sort.Slice(out, func(i, j int) bool { return out[i].ID < out[j].ID })

	return out
}

func description(body string) string {
	rest, ok := strings.CutPrefix(strings.ReplaceAll(body, "\r\n", "\n"), "---\n")
	if !ok {
		return ""
	}

	front, _, _ := strings.Cut(rest, "\n---")

	for _, line := range strings.Split(front, "\n") {
		if v, ok := strings.CutPrefix(line, "description:"); ok {
			return strings.Trim(strings.TrimSpace(v), `"'`)
		}
	}

	return ""
}
