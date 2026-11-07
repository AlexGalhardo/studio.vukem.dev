package tests

import (
	"net/http"
	"strings"
	"testing"

	"github.com/AlexGalhardo/vukem/social"
	"github.com/AlexGalhardo/vukem/vukemtest"

	"github.com/AlexGalhardo/vukem-studio/bootstrap"
)

func TestSignedInHomeIsDashboard(t *testing.T) {
	t.Parallel()

	app := vukemtest.New(t, bootstrap.New)
	c := app.Client(t)
	register(t, app, c, "home@example.com")

	c.Get("/").AssertOK().AssertInertia("Dashboard").PropEquals("auth.user.email", "home@example.com")
}

func TestLogoutReturnsToLogin(t *testing.T) {
	t.Parallel()

	app := vukemtest.New(t, bootstrap.New)
	c := app.Client(t)
	register(t, app, c, "out@example.com")

	c.PostJSON("/logout", nil).AssertRedirect("/login")
	c.Get("/").AssertRedirect("/login")
}

func TestSessionCookieFlags(t *testing.T) {
	t.Parallel()

	user := social.User{ID: "g-2", Email: "cookie@example.com", EmailVerified: true, Name: "Cook"}
	app := vukemtest.New(t, bootstrap.New, vukemtest.Options{Env: vukemtest.FakeSocial(user)})
	c := app.Client(t)

	res := signIn(t, c)
	res.AssertRedirect("/dashboard")

	var session *http.Cookie
	for _, ck := range res.Recorder().Result().Cookies() {
		if ck.Name == "vukem_session" || strings.HasPrefix(ck.Name, "__Host-") {
			session = ck
		}
	}

	// APP_ENV=test speaks plain HTTP, so Secure stays off. Production
	// session setup refuses a cookie that is not Secure.
	if session == nil || !session.HttpOnly || session.SameSite != http.SameSiteLaxMode || session.Secure {
		t.Fatalf("session cookie = %+v, want HttpOnly SameSite=Lax and not Secure", session)
	}
}

func TestGoogleSignInReachesHome(t *testing.T) {
	t.Parallel()

	user := social.User{ID: "g-1", Email: "gia@example.com", EmailVerified: true, Name: "Gia"}
	app := vukemtest.New(t, bootstrap.New, vukemtest.Options{Env: vukemtest.FakeSocial(user)})
	c := app.Client(t)

	signIn(t, c).AssertRedirect("/dashboard")
	c.Get("/").AssertOK().AssertSee("Gia").AssertInertia("Dashboard")
}
