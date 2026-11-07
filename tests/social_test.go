package tests

import (
	"testing"

	"github.com/AlexGalhardo/vukem/social"
	"github.com/AlexGalhardo/vukem/vukemtest"

	"github.com/AlexGalhardo/vukem-studio/bootstrap"
)

// testProvider is the social provider these tests drive: the first one
// vukem install:auth --social was given.
const testProvider = "google"

// signIn follows redirect → fake provider → callback.
func signIn(t *testing.T, c *vukemtest.Client) *vukemtest.Response {
	t.Helper()

	r := c.Get("/auth/" + testProvider + "/redirect")

	return c.Get(r.Header("Location"))
}

func TestSocialSignUpAndLogin(t *testing.T) {
	t.Parallel()

	user := social.User{ID: "gh-1", Email: "Lia@Example.com", EmailVerified: true, Name: "Lia"}
	app := vukemtest.New(t, bootstrap.New, vukemtest.Options{Env: vukemtest.FakeSocial(user)})

	c := app.Client(t)
	signIn(t, c).AssertRedirect("/dashboard")
	c.Get("/dashboard").AssertOK().AssertSee("Lia").AssertSee("verified")

	vukemtest.AssertDatabaseCount(t, app, "users", 1)
	vukemtest.AssertDatabaseHas(t, app, "social_accounts", map[string]any{
		"provider": testProvider, "provider_id": "gh-1",
	})

	// Signing in again reuses the link.
	signIn(t, app.Client(t)).AssertRedirect("/dashboard")
	vukemtest.AssertDatabaseCount(t, app, "users", 1)

	app.Client(t).Get("/auth/myspace/redirect").AssertNotFound()
}

// Someone signs up first with the victim's address and keeps a session,
// a remember-me token and an API token. When the victim signs in with a
// provider that verified the address, the account is linked and every one
// of those ways in ends, password included.
func TestSocialLinkEndsSquatterAccess(t *testing.T) {
	t.Parallel()

	victim := social.User{ID: "gh-9", Email: "vic@example.com", EmailVerified: true, Name: "Vic"}
	app := vukemtest.New(t, bootstrap.New, vukemtest.Options{Env: vukemtest.FakeSocial(victim)})

	seedUser(t, app, "vic@example.com", false)
	squatter := app.Client(t)
	actAs(t, app, squatter, "vic@example.com")

	userID := apiTokenFor(t, app, "vic@example.com")

	c := app.Client(t)
	signIn(t, c).AssertRedirect("/dashboard")
	c.Get("/dashboard").AssertOK()

	// Revoked, not deleted: the token stays listed with revoked_at.
	vukemtest.AssertDatabaseMissing(t, app, "access_tokens", map[string]any{"user_id": userID, "revoked_at": nil})
	vukemtest.AssertDatabaseHas(t, app, "access_tokens", map[string]any{"user_id": userID})
	squatter.Get("/dashboard").AssertRedirect("/login")
}

func TestSocialDoesNotTakeOverUnverifiedEmails(t *testing.T) {
	t.Parallel()

	user := social.User{ID: "gh-2", Email: "owner@example.com", EmailVerified: false, Name: "Mallory"}
	app := vukemtest.New(t, bootstrap.New, vukemtest.Options{Env: vukemtest.FakeSocial(user)})

	seedUser(t, app, "owner@example.com", true)
	signIn(t, app.Client(t)).AssertStatus(409)
	vukemtest.AssertDatabaseCount(t, app, "social_accounts", 0)
}
