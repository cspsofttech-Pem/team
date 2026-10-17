# Team Tasks — setup & update guide

## Files and where they go

| File | Where |
|---|---|
| `app.py` | GitHub (main folder) |
| `storage.py` | GitHub (main folder) |
| `requirements.txt` | GitHub (main folder) |
| `.streamlit/config.toml` | GitHub, inside a folder named `.streamlit` (Add file → Create new file → type `.streamlit/config.toml`) |
| `supabase_setup.sql` | Supabase SQL Editor — **new installs only** (creates both tables) |
| `supabase_update_v2.sql` | Supabase SQL Editor — **if you already created the tasks table earlier** (adds the users table) |
| `secrets.toml.example` | NOT on GitHub with real values — copy its text into Streamlit Cloud → Settings → Secrets |
| `.gitignore`, `SETUP.md` | Optional |

## 1. Database (Supabase)
SQL Editor → New query → paste the right SQL file (see table above) → Run → "Success".
Project Settings → API Keys → copy the Project URL and the **secret** key (`sb_secret_...`).

## 2. Code (GitHub)
Repo → Add file → Upload files → `app.py`, `storage.py`, `requirements.txt` → Commit.
Then Add file → Create new file → name `.streamlit/config.toml` → paste its contents → Commit.

## 3. App (Streamlit Cloud)
share.streamlit.io → your app → ⋮ → Settings → Secrets. It should contain:

```toml
supabase_url = "https://YOUR-PROJECT-ID.supabase.co"
supabase_key = "YOUR-SECRET-KEY"
app_password = "team-password-for-registering"
admin_password = "strong-admin-password"
employees_see_only_own = false
timezone = "Asia/Kolkata"
```
Save. After any GitHub change the app updates itself in 1–2 minutes.

## 4. Phones
Send the app link + team password to employees.
- They open the link → **Register** tab → their name + a PIN + team password.
- Add to home screen: Android Chrome ⋮ → Add to Home screen · iPhone Safari Share → Add to Home Screen.
- You sign in on the **Admin** tab with the admin password.

## Good to know
- 🔔 Deadline sound plays while the app is open; if the phone blocks it, tap **"Tap to hear"**. iPhone silent switch must be off.
- High priority tasks show as a full red card. Card edges: red = due ≤ 1 day, blue = ≤ 4 days, green = later.
- Forgotten PIN: Admin → 👥 Employees → Reset PIN.
- Backup: Admin dashboard → Download as CSV, or Supabase → Table Editor → Export.
- Free plans sleep when unused for days: Streamlit shows a "wake up" button; Supabase may need **Restore** after ~1 week of no use.
