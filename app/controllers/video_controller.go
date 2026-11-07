package controllers

import (
	"errors"
	"net/http"
	"os"
	"path/filepath"
	"strconv"

	"github.com/AlexGalhardo/vukem/errs"
	"github.com/AlexGalhardo/vukem/inertia"
	"github.com/AlexGalhardo/vukem/orm"
	"github.com/AlexGalhardo/vukem/queue"
	"github.com/AlexGalhardo/vukem/web"

	"github.com/AlexGalhardo/vukem-studio/app/jobs"
	"github.com/AlexGalhardo/vukem-studio/app/models"
	"github.com/AlexGalhardo/vukem-studio/app/requests"
	"github.com/AlexGalhardo/vukem-studio/app/studio"
)

// VideoController serves the video jobs of the signed-in user. Every query
// is scoped by user_id, so another user's job is a 404, not a 403.
type VideoController struct {
	svc   *studio.Service
	queue func() (*queue.Queue, error)
	user  func(*web.Ctx) (models.User, error)
}

// NewVideoController wires the controller.
func NewVideoController(svc *studio.Service, q func() (*queue.Queue, error), user func(*web.Ctx) (models.User, error)) *VideoController {
	return &VideoController{svc: svc, queue: q, user: user}
}

// Index lists the user's videos.
func (vc *VideoController) Index(c *web.Ctx) error {
	u, err := vc.user(c)
	if err != nil {
		return err
	}

	videos, err := orm.QueryOf[models.Video](vc.svc.DB).Where("user_id", u.ID).OrderBy("id", orm.Desc).Limit(100).Get(c.Context())
	if err != nil {
		return err
	}

	if c.WantsJSON() {
		return c.JSON(http.StatusOK, map[string]any{"data": videos})
	}

	return inertia.Render(c, "Videos/Index", inertia.Props{"videos": videos})
}

// Create shows the brief form.
func (vc *VideoController) Create(c *web.Ctx) error {
	return inertia.Render(c, "Videos/Create", inertia.Props{
		"skills":   vc.svc.Skills.List(),
		"models":   vc.svc.Cfg.Models,
		"ratios":   studio.Ratios,
		"defaults": map[string]any{"skill": studio.DefaultSkill, "model": studio.DefaultAnthropicModel, "ratio": "9:16", "duration": 30, "language": "English"},
		"limits":   map[string]int{"min": studio.MinDuration, "max": studio.MaxDuration},
	})
}

// Store validates the brief, stores the job with its compiled prompt and
// queues the render.
func (vc *VideoController) Store(c *web.Ctx) error {
	u, err := vc.user(c)
	if err != nil {
		return err
	}

	b, err := web.Parse(c, requests.VideoSchema)
	if err != nil {
		return err
	}

	v := errs.NewValidation()

	if !vc.svc.Skills.Has(b.Skill) {
		v.Append("skill", "Unknown style skill.")
	}

	if !vc.svc.Cfg.ModelAllowed(b.Model) {
		v.Append("model", "Unknown model.")
	}

	for field, msg := range b.CheckLists() {
		v.Append(field, msg)
	}

	if !v.Empty() {
		return v
	}

	video, err := vc.svc.Create(c.Context(), u.ID, b)
	if err != nil {
		if errors.Is(err, studio.ErrDailyLimit) {
			return errs.NewValidation().Add("form", err.Error())
		}

		return err
	}

	if err := vc.dispatch(c, video.ID, video.Attempts); err != nil {
		return err
	}

	if c.WantsJSON() {
		// A sync queue has already run the job; return its current state.
		if fresh, err := orm.QueryOf[models.Video](vc.svc.DB).Find(c.Context(), video.ID); err == nil {
			video = fresh
		}

		return c.Created("/videos/"+strconv.FormatInt(video.ID, 10), video)
	}

	inertia.Flash(c, "success", "Video queued.")

	return c.RedirectRoute("videos.show", "video", video.ID)
}

// Show displays one job with its prompt, plan and state.
func (vc *VideoController) Show(c *web.Ctx) error {
	video, err := vc.find(c)
	if err != nil {
		return err
	}

	if c.WantsJSON() {
		return c.JSON(http.StatusOK, video)
	}

	return inertia.Render(c, "Videos/Show", inertia.Props{"video": video, "ready": video.Status == models.VideoReady})
}

// Status is the polling endpoint: state only, no prompt or plan.
func (vc *VideoController) Status(c *web.Ctx) error {
	video, err := vc.find(c)
	if err != nil {
		return err
	}

	return c.JSON(http.StatusOK, map[string]any{
		"id": video.ID, "status": video.Status, "stage": video.Stage, "progress": video.Progress, "error": video.Error,
	})
}

// Retry re-queues a failed job.
func (vc *VideoController) Retry(c *web.Ctx) error {
	video, err := vc.find(c)
	if err != nil {
		return err
	}

	if err := vc.svc.Retry(c.Context(), &video); err != nil {
		if errors.Is(err, studio.ErrNotRetryable) || errors.Is(err, studio.ErrAttemptsLimit) {
			return errs.Wrap(http.StatusConflict, err)
		}

		return err
	}

	if err := vc.dispatch(c, video.ID, video.Attempts); err != nil {
		return err
	}

	if c.WantsJSON() {
		return c.JSON(http.StatusOK, video)
	}

	inertia.Flash(c, "success", "Video queued again.")

	return c.RedirectRoute("videos.show", "video", video.ID)
}

// Download streams the MP4 of a ready job.
func (vc *VideoController) Download(c *web.Ctx) error {
	video, err := vc.find(c)
	if err != nil {
		return err
	}

	if video.Status != models.VideoReady || video.OutputPath == "" {
		return errs.New(http.StatusConflict, "The video is not ready.")
	}

	dir, err := filepath.Abs(vc.svc.Cfg.OutputDir)
	if err != nil {
		return err
	}

	root, err := os.OpenRoot(dir)
	if err != nil {
		return err
	}

	defer func() { _ = root.Close() }()

	return c.Download(root.FS(), video.OutputPath, "video-"+strconv.FormatInt(video.ID, 10)+".mp4")
}

func (vc *VideoController) dispatch(c *web.Ctx, id int64, attempts int) error {
	q, err := vc.queue()
	if err != nil {
		return err
	}

	return q.Dispatch(c.Context(), jobs.RenderVideo{VideoID: id}, queue.Unique("render_video:"+strconv.FormatInt(id, 10)+":"+strconv.Itoa(attempts)))
}

func (vc *VideoController) find(c *web.Ctx) (models.Video, error) {
	u, err := vc.user(c)
	if err != nil {
		return models.Video{}, err
	}

	id, err := c.ParamInt("video")
	if err != nil {
		return models.Video{}, err
	}

	return orm.QueryOf[models.Video](vc.svc.DB).Where("user_id", u.ID).Find(c.Context(), id)
}
