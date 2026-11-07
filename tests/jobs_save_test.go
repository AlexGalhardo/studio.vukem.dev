package tests

import (
	"context"
	"testing"
	"time"

	"github.com/AlexGalhardo/vukem/orm"

	"github.com/AlexGalhardo/vukem-studio/app/jobs"
	"github.com/AlexGalhardo/vukem-studio/app/models"
	"github.com/AlexGalhardo/vukem-studio/app/studio"
)

// A publish pack saved after a requeue and claim must not restore the status
// and the attempt counter it read earlier.
func TestSavePackKeepsClaimState(t *testing.T) {
	_, db := limitsApp(t)
	ctx := context.Background()

	row := newJob(studio.StatusReady)
	row.Attempts = 1

	if err := orm.Create(ctx, db, &row); err != nil {
		t.Fatal(err)
	}

	if err := jobs.Requeue(ctx, db, row.ID, time.Now()); err != nil {
		t.Fatal(err)
	}

	if ok, err := jobs.Claim(ctx, db, row.ID, time.Now()); err != nil || !ok {
		t.Fatalf("claim: %v %v", ok, err)
	}

	if err := jobs.SavePack(ctx, db, row.ID, "youtube", "title", "", ""); err != nil {
		t.Fatal(err)
	}

	cur, err := orm.QueryOf[models.Job](db).Find(ctx, row.ID)
	if err != nil {
		t.Fatal(err)
	}

	if cur.Status != studio.StatusRendering || cur.Attempts != 2 || cur.PackTitle != "title" {
		t.Fatalf("status %q attempts %d pack %q", cur.Status, cur.Attempts, cur.PackTitle)
	}
}

func TestSaveRunKeepsPackAndAttempts(t *testing.T) {
	_, db := limitsApp(t)
	ctx := context.Background()

	row := newJob(studio.StatusRendering)
	row.Attempts = 3
	row.PackTitle = "keep"

	if err := orm.Create(ctx, db, &row); err != nil {
		t.Fatal(err)
	}

	if err := jobs.SaveRun(ctx, db, studio.State{ID: row.ID, Status: studio.StatusReady, Prompt: "p", ModelID: "m"}); err != nil {
		t.Fatal(err)
	}

	cur, err := orm.QueryOf[models.Job](db).Find(ctx, row.ID)
	if err != nil {
		t.Fatal(err)
	}

	if cur.Status != studio.StatusReady || cur.Attempts != 3 || cur.PackTitle != "keep" {
		t.Fatalf("status %q attempts %d pack %q", cur.Status, cur.Attempts, cur.PackTitle)
	}
}
