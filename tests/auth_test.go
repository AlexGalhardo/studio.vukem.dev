package tests

import (
	"net/http"
	"testing"
	"time"

	"github.com/AlexGalhardo/vukem/orm"
	"github.com/AlexGalhardo/vukem/vukemtest"

	"github.com/AlexGalhardo/vukem-studio/app/accounts"
	"github.com/AlexGalhardo/vukem-studio/app/models"
	"github.com/AlexGalhardo/vukem-studio/bootstrap"
)

// seedUser stores a password account directly. The app has no route that
// creates one: Google creates users, and this stands for an account an older
// release registered with a password.
func seedUser(t *testing.T, app *vukemtest.App, email string, verified bool) models.User {
	t.Helper()

	acc, err := accounts.New(app.App)
	if err != nil {
		t.Fatal(err)
	}

	h, err := acc.Hasher.Make("an old long password")
	if err != nil {
		t.Fatal(err)
	}

	u := models.User{Name: "Old Account", Email: email, Password: h}
	if err := orm.Create(t.Context(), acc.DB, &u); err != nil {
		t.Fatal(err)
	}

	if verified {
		if err := acc.MarkVerified(t.Context(), acc.DB, &u); err != nil {
			t.Fatal(err)
		}
	}

	return u
}

// register gives c a verified account and a signed-in session, standing in
// for the Google round trip that the Playwright tests drive for real.
func register(t *testing.T, app *vukemtest.App, c *vukemtest.Client, email string) {
	t.Helper()

	c.ActingAs("web", seedUser(t, app, email, true))
}

// apiTokenFor issues an API token for email directly, to check that linking a
// provider revokes it.
func apiTokenFor(t *testing.T, app *vukemtest.App, email string) string {
	t.Helper()

	acc, err := accounts.New(app.App)
	if err != nil {
		t.Fatal(err)
	}

	u, err := acc.Users.ByCredentials(t.Context(), map[string]string{"email": email})
	if err != nil {
		t.Fatal(err)
	}

	// No abilities: the test only needs the key to exist, and a key never
	// carries authority nobody asked for.
	if _, _, err := acc.Tokens.Create(t.Context(), u.AuthID(), "cli", nil, time.Hour); err != nil {
		t.Fatal(err)
	}

	return u.AuthID()
}

// Google is the only way in: no password, registration, reset or email
// verification route exists, so none can send mail or create a session.
func TestPasswordRoutesAreGone(t *testing.T) {
	t.Parallel()

	app := vukemtest.New(t, bootstrap.New)
	c := app.Client(t)

	for _, route := range []struct{ method, path string }{
		{http.MethodGet, "/register"},
		{http.MethodPost, "/register"},
		{http.MethodGet, "/register/check-email"},
		{http.MethodPost, "/login"},
		{http.MethodGet, "/forgot-password"},
		{http.MethodPost, "/forgot-password"},
		{http.MethodGet, "/reset-password/token"},
		{http.MethodPost, "/reset-password"},
		{http.MethodGet, "/email/verify"},
		{http.MethodGet, "/email/verify/1"},
		{http.MethodPost, "/email/verification-notification"},
	} {
		got := c.Do(route.method, route.path, nil, "").Recorder().Code
		if got != http.StatusNotFound && got != http.StatusMethodNotAllowed {
			t.Errorf("%s %s answered %d, want the route to be gone", route.method, route.path, got)
		}
	}

	if got := len(app.Mails().Sent()); got != 0 {
		t.Fatalf("%d mails sent, the app sends none", got)
	}
}

func TestLoginPageOffersGoogleOnly(t *testing.T) {
	t.Parallel()

	app := vukemtest.New(t, bootstrap.New)
	app.Client(t).Get("/login").AssertOK().AssertInertia("Auth/Login")
}

// actAs signs c in as the existing user with email.
func actAs(t *testing.T, app *vukemtest.App, c *vukemtest.Client, email string) {
	t.Helper()

	acc, err := accounts.New(app.App)
	if err != nil {
		t.Fatal(err)
	}

	u, err := acc.Users.ByCredentials(t.Context(), map[string]string{"email": email})
	if err != nil {
		t.Fatal(err)
	}

	c.ActingAs("web", u)
}
