package jobs

import (
	"context"
	"path/filepath"
	"strconv"

	vukem "github.com/AlexGalhardo/vukem"
	"github.com/AlexGalhardo/vukem/orm"

	"github.com/AlexGalhardo/vukem-studio/app/models"
	"github.com/AlexGalhardo/vukem-studio/app/studio"
)

// Render is the queued render of one job. The payload is only the id;
// the row holds the prompt, and the file name is fixed so a retry cannot
// publish a second MP4.
type Render struct {
	JobID int64 `json:"job_id"`
}

// Kind names the handler. Keep it stable across deploys.
func (Render) Kind() string { return "studio.render" }

func handleRender(app *vukem.App) func(context.Context, Render) error {
	return func(ctx context.Context, job Render) error {
		db, err := app.DB()
		if err != nil {
			return err
		}

		row, err := orm.QueryOf[models.Job](db).Find(ctx, job.JobID)
		if err != nil {
			return err
		}

		claimed, err := Claim(ctx, db, row.ID, app.Now())
		if err != nil {
			return err
		}

		if !claimed {
			return nil
		}

		root := RootFor(app)
		voice := ""

		if row.Voice == studio.VoiceUpload {
			voice = filepath.Join(root, strconv.FormatInt(row.ID, 10), "upload.wav")
		}

		state := studio.State{
			ID:        row.ID,
			Brief:     briefOf(row),
			Prompt:    row.Prompt,
			ModelID:   row.ModelID,
			Status:    row.Status,
			VoiceFile: voice,
		}

		return studio.Run(ctx, state, studio.Runner{
			Root:     root,
			Planner:  PlannerFor(app),
			Renderer: RendererFor(app),
			Save: func(ctx context.Context, st studio.State) error {
				return SaveRun(ctx, db, st)
			},
		})
	}
}

func briefOf(row models.Job) studio.Brief {
	return studio.Brief{
		Goal:         row.Goal,
		Audience:     row.Audience,
		Subject:      row.Subject,
		Duration:     row.Duration,
		Ratio:        row.Ratio,
		StyleSkill:   row.StyleSkill,
		Language:     row.Language,
		Facts:        studio.SplitLines(row.Facts),
		Links:        row.Links,
		CallToAction: row.CallToAction,
		Voice:        row.Voice,
		MusicLicense: row.MusicLicense,
	}
}
