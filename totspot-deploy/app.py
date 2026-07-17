"""The Tot Spot — waitlist sign-up, PIN check-in kiosk, admin management, and a
family portal where parents view announcements and edit their child's profile.

Views chosen by the ?view= URL parameter:
  ?view=kiosk   -> iPad check-in (4-digit PIN pad)
  ?view=signup  -> public waitlist sign-up
  ?view=admin   -> password-protected management
  ?view=parent  -> family portal (enter 4-digit code)
  (no param)    -> home page with links
"""

from datetime import datetime
from pathlib import Path

import streamlit as st

import notify
import store as S

st.set_page_config(page_title="The Tot Spot", page_icon="🐛", layout="wide")

LOGO_PATH = Path("assets/logo.png")
COHORT_OPTIONS = ["Mon/Wed", "Tues/Thurs", "Full-Time"]


# ------------------------------------------------------------------ config
def load_secrets() -> dict:
    try:
        return dict(st.secrets)
    except Exception:
        return {}


SECRETS = load_secrets()
TZ = SECRETS.get("timezone", "America/Phoenix")
EMAIL_CFG = SECRETS.get("email", {})
CONTACT = SECRETS.get("contact", {})           # name, phone, email, address
HANDBOOK_URL = SECRETS.get("handbook_url", "")

if "store_bundle" not in st.session_state:
    st.session_state.store_bundle = S.get_store(SECRETS)
store, IS_LIVE = st.session_state.store_bundle


# ------------------------------------------------------------------ styling
COLORS = {
    "coral": "#F4978E", "orange": "#F6B26B", "yellow": "#FCE38A",
    "green": "#A8DB8F", "green_deep": "#5FAE4B", "teal": "#9FE0DF",
    "lavender": "#C9A7E9", "ink": "#2B2B2B", "muted": "#8A94A6",
    "card": "#FFFFFF", "line": "#ECEFF4",
    "coral_bg": "#FDEBE8", "teal_bg": "#E7F7F6", "lavender_bg": "#F2EAFB",
    "green_bg": "#EBF6E3", "yellow_bg": "#FEF7DA",
}

GLOBAL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Baloo+2:wght@500;600;700;800&family=Nunito:wght@400;600;700;800&display=swap');

html, body, [class*="css"], .stApp, button, input, textarea, select {
    font-family: 'Nunito', -apple-system, sans-serif;
}
h1, h2, h3 { font-family: 'Baloo 2', 'Nunito', cursive; color: __INK__; }

header[data-testid="stHeader"] { background: transparent; }
#MainMenu, footer, [data-testid="stToolbar"] { visibility: hidden; }
.block-container { padding-top: 2.2rem; padding-bottom: 3rem; max-width: 1120px; }
.stApp { background: __CARD__; }

.subtitle { text-align: center; color: __MUTED__; font-size: 1.15rem; margin: -.2rem 0 1.2rem; font-weight: 600; }
.brand { font-family: 'Baloo 2'; font-weight: 800; font-size: 2.6rem; text-align: center; }
.codechip { display:inline-block; background:__lavender_bg__; color:__ink__; font-family:'Baloo 2';
    font-weight:800; letter-spacing:.2em; font-size:1.3rem; padding:.2rem .8rem; border-radius:.6rem; }
.pindots { text-align:center; font-size:2.6rem; letter-spacing:.4em; color:__ink__; margin:.4rem 0 1rem; }

div[data-testid="stButton"] > button, div[data-testid="stFormSubmitButton"] > button {
    border-radius: .9rem; font-weight: 700; font-family: 'Baloo 2';
}

.home-grid { display: flex; gap: 1.2rem; flex-wrap: wrap; justify-content: center; margin-top: 1.4rem; }
.home-card {
    flex: 1 1 240px; max-width: 300px; text-decoration: none; color: __INK__;
    border-radius: 1.6rem; padding: 2.1rem 1.4rem 1.7rem; text-align: center;
    font-family: 'Baloo 2'; font-weight: 700; font-size: 1.45rem;
    box-shadow: 0 5px 16px rgba(0,0,0,.07); border: 3px solid rgba(0,0,0,.04);
    transition: transform .09s ease;
}
.home-card:hover { transform: translateY(-5px); }
.home-card .emoji { font-size: 2.7rem; display: block; margin-bottom: .5rem; }
.home-card .sub { display: block; font-family: 'Nunito'; font-weight: 600; font-size: .95rem; color: __MUTED__; margin-top: .35rem; }
.c-green { background: __GREEN_BG__; } .c-coral { background: __CORAL_BG__; }
.c-lav { background: __LAVENDER_BG__; } .c-teal { background: __TEAL_BG__; }

div[class*="st-key-kp_"] button {
    height: 4.6rem; font-size: 1.7rem; border-radius: 1rem; font-family:'Baloo 2';
    border: 2px solid __LINE__;
}
.bigcard { border:3px solid __LINE__; border-radius:1.6rem; padding:1.5rem; text-align:center;
    box-shadow:0 4px 14px rgba(0,0,0,.06); }

div[data-testid="stMetric"] { background: __CARD__; border: 2px solid __LINE__; border-radius: 1.2rem; padding: .8rem 1rem; }

.post { border: 2px solid __LINE__; border-radius: 1.1rem; padding: 1rem 1.2rem; margin-bottom: 1rem; background: __CARD__; }
.post .when { color: __MUTED__; font-weight: 700; font-size: .9rem; }
.post .head { font-family:'Baloo 2'; font-weight: 800; font-size: 1.25rem; margin: .1rem 0 .3rem; }
.contactbox { background:__teal_bg__; border-radius:1.1rem; padding:1rem 1.2rem; }
</style>
"""


def css() -> str:
    s = GLOBAL_CSS
    for k, v in COLORS.items():
        s = s.replace(f"__{k.upper()}__", v).replace(f"__{k}__", v)
    return s


def logo_header():
    cols = st.columns([1, 3, 1])
    with cols[1]:
        if LOGO_PATH.exists():
            st.image(str(LOGO_PATH), width="stretch")
        else:
            st.markdown("<div class='brand'>🐛 The Tot Spot</div>", unsafe_allow_html=True)


def banner():
    if not IS_LIVE:
        st.info("🧪 Demo mode — saving to a local file, not Airtable.", icon="🧪")


def cohorts_meeting_today(now) -> list[str]:
    wd = now.weekday()
    if wd in (0, 2):
        return ["Mon/Wed", "Full-Time"]
    if wd in (1, 3):
        return ["Tues/Thurs", "Full-Time"]
    return []


def _idx(options: list[str], value: str) -> int:
    return options.index(value) if value in options else 0


def compute_age(birthdate: str, now) -> str:
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%m-%d-%Y", "%m/%d/%y"):
        try:
            bd = datetime.strptime((birthdate or "").strip(), fmt)
            break
        except ValueError:
            bd = None
    if not bd:
        return ""
    months = (now.year - bd.year) * 12 + (now.month - bd.month) - (1 if now.day < bd.day else 0)
    years, rem = divmod(max(months, 0), 12)
    if years <= 0:
        return f"{rem} months"
    return f"{years} yr {rem} mo" if rem else f"{years} years"


def enrolled_by_pin(pin: str) -> list[dict]:
    pin = (pin or "").strip()
    return [k for k in store.list_kids()
            if k["status"] == "Enrolled" and (k.get("pin") or "").strip() == pin]


def assign_pin(kid_id: str):
    existing = {(k.get("pin") or "") for k in store.list_kids()}
    store.update_kid(kid_id, {"pin": S.new_pin(existing)})


# ------------------------------------------------------------------ KIOSK (PIN)
def view_kiosk():
    st.markdown(css(), unsafe_allow_html=True)
    logo_header()
    now = S.now_local(TZ)
    st.markdown(f"<div class='subtitle'>Check-in &middot; {now.strftime('%A, %B ')}{now.day}</div>",
                unsafe_allow_html=True)
    banner()

    if flash := st.session_state.pop("kflash", ""):
        st.success(flash)

    pin = st.session_state.setdefault("kpin", "")

    if len(pin) == 4:
        matches = enrolled_by_pin(pin)
        cols = st.columns([1, 2, 1])
        with cols[1]:
            if not matches:
                st.error(f"No child found for code {pin}.")
            else:
                date_iso = S.today_iso(TZ)
                todays = {c["kid_id"]: c for c in store.list_checkins_for_date(date_iso)}
                for kid in matches:
                    rec = todays.get(kid["id"])
                    inside = rec is not None and not rec.get("check_out")
                    st.markdown(f"<div class='bigcard'><h2>{kid['name']}</h2>"
                                + (f"<div style='color:{COLORS['green_deep']};font-weight:700'>🟢 In since {rec['check_in']}</div>"
                                   if inside else "<div style='color:#8A94A6;font-weight:700'>Not checked in</div>")
                                + "</div>", unsafe_allow_html=True)
                    label = "Check OUT 👋" if inside else "Check IN ✅"
                    if st.button(label, key=f"do_{kid['id']}", type="primary", width="stretch"):
                        if inside:
                            store.set_checkout(rec["id"], S.time_str(TZ))
                            st.session_state.kflash = f"{kid['name']} checked out at {S.time_str(TZ)}. See you! 👋"
                        else:
                            store.add_checkin(kid["id"], date_iso, S.time_str(TZ))
                            st.session_state.kflash = f"{kid['name']} checked in at {S.time_str(TZ)}! 🌈"
                        st.session_state.kpin = ""
                        st.rerun()
            if st.button("Start over", width="stretch"):
                st.session_state.kpin = ""
                st.rerun()
        return

    # keypad
    cols = st.columns([1, 2, 1])
    with cols[1]:
        dots = "".join("●" if i < len(pin) else "○" for i in range(4))
        st.markdown(f"<div class='pindots'>{dots}</div>", unsafe_allow_html=True)
        st.markdown("<div class='subtitle'>Enter your 4-digit family code</div>", unsafe_allow_html=True)

        def press(d):
            if len(st.session_state.kpin) < 4:
                st.session_state.kpin += d
                st.rerun()

        for row in (["1", "2", "3"], ["4", "5", "6"], ["7", "8", "9"]):
            rc = st.columns(3)
            for i, d in enumerate(row):
                if rc[i].button(d, key=f"kp_{d}", width="stretch"):
                    press(d)
        rc = st.columns(3)
        if rc[0].button("Clear", key="kp_clear", width="stretch"):
            st.session_state.kpin = ""
            st.rerun()
        if rc[1].button("0", key="kp_0", width="stretch"):
            press("0")
        if rc[2].button("⌫", key="kp_back", width="stretch"):
            st.session_state.kpin = st.session_state.kpin[:-1]
            st.rerun()


# ------------------------------------------------------------------ SIGN-UP
def view_signup():
    st.markdown(css(), unsafe_allow_html=True)
    logo_header()
    st.markdown("<div class='subtitle'>Join our waitlist — we'll reach out when a spot opens up! 🌈</div>",
                unsafe_allow_html=True)
    banner()
    cols = st.columns([1, 3, 1])
    with cols[1]:
        with st.form("signup", clear_on_submit=True, border=True):
            child = st.text_input("Child's name *")
            birthdate = st.text_input("Child's birthdate (MM/DD/YYYY)")
            parent = st.text_input("Parent / guardian name *")
            c1, c2 = st.columns(2)
            phone = c1.text_input("Phone *")
            email = c2.text_input("Email")
            cohort = st.selectbox("Preferred cohort", ["No preference"] + COHORT_OPTIONS)
            notes = st.text_area("Allergies / anything we should know?")
            submitted = st.form_submit_button("Join the waitlist  🎉", width="stretch", type="primary")
        if submitted:
            if not child or not parent or not phone:
                st.error("Please fill in the required fields (*).")
                return
            store.add_kid({
                "name": child.strip(), "birthdate": birthdate.strip(),
                "parent_name": parent.strip(), "phone": phone.strip(),
                "email": email.strip(), "notes": notes.strip(),
                "cohort": "" if cohort == "No preference" else cohort,
                "status": "Waitlist", "signup_date": S.today_iso(TZ),
            })
            st.success(f"Thanks! **{child}** has been added to the waitlist. 🎉")
            st.balloons()


# ------------------------------------------------------------------ ADMIN
def check_password() -> bool:
    admin_pw = SECRETS.get("admin_password", "totspot")
    if st.session_state.get("admin_ok"):
        return True
    cols = st.columns([1, 2, 1])
    with cols[1]:
        pw = st.text_input("Admin password", type="password")
        if pw:
            if pw == admin_pw:
                st.session_state.admin_ok = True
                st.rerun()
            else:
                st.error("Wrong password.")
    return False


def profile_fields(k: dict, prefix: str) -> dict:
    """Render the shared profile inputs; return the collected values.
    Used by both the admin editor and the parent portal."""
    now = S.now_local(TZ)
    c1, c2 = st.columns(2)
    birthdate = c1.text_input("Birthday (MM/DD/YYYY)", k["birthdate"], key=f"{prefix}bd")
    c2.text_input("Age", compute_age(birthdate, now) or "—", disabled=True, key=f"{prefix}age")
    address = st.text_input("Address", k["address"], key=f"{prefix}ad")
    c3, c4 = st.columns(2)
    mother = c3.text_input("Mother name", k["mother_name"], key=f"{prefix}mn")
    mother_ph = c4.text_input("Mother phone", k["mother_phone"], key=f"{prefix}mp")
    c5, c6 = st.columns(2)
    father = c5.text_input("Father name", k["father_name"], key=f"{prefix}fn")
    father_ph = c6.text_input("Father phone", k["father_phone"], key=f"{prefix}fp")
    email = st.text_input("Email", k["email"], key=f"{prefix}em")
    c7, c8 = st.columns(2)
    e1 = c7.text_input("Emergency contact 1", k["emergency1"], key=f"{prefix}e1")
    e1p = c8.text_input("Phone", k["emergency1_phone"], key=f"{prefix}e1p")
    c9, c10 = st.columns(2)
    e2 = c9.text_input("Emergency contact 2", k["emergency2"], key=f"{prefix}e2")
    e2p = c10.text_input("Phone", k["emergency2_phone"], key=f"{prefix}e2p")
    pickups = st.text_area("People allowed to pick up (one per line)", k["authorized_pickups"], key=f"{prefix}pu")
    allergies = st.text_area("Allergies", k["notes"], key=f"{prefix}al")
    medications = st.text_area("Medications", k["medications"], key=f"{prefix}md")
    c11, c12 = st.columns(2)
    physician = c11.text_input("Doctor", k["physician"], key=f"{prefix}phy")
    physician_ph = c12.text_input("Doctor phone", k["physician_phone"], key=f"{prefix}phyp")
    return {
        "birthdate": birthdate, "address": address,
        "mother_name": mother, "mother_phone": mother_ph,
        "father_name": father, "father_phone": father_ph, "email": email,
        "emergency1": e1, "emergency1_phone": e1p,
        "emergency2": e2, "emergency2_phone": e2p,
        "authorized_pickups": pickups, "notes": allergies, "medications": medications,
        "physician": physician, "physician_phone": physician_ph,
    }


def admin_profile_editor(k: dict):
    if k["child_photo"]:
        st.image(k["child_photo"][0]["url"], width=140)
    with st.form(f"prof_{k['id']}"):
        cohort = st.selectbox("Cohort", [""] + COHORT_OPTIONS,
                              index=_idx([""] + COHORT_OPTIONS, k["cohort"]), key=f"co_{k['id']}")
        vals = profile_fields(k, prefix=f"a_{k['id']}_")
        c1, c2 = st.columns(2)
        photo_social = c1.selectbox("OK on social media?", ["", "Yes", "No"],
                                    index=_idx(["", "Yes", "No"], k["photo_social"]), key=f"ps_{k['id']}")
        photo_blur = c2.selectbox("Blur face if not?", ["", "Yes", "No"],
                                  index=_idx(["", "Yes", "No"], k["photo_blur"]), key=f"pb_{k['id']}")
        with st.expander("Emergency medical details"):
            c13, c14 = st.columns(2)
            hospital = c13.text_input("Hospital", k["hospital"], key=f"hos_{k['id']}")
            hospital_ph = c14.text_input("Hospital phone", k["hospital_phone"], key=f"hosp_{k['id']}")
            c15, c16 = st.columns(2)
            insurance = c15.text_input("Insurance", k["insurance"], key=f"ins_{k['id']}")
            policy = c16.text_input("Policy #", k["policy_number"], key=f"pol_{k['id']}")
        photo = st.file_uploader("Child photo", type=["png", "jpg", "jpeg"], key=f"ph_{k['id']}")
        scan = st.file_uploader("Signed paper form (photo/PDF)",
                                type=["png", "jpg", "jpeg", "pdf"], key=f"sc_{k['id']}")
        saved = st.form_submit_button("💾 Save profile", type="primary")
    if saved:
        vals.update({"cohort": cohort, "photo_social": photo_social, "photo_blur": photo_blur,
                     "hospital": hospital, "hospital_phone": hospital_ph,
                     "insurance": insurance, "policy_number": policy})
        store.update_kid(k["id"], vals)
        if photo is not None:
            store.set_child_photo(k["id"], photo.name, photo.getvalue())
        if scan is not None:
            store.upload_enrollment_form(k["id"], scan.name, scan.getvalue())
        st.success("Saved.")
        st.rerun()
    if k["enrollment_form"]:
        st.caption("Attached forms:")
        for att in k["enrollment_form"]:
            st.markdown(f"- [{att['filename']}]({att['url']})")


def view_admin():
    st.markdown(css(), unsafe_allow_html=True)
    logo_header()
    st.markdown("<div class='subtitle'>Admin</div>", unsafe_allow_html=True)
    banner()
    if not check_password():
        return
    if not EMAIL_CFG.get("host"):
        st.caption("✉️ Email notifications aren't configured yet — profile-change "
                   "alerts won't send until the [email] secrets are set.")

    kids = store.list_kids()
    waitlist = [k for k in kids if k["status"] == "Waitlist"]
    enrolled = [k for k in kids if k["status"] == "Enrolled"]
    date_iso = S.today_iso(TZ)
    todays = store.list_checkins_for_date(date_iso)
    here_now = len({c["kid_id"] for c in todays if not c["check_out"]})

    m1, m2, m3 = st.columns(3)
    m1.metric("On waitlist", len(waitlist))
    m2.metric("Enrolled", len(enrolled))
    m3.metric("Here today", here_now)

    t_wait, t_kids, t_today, t_ann, t_upd = st.tabs(
        [f"Waitlist ({len(waitlist)})", f"Children ({len(enrolled)})",
         "Today", "Announcements", "Daily Update"]
    )

    with t_wait:
        if not waitlist:
            st.write("No one on the waitlist.")
        for pos, k in enumerate(waitlist, 1):
            c1, c2 = st.columns([5, 1])
            pref = f" · prefers {k['cohort']}" if k["cohort"] else ""
            c1.markdown(f"**{pos}. {k['name']}** — {k['parent_name']} · {k['phone']} · {k['signup_date']}{pref}"
                        + (f"  \n_{k['notes']}_" if k["notes"] else ""))
            if c2.button("Enroll ✅", key=f"enroll_{k['id']}", width="stretch"):
                store.update_kid_status(k["id"], "Enrolled")
                assign_pin(k["id"])
                st.rerun()

    with t_kids:
        if not enrolled:
            st.write("No one enrolled yet.")
        for k in enrolled:
            label = f"{k['name']}" + (f"  ·  {k['cohort']}" if k["cohort"] else "")
            with st.expander(label):
                code = k["pin"] or "—"
                cc1, cc2 = st.columns([3, 1])
                cc1.markdown(f"Family code (check-in + portal): <span class='codechip'>{code}</span>",
                             unsafe_allow_html=True)
                if cc2.button("New code", key=f"code_{k['id']}", width="stretch"):
                    assign_pin(k["id"])
                    st.rerun()
                admin_profile_editor(k)
                if st.button("Withdraw child", key=f"wd_{k['id']}"):
                    store.update_kid_status(k["id"], "Withdrawn")
                    st.rerun()

    with t_today:
        st.caption(f"Attendance for {date_iso}")
        name_by_id = {k["id"]: k["name"] for k in kids}
        if not todays:
            st.write("No check-ins yet today.")
        else:
            st.dataframe([{"Child": name_by_id.get(c["kid_id"], "?"), "In": c["check_in"],
                           "Out": c["check_out"] or "—"} for c in todays],
                         width="stretch", hide_index=True)

    with t_ann:
        with st.form("new_ann", clear_on_submit=True):
            title = st.text_input("Title")
            msg = st.text_area("Message")
            if st.form_submit_button("📣 Post announcement", type="primary") and (title or msg):
                now = S.now_local(TZ)
                store.add_announcement(title.strip(), msg.strip(),
                                       now.strftime("%b ") + str(now.day) + now.strftime(", %Y"), S.stamp(TZ))
                st.rerun()
        st.divider()
        for a in store.list_announcements():
            c1, c2 = st.columns([6, 1])
            c1.markdown(f"<div class='post'><div class='when'>{a['posted_date']}</div>"
                        f"<div class='head'>{a['title']}</div>{a['message']}</div>", unsafe_allow_html=True)
            if c2.button("Delete", key=f"delann_{a['id']}"):
                store.delete_announcement(a["id"])
                st.rerun()

    with t_upd:
        now = S.now_local(TZ)
        meeting = cohorts_meeting_today(now)
        opts = COHORT_OPTIONS + ["All"]
        with st.form("new_upd", clear_on_submit=True):
            up_cohort = st.selectbox("Which group?", opts, index=_idx(opts, meeting[0] if meeting else "All"))
            note = st.text_area("What did we do today?")
            photos = st.file_uploader("Photos", type=["png", "jpg", "jpeg"], accept_multiple_files=True)
            no_social = [k["name"] for k in enrolled
                         if k["photo_social"] == "No" and (up_cohort == "All" or k["cohort"] == up_cohort)]
            if no_social:
                st.warning("⚠️ No social-media consent (don't post publicly): " + ", ".join(no_social))
            if st.form_submit_button("🌈 Post update", type="primary") and (note or photos):
                u = store.add_update(S.today_iso(TZ), note.strip(), up_cohort)
                if photos:
                    store.add_update_photos(u["id"], [(f.name, f.getvalue()) for f in photos])
                st.rerun()
        st.divider()
        for u in store.list_updates()[:10]:
            tag = f" · {u['cohort']}" if u["cohort"] else ""
            st.markdown(f"<div class='post'><div class='when'>{u['date']}{tag}</div>{u['note']}</div>",
                        unsafe_allow_html=True)
            if u["photos"]:
                pcols = st.columns(4)
                for i, ph in enumerate(u["photos"]):
                    pcols[i % 4].image(ph["url"], width="stretch")


# ------------------------------------------------------------------ PARENT PORTAL
def contact_and_handbook():
    if CONTACT or HANDBOOK_URL:
        st.markdown("### 📇 Contact Mrs. Y")
        bits = []
        if CONTACT.get("name"):
            bits.append(f"**{CONTACT['name']}**")
        if CONTACT.get("phone"):
            bits.append(f"📱 [{CONTACT['phone']}](sms:{CONTACT['phone']})")
        if CONTACT.get("email"):
            bits.append(f"✉️ {CONTACT['email']}")
        if CONTACT.get("address"):
            bits.append(f"📍 {CONTACT['address']}")
        st.markdown("<div class='contactbox'>" + "<br>".join(bits) + "</div>", unsafe_allow_html=True)
    if HANDBOOK_URL:
        st.markdown("### 📖 Parent Handbook")
        st.markdown(f"[Open the handbook]({HANDBOOK_URL})")
        png = notify.qr_png(HANDBOOK_URL)
        if png:
            st.image(png, width=160, caption="Scan for the handbook")


def parent_profile_form(k: dict):
    st.markdown(f"### 👶 {k['name']}'s profile")
    if k["child_photo"]:
        st.image(k["child_photo"][0]["url"], width=160)
    with st.form(f"pp_{k['id']}"):
        vals = profile_fields(k, prefix=f"p_{k['id']}_")
        photo = st.file_uploader("Update photo", type=["png", "jpg", "jpeg"], key=f"pph_{k['id']}")
        saved = st.form_submit_button("💾 Save my changes", type="primary")
    if saved:
        store.update_kid(k["id"], vals)
        if photo is not None:
            store.set_child_photo(k["id"], photo.name, photo.getvalue())
        ok, _ = notify.send_email(
            EMAIL_CFG,
            f"[Tot Spot] {k['name']}'s profile was updated",
            f"{k['name']}'s family updated their profile in the parent portal "
            f"at {S.stamp(TZ)}.\n\nOpen Admin → Children to review.",
        )
        st.success("Saved! " + ("Mrs. Y has been notified. 💌" if ok else "Thanks!"))
        st.rerun()


def view_parent():
    st.markdown(css(), unsafe_allow_html=True)
    logo_header()
    banner()
    code = st.session_state.get("parent_pin")
    if not code:
        st.markdown("<div class='subtitle'>Enter your 4-digit family code 🌈</div>", unsafe_allow_html=True)
        cols = st.columns([1, 2, 1])
        with cols[1]:
            entered = st.text_input("Family code", max_chars=4)
            if st.button("View", type="primary", width="stretch") and entered.strip():
                st.session_state.parent_pin = entered.strip()
                st.rerun()
        return

    kids = enrolled_by_pin(code)
    if not kids:
        st.error("That code didn't match an enrolled child. Double-check with Mrs. Y.")
        if st.button("Try another code"):
            del st.session_state["parent_pin"]
            st.rerun()
        return

    names = ", ".join(k["name"] for k in kids)
    my_cohorts = {k["cohort"] for k in kids if k["cohort"]}
    st.markdown(f"<div class='subtitle'>Welcome, family of {names}! 👋</div>", unsafe_allow_html=True)

    st.markdown("### 📣 Announcements")
    anns = store.list_announcements()
    if not anns:
        st.caption("No announcements right now.")
    for a in anns[:10]:
        st.markdown(f"<div class='post'><div class='when'>{a['posted_date']}</div>"
                    f"<div class='head'>{a['title']}</div>{a['message']}</div>", unsafe_allow_html=True)

    st.markdown("### 🌈 Daily updates")
    updates = [u for u in store.list_updates()
               if not u["cohort"] or u["cohort"] == "All" or u["cohort"] in my_cohorts]
    if not updates:
        st.caption("No updates yet.")
    for u in updates[:15]:
        st.markdown(f"<div class='post'><div class='when'>{u['date']}</div>{u['note']}</div>",
                    unsafe_allow_html=True)
        if u["photos"]:
            pcols = st.columns(4)
            for i, ph in enumerate(u["photos"]):
                pcols[i % 4].image(ph["url"], width="stretch")

    for k in kids:
        parent_profile_form(k)

    contact_and_handbook()

    if st.button("Sign out"):
        del st.session_state["parent_pin"]
        st.rerun()


# ------------------------------------------------------------------ HOME
def view_home():
    st.markdown(css(), unsafe_allow_html=True)
    logo_header()
    banner()
    st.markdown(
        """
        <div class="home-grid">
          <a class="home-card c-green" href="?view=kiosk" target="_self">
            <span class="emoji">🧒</span>Check-in Kiosk<span class="sub">Open this on the iPad</span></a>
          <a class="home-card c-coral" href="?view=signup" target="_self">
            <span class="emoji">✏️</span>Sign-up Form<span class="sub">Share the link / QR with parents</span></a>
          <a class="home-card c-teal" href="?view=parent" target="_self">
            <span class="emoji">🌈</span>Family Portal<span class="sub">Updates, profile & handbook</span></a>
          <a class="home-card c-lav" href="?view=admin" target="_self">
            <span class="emoji">📋</span>Admin<span class="sub">Waitlist, profiles & posting</span></a>
        </div>
        """,
        unsafe_allow_html=True,
    )


ROUTES = {
    "kiosk": view_kiosk, "signup": view_signup, "admin": view_admin,
    "parent": view_parent, "home": view_home,
}
ROUTES.get(st.query_params.get("view", "home"), view_home)()
