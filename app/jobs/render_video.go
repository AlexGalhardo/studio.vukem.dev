package jobs

import (
	"context"
	"time"

	vukem "github.com/AlexGalhardo/vukem"
	"github.com/AlexGalhardo/vukem/queue"

	"github.com/AlexGalhardo/vukem-studio/app/studio"
)

// RenderVideo plans and renders one video job.
type RenderVideo struct {
	VideoID int64 `json:"video_id"`
}

// Kind implements queue.Job.
func (RenderVideo) Kind() string { return "render_video" }

// HandleRenderVideo returns the handler. Failures are stored on the job, so
// the handler returns only storage errors.
func HandleRenderVideo(app *vukem.App) func(context.Context, RenderVideo) error {
	return func(ctx context.Context, j RenderVideo) error {
		svc, err := Studio(app)
		if err != nil {
			return err
		}

		return svc.Run(ctx, j.VideoID)
	}
}

// Studio builds the video service from the app's configuration.
func Studio(app *vukem.App) (*studio.Service, error) {
	cfg, err := studio.LoadConfig(app.Source.Get)
	if err != nil {
		return nil, err
	}

	db, err := app.DB()
	if err != nil {
		return nil, err
	}

	return studio.NewService(db, cfg, app.Log, app.Now), nil
}

var renderOptions = []queue.Option{queue.Retries(2), queue.Backoff(queue.Constant(5 * time.Second)), queue.Timeout(15 * time.Minute)}
