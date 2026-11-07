package routes

import (
	"github.com/AlexGalhardo/vukem"
	"github.com/AlexGalhardo/vukem/auth"
	"github.com/AlexGalhardo/vukem/router"

	"github.com/AlexGalhardo/vukem-studio/app/accounts"
	"github.com/AlexGalhardo/vukem-studio/app/controllers"
	"github.com/AlexGalhardo/vukem-studio/app/jobs"
)

// Studio registers the video jobs. Every route needs a signed-in, verified user.
func Studio(r *router.Router, app *vukem.App) error {
	acc, err := accounts.New(app)
	if err != nil {
		return err
	}

	svc, err := jobs.Studio(app)
	if err != nil {
		return err
	}

	vc := controllers.NewVideoController(svc, app.Queue, acc.Web.User)
	guard := []router.Middleware{auth.Required(acc.Web), auth.Verified(acc.Web)}

	r.Get("/videos", vc.Index).Name("videos.index").Use(guard...)
	r.Get("/videos/create", vc.Create).Name("videos.create").Use(guard...)
	r.Post("/videos", vc.Store).Name("videos.store").Use(guard...)
	r.Get("/videos/{video}", vc.Show).Name("videos.show").Use(guard...)
	r.Get("/videos/{video}/status", vc.Status).Name("videos.status").Use(guard...)
	r.Get("/videos/{video}/download", vc.Download).Name("videos.download").Use(guard...)
	r.Post("/videos/{video}/retry", vc.Retry).Name("videos.retry").Use(guard...)

	return nil
}
