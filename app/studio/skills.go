package studio

import (
	"os"
	"path/filepath"
	"slices"
	"strings"
)

// Styles are the visual style ids from the skill catalog. A brief may name
// only one of these, and the directory must exist when the skill tree is on
// disk. Software-practice kits live under .agents/skills too and are not styles.
var Styles = []string{
	"airpainting",
	"blocos-de-montar",
	"colagem-explicativa",
	"colagem-parallax",
	"diorama-isometrico",
	"dossie-investigativo",
	"floresta-luminosa",
	"ilustracao-explicativa",
	"jelly",
	"laminas-de-especimes",
	"lowpoly-explicativo",
	"mapa-documental",
	"maquete-3d",
	"midia-mista",
	"palavra-em-recortes",
	"pelucia",
	"pintura-em-camadas",
	"pixel-art-hd2d",
	"texto-grifado",
	"traco-simples",
}

// ValidStyle reports whether id is a visual style the compiler may attach.
// When the skill tree is present, the directory has to exist. A deploy that
// ships the binary without the tree still accepts the catalog.
func ValidStyle(id string) bool {
	if !slices.Contains(Styles, id) {
		return false
	}

	root, err := SkillsRoot()
	if err != nil {
		return true
	}

	info, err := os.Stat(filepath.Join(root, id))

	return err == nil && info.IsDir()
}

// SkillsRoot finds .agents/skills by walking up from the working directory
// and from the executable. The Docker image and the tests do not share a cwd.
func SkillsRoot() (string, error) {
	var starts []string

	if wd, err := os.Getwd(); err == nil {
		starts = append(starts, wd)
	}

	if exe, err := os.Executable(); err == nil {
		starts = append(starts, filepath.Dir(exe))
	}

	for _, start := range starts {
		dir := start

		for {
			candidate := filepath.Join(dir, ".agents", "skills")
			info, err := os.Stat(candidate)

			if err == nil && info.IsDir() {
				return candidate, nil
			}

			parent := filepath.Dir(dir)
			if parent == dir {
				break
			}

			dir = parent
		}
	}

	return "", os.ErrNotExist
}

// skillAttachLimit keeps one prompt from carrying a whole kit.
const skillAttachLimit = 4000

// LoadSkill returns the visual law for id. An English SKILL.en.md wins when
// the kit has one. Otherwise the Portuguese SKILL.md is attached as the law.
// A missing tree falls back to a one-line law so a render can still be explained.
func LoadSkill(id string) string {
	root, err := SkillsRoot()
	if err != nil {
		return fallbackLaw(id)
	}

	var english, skill string

	_ = filepath.WalkDir(filepath.Join(root, id), func(path string, d os.DirEntry, err error) error {
		if err != nil || d.IsDir() {
			return nil
		}

		switch d.Name() {
		case "SKILL.en.md":
			if english == "" {
				english = path
			}
		case "SKILL.md":
			if strings.Contains(path, "video-"+id) {
				skill = path
			}
		}

		return nil
	})

	pick := english
	if pick == "" {
		pick = skill
	}

	if pick == "" {
		return fallbackLaw(id)
	}

	body, err := os.ReadFile(pick)
	if err != nil {
		return fallbackLaw(id)
	}

	text := strings.TrimSpace(string(body))
	if len(text) > skillAttachLimit {
		text = text[:skillAttachLimit] + "\n\n[skill file truncated]"
	}

	return text
}

func fallbackLaw(id string) string {
	if id == "traco-simples" {
		return "Flat cut-paper shapes. No outline, no shadow, no gradient. Draw at 12 fps."
	}

	return "Follow the visual system named by the skill id " + id + ". Do not invent a second palette."
}
