# Tot Spot

Sign-ups, waitlist, and an iPad check-in kiosk for the Tot Spot preschool prep program.
A lightweight, self-hosted alternative to Brightwheel.

## What it does

- **Sign-up form** (`?view=signup`) — parents join the waitlist from a link/QR
- **Kiosk** (`?view=kiosk`) — big tap-to-check-in/out grid for the iPad, showing
  only the cohort that has class that day (Mon/Wed vs Tues/Thurs)
- **Family portal** (`?view=parent`) — parents enter a family code to see
  announcements and daily updates/photos for their child's cohort
- **Admin** (`?view=admin`, password-protected):
  - Waitlist → enroll/withdraw (enrolling assigns a family code)
  - Children → full profiles (parents, emergency contacts, allergies, cohort,
    photo consent, emergency medical) + attach a scan of the signed paper form
  - Today → attendance
  - Announcements → post/delete notices parents see
  - Daily Update → post a class note + photos (warns which kids have no
    social-media photo consent)

It runs in **demo mode** out of the box (saves to a local file + `data/uploads`),
so you can try it before setting up Airtable.

The Airtable schema (all profile fields + the Announcements and Daily Updates
tables) is created/maintained by **`_schema_build.py`** — re-runnable and safe;
it only adds what's missing (needs the token's `schema.bases:write` scope).

---

## 1. Run it locally (demo mode — no setup)

From this folder, in PowerShell:

```powershell
# one-time: install the requirements
pip install -r requirements.txt

# run it
streamlit run app.py
```

Your browser opens to the home page. Try the links:
- Add a couple of kids on **Sign-up**
- Go to **Admin** (password: `totspot`), open the **Waitlist** tab, click **Enroll**
- Open **Kiosk** and tap a name to check in / out

Demo data lives in `data/local_db.json` — delete that file to start fresh.

---

## 2. Switch to Airtable (the real database)

### a) Create the base
1. Go to https://airtable.com and create a base called **Tot Spot**.
2. Make a table named **`Kids`** with these fields (exact names matter):

   | Field name        | Type                                            |
   |-------------------|-------------------------------------------------|
   | Child Name        | Single line text (this is the primary field)    |
   | Birthdate         | Single line text                                |
   | Parent Name       | Single line text                                |
   | Parent Phone      | Single line text                                |
   | Parent Email      | Single line text                                |
   | Notes/Allergies   | Long text                                       |
   | Status            | Single select — options: Waitlist, Enrolled, Withdrawn |
   | Signup Date       | Single line text                                |

3. Make a second table named **`Check-Ins`** with these fields (names are
   case-sensitive — match them exactly):

   | Field name      | Type                              |
   |-----------------|-----------------------------------|
   | Child           | Link to another record → **Kids** |
   | Date            | Single line text                  |
   | Check-In Time   | Single line text                  |
   | Check-Out Time  | Single line text                  |

   > Note: `Notes/Allergies` in the Kids table must be a **plain Long text**
   > field — not Airtable's "AI text" (with a ✨ icon), which can't be written to.

### b) Get your keys
1. **Base id**: open the base, the URL looks like
   `https://airtable.com/appXXXXXXXXXXXXXX/...` — the `app...` part is your base id.
2. **Token**: https://airtable.com/create/tokens → create a personal access token with
   scopes `data.records:read` and `data.records:write`, and give it access to the Tot Spot base.
   It starts with `pat...`.

### c) Configure the app
Copy the example secrets file and fill it in:

```powershell
Copy-Item .streamlit\secrets.toml.example .streamlit\secrets.toml
notepad .streamlit\secrets.toml
```

Set `token`, `base_id`, your `timezone`, and a real `admin_password`.
Restart the app — the "Demo mode" banner disappears and you're live on Airtable.

---

## 3. Set up the iPad kiosk

1. On the iPad, open Safari to the kiosk URL (e.g. `http://<server>:8503/?view=kiosk`).
2. Tap the **Share** button → **Add to Home Screen**.
3. Launch it from the home screen — it opens full-screen with no address bar, like an app.
4. In Settings → Display, set Auto-Lock to a long interval (or "Never" while plugged in).

## Sharing the sign-up link
The sign-up page is `.../?view=signup`. Any free QR-code generator can turn that URL
into a QR code to print or post.
