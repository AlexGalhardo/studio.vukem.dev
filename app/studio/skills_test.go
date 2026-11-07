package studio

import "testing"

func TestSkillsCatalog(t *testing.T) {
	s := NewSkills("")

	if !s.Has(DefaultSkill) {
		t.Fatalf("default skill %q missing from the catalog", DefaultSkill)
	}

	if s.Has("../etc/passwd") || s.Has("nope") || s.Has("") {
		t.Fatal("unknown ids must not resolve")
	}

	sk, err := s.Get(DefaultSkill)
	if err != nil || sk.Description == "" {
		t.Fatalf("Get default = %+v, %v", sk, err)
	}

	if len(s.List()) < 10 {
		t.Fatalf("expected the kits to be indexed, got %d", len(s.List()))
	}
}
