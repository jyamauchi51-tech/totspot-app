# The Tot Spot — Project Handoff / Continuity Doc

This is everything needed to keep working on the project from a new machine or a
new Claude session. **The app, website, and data do NOT live inside Claude** —
they live in your own accounts and on disk. Claude only needs this doc + the code
to pick up where we left off.

---

## 1. Live URLs
- **App (Streamlit):** https://the-tot-spot.streamlit.app
- **Public website (Netlify):** https://tubular-sawine-ac3d51.netlify.app
- **App code (GitHub):** https://github.com/jyamauchi51-tech/totspot-app
- **Streamlit dashboard:** https://share.streamlit.io  (Reboot app here: ⋮ → Reboot)
- **Netlify dashboard:** https://app.netlify.com/sites/tubular-sawine-ac3d51
- **Airtable base id:** `appkg0DAfs2do7UF2`

## 2. ⚠️ Accounts — VERIFY THESE ARE ON A PERSONAL EMAIL
If any of these were created with your **work/Cox email**, change the account's
email to a **personal** one BEFORE the merger, or you could lose access:
- GitHub: `jyamauchi51-tech`
- Streamlit Community Cloud (you sign in via GitHub)
- Netlify
- Airtable
- Gmail: `contactthetotspot@gmail.com` (used for app email + parent contact)

Your **Claude** account going away does NOT affect any of the above.

## 3. Where the files are (all included in the backup zip)
- **App code:** `C:\Users\b57280\totspot\` (working copy) and
  `C:\Users\b57280\totspot-deploy\` (clean copy that gets pushed to GitHub)
- **Website:** `C:\Users\b57280\totspot-site\`
- **Claude project memory/context:**
  `C:\Users\b57280\.claude\projects\C--Users-b57280\memory\`

## 4. Architecture (quick map)
- `app.py` — all UI + routing (?view=kiosk / signup / parent / admin / reset / home)
- `store.py` — data layer: `AirtableStore` (live) + `LocalStore` (demo). Field/table names live here.
- `notify.py` — email sending + QR code
- `_schema_build.py` — creates/updates Airtable fields & tables (idempotent; re-runnable)
- `requirements.txt` — Python deps
- Runs on **Streamlit Community Cloud** from the GitHub repo. **Main file path is
  `totspot-deploy/app.py`.** Working dir = repo root (app.py loads the logo via
  `__file__`, and PWA icons come from the Netlify site to avoid Streamlit's auth bounce).
- **Airtable tables:** Kids, Check-Ins, Announcements, Daily Updates, Daily Logs, Album.

## 5. Secrets (NOT in GitHub — do not commit them)
Secrets live in two places:
1. **Streamlit Cloud → your app → Settings → Secrets** (this is what the live app uses)
2. Locally in `totspot\.streamlit\secrets.toml` (included in the backup zip)

They include: Airtable personal access token, Gmail app password, admin password,
contact info, handbook URL, timezone. **If this handoff ever leaves your control,
regenerate the Airtable token (airtable.com/create/tokens) and the Gmail app
password (myaccount.google.com/apppasswords).**

## 6. Features built
Waitlist sign-up (2-parent option, gender, school year, emails Megan on new sign-up);
cohort-aware 6-digit PIN check-in kiosk; family portal with 2-factor login
(email+password, then 6-digit code), self-registration by child code, forgot-password
email reset; per-child daily reports (potty/snack/mood/injury); announcements +
class daily photo updates; printable scrapbook; Student ID card; child photo upload
with face-crop; full profiles; admin management; PWA (installable); pastel-rainbow
theme + pill tabs.

## 7. How to deploy changes
- **App:** edit files, then put the changed files into the GitHub repo under
  `totspot-deploy/` (and `requirements.txt` in BOTH `totspot-deploy/` and repo root
  if deps change). Then Streamlit dashboard → ⋮ → **Reboot app**.
  - You can upload via GitHub's website ("Add file → Upload files"), or push via git,
    or (what we used) the GitHub Contents API with a fine-grained token that has
    Contents: read/write.
- **Website:** drag the `totspot-site` folder onto the Netlify site's **Deploys** page.

## 8. To continue in a NEW Claude session (different account/machine)
1. Copy the backup zip to the new machine and unzip it.
2. Open Claude Code (or Claude) in the project folder.
3. Say: *"Read HANDOFF.md and the files in the memory folder — this is my in-progress
   Tot Spot app (Streamlit + Airtable). Continue from here."*
4. Put the secrets back (`.streamlit/secrets.toml`) if running locally, and make sure
   the new machine has Python + `pip install -r requirements.txt`.

That's it — a fresh Claude session + this doc + the code = full continuity.
