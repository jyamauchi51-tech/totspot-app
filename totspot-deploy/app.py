"""The Tot Spot — waitlist sign-up, PIN check-in kiosk, admin management, and a
family portal where parents view announcements and edit their child's profile.

Views chosen by the ?view= URL parameter:
  ?view=kiosk   -> iPad check-in (6-digit PIN pad)
  ?view=signup  -> public waitlist sign-up
  ?view=admin   -> password-protected management
  ?view=parent  -> family portal (enter 6-digit code)
  (no param)    -> home page with links
"""

import base64
import io
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import streamlit as st

import notify
import store as S

_ICON192 = Path(__file__).resolve().parent / "assets" / "app-icon-192.png"
st.set_page_config(page_title="The Tot Spot",
                   page_icon=str(_ICON192) if _ICON192.exists() else "🐛",
                   layout="wide", initial_sidebar_state="collapsed")

LOGO_PATH = Path(__file__).resolve().parent / "assets" / "logo.png"  # load next to app.py


def _logo_data_uri() -> str:
    try:
        return "data:image/png;base64," + base64.b64encode(LOGO_PATH.read_bytes()).decode()
    except Exception:
        return ""


LOGO_URI = _logo_data_uri()

_PWA_DONE = False


def inject_pwa():
    """Make the app installable (Add to Home Screen -> full-screen app).
    Writes a manifest + icons into Streamlit's static dir and patches <head>."""
    global _PWA_DONE
    if _PWA_DONE:
        return
    try:
        import re

        # Icons + manifest are hosted on the Netlify site (served cleanly, with
        # no Streamlit auth-cookie bounce that would otherwise return a red icon).
        site = "https://tubular-sawine-ac3d51.netlify.app"
        idx = Path(st.__file__).parent / "static" / "index.html"
        html = idx.read_text(encoding="utf-8")
        if "tot-spot-pwa" not in html:
            # remove Streamlit's own icon/manifest links so ours win
            html = re.sub(r'<link[^>]*rel="(shortcut icon|icon|apple-touch-icon|manifest)"[^>]*>',
                          "", html)
            tags = (
                "<!--tot-spot-pwa-->"
                f'<link rel="manifest" href="{site}/manifest.json">'
                f'<link rel="apple-touch-icon" href="{site}/apple-touch-icon.png">'
                f'<link rel="icon" type="image/png" href="{site}/app-icon-192.png">'
                '<meta name="apple-mobile-web-app-capable" content="yes">'
                '<meta name="apple-mobile-web-app-status-bar-style" content="default">'
                '<meta name="apple-mobile-web-app-title" content="The Tot Spot">'
                '<meta name="theme-color" content="#F4978E">'
            )
            idx.write_text(html.replace("</head>", tags + "</head>", 1), encoding="utf-8")
        _PWA_DONE = True
    except Exception:
        pass


inject_pwa()
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
APP_URL = SECRETS.get("app_url", "https://the-tot-spot.streamlit.app")

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
/* the ☰ Menu popup button */
.menubtn div[data-testid="stPopover"] button { font-family:'Baloo 2'; font-weight:800; }

/* rainbow bar pinned to the very top */
.stApp::before{content:"";position:fixed;top:0;left:0;right:0;height:6px;z-index:1000;
  background:linear-gradient(90deg,__CORAL__,__ORANGE__,__YELLOW__,__GREEN__,__TEAL__,__LAVENDER__);}

/* playful polka-dot background */
.stApp{background-color:#FFFAF6;
  background-image:radial-gradient(rgba(244,151,142,.18) 2.2px, transparent 2.4px);
  background-size:26px 26px;}

/* content sits on a clean white "sheet" floating over the dots */
.block-container{background:#fff;border-radius:1.8rem;padding:2rem 2.3rem 3rem;
  box-shadow:0 12px 44px rgba(0,0,0,.08);margin-top:1.7rem;margin-bottom:2rem;
  max-width:1020px;border:1px solid __LINE__;}

.subtitle { text-align: center; color: __MUTED__; font-size: 1.15rem; margin: -.2rem 0 1.2rem; font-weight: 600; }
.brand { font-family: 'Baloo 2'; font-weight: 800; font-size: 2.6rem; text-align: center; }
.codechip { display:inline-block; background:__lavender_bg__; color:__ink__; font-family:'Baloo 2';
    font-weight:800; letter-spacing:.2em; font-size:1.3rem; padding:.2rem .8rem; border-radius:.6rem; }
.pindots { text-align:center; font-size:2rem; letter-spacing:.35em; color:__coral__; margin:.2rem 0 .5rem; }

/* buttons — brand coral, baked in so they never fall back to Streamlit red */
div[data-testid="stButton"] > button, div[data-testid="stFormSubmitButton"] > button {
    border-radius: 999px; font-weight: 700; font-family: 'Baloo 2';
    background:#fff; color:__CORAL__; border:2px solid __CORAL__; padding:.5rem 1.25rem;
    transition:transform .08s ease, box-shadow .08s ease;
}
div[data-testid="stButton"] > button:hover, div[data-testid="stFormSubmitButton"] > button:hover {
    transform:translateY(-2px); box-shadow:0 6px 16px rgba(244,151,142,.35);
    border-color:__CORAL__; color:__CORAL__;
}
button[kind="primary"], button[kind="primaryFormSubmit"] {
    background:__CORAL__ !important; color:#fff !important; border-color:__CORAL__ !important;
    box-shadow:0 4px 14px rgba(244,151,142,.45) !important;
}
button[kind="primary"]:hover, button[kind="primaryFormSubmit"]:hover { color:#fff !important; filter:brightness(.96); }

/* rounder inputs + branded tabs */
.stTextInput input, .stTextArea textarea, .stDateInput input { border-radius:.8rem !important; }
/* keep inputs + labels readable even if the phone/browser is in dark mode */
div[data-baseweb="input"], div[data-baseweb="base-input"], div[data-baseweb="select"] { background:#fff !important; }
.stTextInput input, .stTextArea textarea, .stNumberInput input, .stDateInput input {
    background:#fff !important; color:__ink__ !important; -webkit-text-fill-color:__ink__ !important;
}
[data-testid="stWidgetLabel"] *, .stTextInput label, .stTextArea label, .stSelectbox label,
.stRadio label, .stCheckbox label { color:__ink__ !important; }
[data-testid="stForm"] { background:#fff; }
.stTabs [data-baseweb="tab-list"] { gap:.45rem; flex-wrap:wrap; border-bottom:none; }
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] { display:none !important; }
.stTabs [data-baseweb="tab"] {
    font-family:'Baloo 2'; font-weight:700; background:__coral_bg__; color:__ink__;
    border-radius:999px; padding:.35rem 1.05rem; border:2px solid transparent; height:auto;
}
.stTabs [data-baseweb="tab"]:hover { background:#fff; border-color:__coral__; color:__ink__; }
.stTabs [aria-selected="true"] {
    background:__coral__ !important; color:#fff !important; border-color:__coral__ !important;
    box-shadow:0 3px 10px rgba(244,151,142,.4);
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
    height: 3.5rem; font-size: 1.55rem; border-radius: .9rem; font-family:'Baloo 2';
    background: __coral_bg__ !important; color: __ink__ !important;
    border: 2px solid __coral__ !important; box-shadow: 0 2px 6px rgba(0,0,0,.10); padding:.2rem;
}
div[class*="st-key-kp_"] button:hover { background:#fff !important; color:__coral__ !important; }
div[class*="st-key-kp_"] button:active { transform: scale(.96); }
.bigcard { border:3px solid __LINE__; border-radius:1.6rem; padding:1.5rem; text-align:center;
    box-shadow:0 4px 14px rgba(0,0,0,.06); }

div[data-testid="stMetric"] { background: __CARD__; border: 2px solid __LINE__; border-radius: 1.2rem; padding: .8rem 1rem; }

.post { border: 2px solid __LINE__; border-radius: 1.1rem; padding: 1rem 1.2rem; margin-bottom: 1rem; background: __CARD__; }
.post .when { color: __MUTED__; font-weight: 700; font-size: .9rem; }
.post .head { font-family:'Baloo 2'; font-weight: 800; font-size: 1.25rem; margin: .1rem 0 .3rem; }
.contactbox { background:__teal_bg__; border-radius:1.1rem; padding:1rem 1.2rem; }

/* cute student ID card */
.idcard{max-width:370px;margin:.4rem auto 1.4rem;background:#fff;border-radius:1.1rem;overflow:hidden;
  box-shadow:0 10px 26px rgba(0,0,0,.15);border:1px solid __LINE__;}
.idbar{height:8px;background:linear-gradient(90deg,__CORAL__,__ORANGE__,__YELLOW__,__GREEN__,__TEAL__,__LAVENDER__);}
.idtop{display:flex;align-items:center;justify-content:space-between;padding:.6rem 1rem .2rem;}
.idlogo{height:34px;width:auto;}
.idtag{background:__CORAL__;color:#fff;font-family:'Baloo 2';font-weight:800;font-size:.72rem;
  letter-spacing:.12em;padding:.28rem .7rem;border-radius:999px;}
.idbody{display:flex;flex-wrap:nowrap;gap:.8rem;padding:.5rem .9rem .9rem;align-items:center;}
.idphoto{width:88px;height:88px;object-fit:cover;border-radius:.8rem;border:3px solid __YELLOW__;flex:0 0 auto;}
.idfields{min-width:0;}
.idname{font-family:'Baloo 2';font-weight:800;font-size:1.2rem;color:__INK__;line-height:1.05;margin-bottom:.2rem;}
.idrow{font-size:.8rem;color:__INK__;margin:.05rem 0;}
.idrow b{color:__MUTED__;font-weight:800;font-size:.58rem;text-transform:uppercase;letter-spacing:.04em;
  margin-right:.35rem;display:inline-block;min-width:58px;}
.idnum{margin-top:.35rem;font-size:.9rem;}
.idnum{margin-top:.45rem;font-family:'Baloo 2';font-weight:800;color:__CORAL__;letter-spacing:.05em;}
.idfoot{background:__CORAL_BG__;text-align:center;padding:.5rem;font-family:'Baloo 2';font-weight:700;
  color:__INK__;font-size:.9rem;}

/* daily-report chips */
.chip{display:inline-block;background:__teal_bg__;color:__ink__;border-radius:999px;
  padding:.15rem .65rem;margin:.15rem .25rem 0 0;font-weight:700;font-size:.85rem;}
.chip.snack{background:__yellow_bg__;} .chip.mood{background:__coral_bg__;} .chip.potty{background:__lavender_bg__;}
.rep{border:2px solid __line__;border-radius:1rem;padding:.8rem 1rem;margin-bottom:.8rem;background:#fff;}
.rep h4{font-family:'Baloo 2';margin:0 0 .2rem;}
.rep .lbl{font-weight:800;color:__muted__;font-size:.72rem;text-transform:uppercase;letter-spacing:.04em;margin-top:.5rem;}

/* scrapbook */
.scrapbook{background:#fff;border-radius:1rem;padding:1rem .5rem;}
.sb-title{font-family:'Baloo 2';text-align:center;font-size:1.8rem;margin:.2rem 0 1rem;}
.sb-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:1rem;}
.sb-card{border:1px solid __line__;border-radius:.8rem;overflow:hidden;background:#fff;box-shadow:0 3px 10px rgba(0,0,0,.08);}
.sb-card img{width:100%;height:190px;object-fit:cover;display:block;}
.sb-cap{padding:.5rem .7rem;font-weight:600;font-size:.95rem;}
.sb-foot{display:flex;justify-content:flex-end;align-items:center;gap:.5rem;margin-top:1rem;padding-right:.5rem;}
.sb-foot img{height:34px;width:auto;} .sb-foot span{font-family:'Baloo 2';color:__muted__;font-size:.8rem;}

@media print{
  [data-testid="stHeader"],[data-testid="stToolbar"],[data-testid="stSidebar"],
  .stTabs [data-baseweb="tab-list"], div[data-testid="stButton"], .no-print{display:none !important;}
  .stApp::before{display:none !important;}
  .stApp,.block-container{background:#fff !important;box-shadow:none !important;border:none !important;padding:0 !important;}
  .sb-card{break-inside:avoid;}
}
</style>
"""


def css() -> str:
    s = GLOBAL_CSS
    for k, v in COLORS.items():
        s = s.replace(f"__{k.upper()}__", v).replace(f"__{k}__", v)
    return s


def logo_header(max_width: int = 440):
    if LOGO_URI:
        st.markdown(
            f"<div style='text-align:center'><img src='{LOGO_URI}' "
            f"style='width:78%;max-width:{max_width}px;margin:.1rem auto .3rem;display:inline-block'/></div>",
            unsafe_allow_html=True)
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


def id_card_html(k: dict, now) -> str:
    """A cute 'Student ID' card for the family portal (shown once a photo exists)."""
    photo = k["child_photo"][0]["url"] if k["child_photo"] else ""
    age = compute_age(k["birthdate"], now)
    bday = k["birthdate"] or "—"
    if age:
        bday = f"{bday} · {age}"
    parents = " & ".join(p for p in [k["parent_name"], k["parent2_name"]] if p) or "—"
    sid = k["pin"] or "----"
    return f"""
    <div class="idcard">
      <div class="idbar"></div>
      <div class="idtop"><img src="{LOGO_URI}" class="idlogo"/><span class="idtag">STUDENT ID</span></div>
      <div class="idbody">
        <img src="{photo}" class="idphoto"/>
        <div class="idfields">
          <div class="idname">{k['name']}</div>
          <div class="idrow"><b>Birthday</b>{bday}</div>
          <div class="idrow"><b>Gender</b>{k['gender'] or '—'}</div>
          <div class="idrow"><b>Cohort</b>{k['cohort'] or '—'}</div>
          <div class="idrow"><b>Year</b>{k['school_year'] or '—'}</div>
          <div class="idrow"><b>Grown-ups</b>{parents}</div>
          <div class="idnum">★ Student #{sid} ★</div>
        </div>
      </div>
      <div class="idfoot">The Tot Spot · Preschool Prep · Little Learner 🌈</div>
    </div>
    """


def child_photo_uploader(k: dict, key_prefix: str):
    """Upload a photo and crop it to the child's face before saving."""
    up = st.file_uploader("Upload / change photo", type=["png", "jpg", "jpeg"],
                          key=f"{key_prefix}up_{k['id']}")
    if up is None:
        return
    try:
        from streamlit_cropper import st_cropper
        from PIL import Image
    except Exception:  # cropper unavailable -> save uncropped
        if st.button("💾 Save photo", key=f"{key_prefix}save_{k['id']}", type="primary"):
            store.set_child_photo(k["id"], up.name, up.getvalue())
            st.rerun()
        return
    st.caption("Drag & resize the box to crop to your child's face 🙂")
    cropped = st_cropper(Image.open(up), box_color="#F4978E", aspect_ratio=(1, 1),
                         realtime_update=True, key=f"{key_prefix}crop_{k['id']}")
    st.image(cropped, width=150, caption="Preview")
    if st.button("💾 Save photo", key=f"{key_prefix}save_{k['id']}", type="primary"):
        buf = io.BytesIO()
        cropped.convert("RGB").save(buf, format="JPEG", quality=88)
        store.set_child_photo(k["id"], f"{k['name'] or 'child'}.jpg", buf.getvalue())
        st.success("Photo saved!")
        st.rerun()


def enrolled_by_pin(pin: str) -> list[dict]:
    pin = (pin or "").strip()
    return [k for k in store.list_kids()
            if k["status"] == "Enrolled" and (k.get("pin") or "").strip() == pin]


def kids_for_login(email: str) -> list[dict]:
    """Enrolled kids whose parent email (either parent) matches the login email."""
    e = (email or "").strip().lower()
    if not e:
        return []
    out = []
    for k in store.list_kids():
        if k["status"] != "Enrolled":
            continue
        emails = {(k.get("login_email") or "").strip().lower(),
                  (k.get("email") or "").strip().lower(),
                  (k.get("parent2_email") or "").strip().lower()}
        if e in emails:
            out.append(k)
    return out


def authenticate(email: str, password: str) -> list[dict]:
    if not password:
        return []
    return [k for k in kids_for_login(email) if (k.get("login_password") or "") == password]


def _parent_logout():
    for key in ("parent_authed", "parent_login_email", "parent_pin"):
        st.session_state.pop(key, None)


def security_reminder():
    st.markdown(
        f"<div style='text-align:center;color:{COLORS['muted']};font-size:.85rem;margin-top:1.4rem'>"
        "🔒 For optimal security, please don't share your login info or 6-digit code with anyone.</div>",
        unsafe_allow_html=True)


def menu_nav(options: list[str], key: str, logout: bool = False) -> str:
    """A '☰ Menu' button that opens a popup list of sections; returns the chosen one."""
    st.session_state.setdefault(key, options[0])
    current = st.session_state[key]
    with st.popover(f"☰  {current}", use_container_width=True):
        for opt in options:
            if st.button(opt, key=f"{key}__{opt}", width="stretch"):
                st.session_state[key] = opt
                st.rerun()
        if logout:
            st.divider()
            if st.button("Sign out", key=f"{key}__signout", width="stretch"):
                _parent_logout()
                st.rerun()
    return st.session_state[key]


def assign_pin(kid_id: str):
    existing = {(k.get("pin") or "") for k in store.list_kids()}
    store.update_kid(kid_id, {"pin": S.new_pin(existing)})


PIN_LEN = 6


def _locked(scope: str) -> bool:
    """True if this browser is temporarily locked out after too many wrong codes."""
    now = S.now_local(TZ).timestamp()
    until = st.session_state.get(f"{scope}_lock_until", 0)
    if now < until:
        st.error(f"Too many attempts. Please wait {int(until - now)} seconds, then try again.")
        return True
    return False


def _record_fail(scope: str, limit: int = 5, wait: int = 60):
    n = st.session_state.get(f"{scope}_fails", 0) + 1
    st.session_state[f"{scope}_fails"] = n
    if n >= limit:
        st.session_state[f"{scope}_lock_until"] = S.now_local(TZ).timestamp() + wait
        st.session_state[f"{scope}_fails"] = 0


def _reset_fails(scope: str):
    st.session_state[f"{scope}_fails"] = 0
    st.session_state[f"{scope}_lock_until"] = 0


# ------------------------------------------------------------------ KIOSK (PIN)
def view_kiosk():
    st.markdown(css(), unsafe_allow_html=True)
    logo_header(max_width=230)
    now = S.now_local(TZ)
    st.markdown("<div style=\"text-align:center;font-family:'Baloo 2',cursive;font-weight:800;"
                "font-size:1.7rem;color:#2B2B2B;margin:.2rem 0 0\">Welcome to The Tot Spot! 👋</div>",
                unsafe_allow_html=True)
    st.markdown(f"<div class='subtitle'>Check-in &middot; {now.strftime('%A, %B ')}{now.day}</div>",
                unsafe_allow_html=True)
    banner()

    if flash := st.session_state.pop("kflash", ""):
        st.success(flash)

    pin = st.session_state.setdefault("kpin", "")

    if len(pin) == PIN_LEN:
        matches = enrolled_by_pin(pin)
        cols = st.columns([1, 2, 1])
        with cols[1]:
            if not matches:
                _record_fail("kiosk")
                st.error("No child found for that code.")
            else:
                _reset_fails("kiosk")
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
                            st.session_state.kflash = (f"Have a great rest of your day, {kid['name']}! "
                                                       "See you next time. 👋")
                        else:
                            store.add_checkin(kid["id"], date_iso, S.time_str(TZ))
                            st.session_state.kflash = (f"Have a great day, {kid['name']}! "
                                                       "See you in a few. 🌈")
                        st.session_state.kpin = ""
                        st.rerun()
            if st.button("Start over", width="stretch"):
                st.session_state.kpin = ""
                st.rerun()
        return

    # keypad
    cols = st.columns([1, 2, 1])
    with cols[1]:
        if _locked("kiosk"):
            return
        dots = "".join("●" if i < len(pin) else "○" for i in range(PIN_LEN))
        st.markdown(f"<div class='pindots'>{dots}</div>", unsafe_allow_html=True)
        st.markdown("<div class='subtitle'>Enter your 6-digit family code</div>", unsafe_allow_html=True)

        def press(d):
            if len(st.session_state.kpin) < PIN_LEN:
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
        num_parents = st.selectbox("How many parents / guardians?", [1, 2], key="signup_np")
        with st.form("signup", clear_on_submit=True, border=True):
            child = st.text_input("Child's name *")
            c0a, c0b = st.columns(2)
            birthdate = c0a.text_input("Child's birthdate (MM/DD/YYYY)")
            gender = c0b.selectbox("Child's gender", ["", "Male", "Female"])

            st.markdown("**Parent / guardian 1**")
            parent = st.text_input("Name *", key="p1n")
            c1, c2 = st.columns(2)
            phone = c1.text_input("Phone *", key="p1p")
            email = c2.text_input("Email", key="p1e")

            parent2 = parent2_phone = parent2_email = ""
            if num_parents == 2:
                st.markdown("**Parent / guardian 2**")
                parent2 = st.text_input("Name", key="p2n")
                c2a, c2b = st.columns(2)
                parent2_phone = c2a.text_input("Phone", key="p2p")
                parent2_email = c2b.text_input("Email", key="p2e")

            c3, c4 = st.columns(2)
            school_year = c3.selectbox("Desired school year", ["2026-2027", "2027-2028", "2028-2029"])
            cohort = c4.selectbox("Preferred cohort", ["No preference"] + COHORT_OPTIONS)
            notes = st.text_area("Allergies / anything we should know?")
            submitted = st.form_submit_button("Join the waitlist  🎉", width="stretch", type="primary")
        if submitted:
            if not child or not parent or not phone:
                st.error("Please fill in the required fields (*).")
                return
            store.add_kid({
                "name": child.strip(), "birthdate": birthdate.strip(), "gender": gender,
                "parent_name": parent.strip(), "phone": phone.strip(), "email": email.strip(),
                "parent2_name": parent2.strip(), "parent2_phone": parent2_phone.strip(),
                "parent2_email": parent2_email.strip(),
                "notes": notes.strip(), "school_year": school_year,
                "cohort": "" if cohort == "No preference" else cohort,
                "status": "Waitlist", "signup_date": S.today_iso(TZ),
            })
            p2_line = (f"Parent 2: {parent2.strip()} ({parent2_phone.strip()}, {parent2_email.strip()})\n"
                       if parent2.strip() else "")
            notify.send_email(
                EMAIL_CFG,
                f"[Tot Spot] New waitlist sign-up: {child.strip()}",
                (f"{child.strip()} joined the waitlist on {S.today_iso(TZ)}.\n\n"
                 f"Parent 1: {parent.strip()} ({phone.strip()}, {email.strip()})\n"
                 f"{p2_line}"
                 f"Gender: {gender or '—'}\nDesired school year: {school_year}\n"
                 f"Cohort preference: {cohort}\nNotes: {notes.strip() or '—'}\n\n"
                 f"Open Admin → Waitlist to review."),
            )
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
    cg1, cg2 = st.columns(2)
    gender = cg1.selectbox("Gender", ["", "Male", "Female"],
                           index=_idx(["", "Male", "Female"], k["gender"]), key=f"{prefix}gn")
    school_year = cg2.selectbox("School year", ["", "2026-2027", "2027-2028", "2028-2029"],
                                index=_idx(["", "2026-2027", "2027-2028", "2028-2029"], k["school_year"]),
                                key=f"{prefix}sy")
    address = st.text_input("Address", k["address"], key=f"{prefix}ad")
    st.markdown("**Parent / guardian 1**")
    p1n = st.text_input("Name", k["parent_name"], key=f"{prefix}p1n")
    cp1, cp2 = st.columns(2)
    p1p = cp1.text_input("Phone", k["phone"], key=f"{prefix}p1p")
    p1e = cp2.text_input("Email", k["email"], key=f"{prefix}p1e")
    st.markdown("**Parent / guardian 2**")
    p2n = st.text_input("Name", k["parent2_name"], key=f"{prefix}p2n")
    cp3, cp4 = st.columns(2)
    p2p = cp3.text_input("Phone", k["parent2_phone"], key=f"{prefix}p2p")
    p2e = cp4.text_input("Email", k["parent2_email"], key=f"{prefix}p2e")
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
        "birthdate": birthdate, "gender": gender, "school_year": school_year, "address": address,
        "parent_name": p1n, "phone": p1p, "email": p1e,
        "parent2_name": p2n, "parent2_phone": p2p, "parent2_email": p2e,
        "emergency1": e1, "emergency1_phone": e1p,
        "emergency2": e2, "emergency2_phone": e2p,
        "authorized_pickups": pickups, "notes": allergies, "medications": medications,
        "physician": physician, "physician_phone": physician_ph,
    }


def admin_profile_editor(k: dict):
    if k["child_photo"]:
        st.image(k["child_photo"][0]["url"], width=140)
    child_photo_uploader(k, "a")
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
        login_pw = st.text_input("Family portal password", k.get("login_password", ""),
                                 key=f"lpw_{k['id']}",
                                 help="Parent logs into the portal with their email + this password.")
        scan = st.file_uploader("Signed paper form (photo/PDF)",
                                type=["png", "jpg", "jpeg", "pdf"], key=f"sc_{k['id']}")
        saved = st.form_submit_button("💾 Save profile", type="primary")
    if saved:
        vals.update({"cohort": cohort, "photo_social": photo_social, "photo_blur": photo_blur,
                     "hospital": hospital, "hospital_phone": hospital_ph,
                     "insurance": insurance, "policy_number": policy,
                     "login_password": login_pw})
        store.update_kid(k["id"], vals)
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

    t_wait, t_kids, t_today, t_logs, t_ann, t_upd, t_album = st.tabs(
        [f"Waitlist ({len(waitlist)})", f"Children ({len(enrolled)})",
         "Today", "Daily Logs", "Announcements", "Daily Update", "Album"]
    )

    with t_wait:
        if not waitlist:
            st.write("No one on the waitlist.")
        for pos, k in enumerate(waitlist, 1):
            c1, c2, c3 = st.columns([5, 1, 1])
            pref = f" · prefers {k['cohort']}" if k["cohort"] else ""
            c1.markdown(f"**{pos}. {k['name']}** — {k['parent_name']} · {k['phone']} · {k['signup_date']}{pref}"
                        + (f"  \n_{k['notes']}_" if k["notes"] else ""))
            if c2.button("Enroll ✅", key=f"enroll_{k['id']}", width="stretch"):
                store.update_kid_status(k["id"], "Enrolled")
                assign_pin(k["id"])
                st.rerun()
            with c3.popover("Remove", width="stretch"):
                st.write(f"Permanently delete **{k['name']}** from the waitlist?")
                if st.button("Yes, delete", key=f"delwait_{k['id']}", type="primary"):
                    store.delete_kid(k["id"])
                    st.rerun()

    with t_kids:
        if not enrolled:
            st.write("No one enrolled yet.")
        for k in enrolled:
            label = f"{k['name']}" + (f"  ·  {k['cohort']}" if k["cohort"] else "")
            with st.expander(label):
                code = k["pin"] or "—"
                cc1, cc2 = st.columns([3, 1])
                cc1.markdown(f"6-digit code (check-in + unlock): <span class='codechip'>{code}</span>",
                             unsafe_allow_html=True)
                if cc2.button("New code", key=f"code_{k['id']}", width="stretch"):
                    assign_pin(k["id"])
                    st.rerun()
                login_email = k.get("login_email") or k["email"] or "— (parent hasn't registered)"
                login_pw = k.get("login_password") or "— (parent hasn't registered)"
                st.caption(f"Portal login → **email:** {login_email}  ·  **password:** {login_pw}")
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

    with t_logs:
        st.caption(f"Per-child daily report for {date_iso}")
        if not enrolled:
            st.write("No enrolled children yet.")
        for k in enrolled:
            existing = store.get_daily_log(k["id"], date_iso) or {}
            with st.expander(f"{k['name']}" + (f"  ·  {k['cohort']}" if k["cohort"] else "")):
                with st.form(f"log_{k['id']}"):
                    pt = st.multiselect("Potty type", S.POTTY_TYPE,
                                        default=existing.get("potty_type", []), key=f"pt_{k['id']}")
                    pp = st.multiselect("Potty progress", S.POTTY_PROGRESS,
                                        default=existing.get("potty_progress", []), key=f"pp_{k['id']}")
                    snack = st.selectbox("Snack", ["", *S.SNACK],
                                         index=_idx(["", *S.SNACK], existing.get("snack", "")),
                                         key=f"sn_{k['id']}")
                    mood = st.multiselect("Mood", S.MOOD,
                                          default=existing.get("mood", []), key=f"mo_{k['id']}")
                    behavior = st.text_area("Behavior notes", existing.get("behavior", ""),
                                            key=f"bh_{k['id']}")
                    injury = st.text_area("Injury report", existing.get("injury", ""),
                                          key=f"inj_{k['id']}")
                    if st.form_submit_button("💾 Save daily report", type="primary"):
                        store.upsert_daily_log(k["id"], date_iso, {
                            "potty_type": pt, "potty_progress": pp, "snack": snack,
                            "mood": mood, "behavior": behavior.strip(), "injury": injury.strip()})
                        st.success("Saved!")
                        st.rerun()

    with t_ann:
        with st.form("new_ann", clear_on_submit=True):
            title = st.text_input("Title")
            msg = st.text_area("Message")
            ann_photos = st.file_uploader("Photos (optional)", type=["png", "jpg", "jpeg"],
                                          accept_multiple_files=True)
            posted = st.form_submit_button("📣 Post announcement", type="primary")
        if posted and (title or msg):
            now = S.now_local(TZ)
            a = store.add_announcement(title.strip(), msg.strip(),
                                       now.strftime("%b ") + str(now.day) + now.strftime(", %Y"), S.stamp(TZ))
            if ann_photos:
                store.add_announcement_photos(a["id"], [(f.name, f.getvalue()) for f in ann_photos])
            st.rerun()
        st.divider()
        for a in store.list_announcements():
            c1, c2 = st.columns([6, 1])
            c1.markdown(f"<div class='post'><div class='when'>{a['posted_date']}</div>"
                        f"<div class='head'>{a['title']}</div>{a['message']}</div>", unsafe_allow_html=True)
            if a.get("photos"):
                pc = c1.columns(4)
                for i, ph in enumerate(a["photos"]):
                    pc[i % 4].image(ph["url"], width="stretch")
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

    with t_album:
        st.caption("Add photos + captions to a child's scrapbook (parents can print it).")
        kmap = {k["name"]: k["id"] for k in enrolled}
        if kmap:
            with st.form("album_add", clear_on_submit=True):
                who = st.selectbox("Child", list(kmap.keys()))
                cap = st.text_input("Caption")
                aphoto = st.file_uploader("Photo", type=["png", "jpg", "jpeg"])
                if st.form_submit_button("📖 Add to scrapbook", type="primary") and aphoto:
                    store.add_album_photo(kmap[who], date_iso, cap.strip(),
                                          aphoto.name, aphoto.getvalue())
                    st.success("Added!")
                    st.rerun()
        else:
            st.write("No enrolled children yet.")
        st.divider()
        for k in enrolled:
            items = store.list_album(k["id"])
            if not items:
                continue
            total = sum(len(it["photos"]) for it in items)
            st.markdown(f"**{k['name']}** — {total} photo(s)")
            cols = st.columns(4)
            i = 0
            for it in items:
                for ph in it["photos"]:
                    with cols[i % 4]:
                        st.image(ph["url"], caption=it.get("caption") or "", width="stretch")
                        if st.button("🗑 Delete", key=f"delalb_{it['id']}"):
                            store.delete_album_photo(it["id"])
                            st.rerun()
                    i += 1


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
    if not k["child_photo"]:
        st.caption("📸 Add a photo below to unlock your child's Student ID card!")
    child_photo_uploader(k, "p")
    with st.form(f"pp_{k['id']}"):
        vals = profile_fields(k, prefix=f"p_{k['id']}_")
        saved = st.form_submit_button("💾 Save my changes", type="primary")
    if saved:
        store.update_kid(k["id"], vals)
        ok, _ = notify.send_email(
            EMAIL_CFG,
            f"[Tot Spot] {k['name']}'s profile was updated",
            f"{k['name']}'s family updated their profile in the parent portal "
            f"at {S.stamp(TZ)}.\n\nOpen Admin → Children to review.",
        )
        st.success("Saved! " + ("Mrs. Y has been notified. 💌" if ok else "Thanks!"))
        st.rerun()


def _chips(items, cls=""):
    if not items:
        return "<span class='chip'>—</span>"
    return "".join(f"<span class='chip {cls}'>{x}</span>" for x in items)


def daily_report_html(log: dict, title: str) -> str:
    pt = (log.get("potty_type") or []) + (log.get("potty_progress") or [])
    parts = [f"<div class='rep'><h4>{title}</h4>",
             "<div class='lbl'>Potty</div>", _chips(pt, "potty"),
             "<div class='lbl'>Snack</div>",
             f"<span class='chip snack'>{log.get('snack') or '—'}</span>",
             "<div class='lbl'>Mood</div>", _chips(log.get("mood") or [], "mood")]
    if log.get("behavior"):
        parts.append(f"<div style='margin-top:.3rem'>{log['behavior']}</div>")
    if log.get("injury"):
        parts.append(f"<div class='lbl'>Injury note</div><div>{log['injury']}</div>")
    parts.append("</div>")
    return "".join(parts)


def render_parent_daily(kids: list[dict]):
    now = S.now_local(TZ)
    today = S.today_iso(TZ)
    for k in kids:
        st.markdown(f"#### 📋 {k['name']}")
        log = store.get_daily_log(k["id"], today)
        if log:
            st.markdown(daily_report_html(log, "Today · " + now.strftime("%b ") + str(now.day)),
                        unsafe_allow_html=True)
        else:
            st.caption("No report posted yet today.")
        history = [lg for lg in store.list_daily_logs(k["id"]) if lg["date"] != today]
        if history:
            with st.expander("Past days"):
                for lg in history[:20]:
                    st.markdown(daily_report_html(lg, lg["date"]), unsafe_allow_html=True)


def render_news(my_cohorts: set):
    st.markdown("### 📣 Announcements")
    anns = store.list_announcements()
    if not anns:
        st.caption("No announcements right now.")
    for a in anns[:10]:
        st.markdown(f"<div class='post'><div class='when'>{a['posted_date']}</div>"
                    f"<div class='head'>{a['title']}</div>{a['message']}</div>", unsafe_allow_html=True)
        if a.get("photos"):
            pcols = st.columns(4)
            for i, ph in enumerate(a["photos"]):
                pcols[i % 4].image(ph["url"], width="stretch")
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


def render_scrapbook(kids: list[dict]):
    st.caption("💡 To save/print: use your browser's Print → Save as PDF "
               "(on iPad: Share → Print). Stay on this tab when you print.")
    logo_tag = f"<img src='{LOGO_URI}'/>" if LOGO_URI else ""
    for k in kids:
        items = store.list_album(k["id"])
        if not items:
            st.info(f"No scrapbook photos yet for {k['name']}. Mrs. Y adds these!")
            continue
        cards = ""
        for it in items:
            for ph in it["photos"]:
                cap = it.get("caption") or ""
                cards += f"<div class='sb-card'><img src='{ph['url']}'/><div class='sb-cap'>{cap}</div></div>"
        st.markdown(
            f"<div class='scrapbook'><div class='sb-title'>{k['name']}'s Scrapbook 🌈</div>"
            f"<div class='sb-grid'>{cards}</div>"
            f"<div class='sb-foot'><span>The Tot Spot</span>{logo_tag}</div></div>",
            unsafe_allow_html=True)


def view_parent():
    st.markdown(css(), unsafe_allow_html=True)
    logo_header()
    banner()
    # Layer 1 — log in (email + password) or register (with child's code)
    if not st.session_state.get("parent_authed"):
        st.markdown("<div class='subtitle'>Family Portal 🌈</div>", unsafe_allow_html=True)
        cols = st.columns([1, 2, 1])
        with cols[1]:
            tab_login, tab_reg = st.tabs(["Log in", "Register"])
            with tab_login:
                if not _locked("plogin"):
                    with st.form("login_form"):
                        email = st.text_input("Email",
                                              help="Tip: let your browser save your login for next time.")
                        pw = st.text_input("Password", type="password")
                        do_login = st.form_submit_button("Log in", type="primary", width="stretch")
                    if do_login:
                        if authenticate(email, pw):
                            _reset_fails("plogin")
                            st.session_state.parent_authed = True
                            st.session_state.parent_login_email = email.strip().lower()
                            st.rerun()
                        else:
                            _record_fail("plogin")
                            st.error("Email or password not recognized. Check with Mrs. Y.")
            with tab_reg:
                st.caption("First time? Use your child's 6-digit code to set up your login.")
                with st.form("register_form"):
                    rcode = st.text_input("Child's 6-digit code", max_chars=PIN_LEN)
                    remail = st.text_input("Your email")
                    rpw = st.text_input("Create a password", type="password")
                    rpw2 = st.text_input("Confirm password", type="password")
                    do_reg = st.form_submit_button("Create login", type="primary", width="stretch")
                if do_reg:
                    matches = enrolled_by_pin(rcode.strip())
                    if not matches:
                        st.error("That code didn't match a child. Please check with Mrs. Y.")
                    elif any((k.get("login_password") or "") for k in matches):
                        st.error("This child is already registered. Use **Forgot password?** "
                                 "below if you need to reset it.")
                    elif not remail.strip() or not rpw:
                        st.error("Please enter your email and a password.")
                    elif rpw != rpw2:
                        st.error("The passwords don't match.")
                    else:
                        for k in matches:
                            store.update_kid(k["id"], {"login_email": remail.strip().lower(),
                                                       "login_password": rpw})
                        st.success("Login created! Switch to the **Log in** tab to sign in. 🎉")

            with st.expander("Forgot password?"):
                with st.form("forgot_form"):
                    femail = st.text_input("Your registered email")
                    if st.form_submit_button("Email me a reset link"):
                        targets = [k for k in kids_for_login(femail) if (k.get("login_password") or "")]
                        if targets:
                            token = uuid.uuid4().hex
                            expires = (S.now_local(TZ) + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
                            for k in targets:
                                store.update_kid(k["id"], {"reset_token": token, "reset_expires": expires})
                            link = f"{APP_URL}/?view=reset&token={token}"
                            notify.send_email(
                                EMAIL_CFG, "Reset your Tot Spot password",
                                f"Hi! Someone requested a password reset for your Tot Spot login.\n\n"
                                f"Click this link (valid for 1 hour) to set a new password:\n{link}\n\n"
                                f"If you didn't request this, you can ignore this email.",
                                to=femail.strip())
                        st.success("If that email is registered, we've sent a reset link. "
                                   "Check your inbox (and spam).")
            security_reminder()
        return

    kids = kids_for_login(st.session_state.get("parent_login_email", ""))
    if not kids:
        st.error("No enrolled children found for this login. Please contact Mrs. Y.")
        if st.button("Log out"):
            _parent_logout()
            st.rerun()
        return

    # Layer 2 — 6-digit family code
    if not st.session_state.get("parent_pin"):
        st.markdown("<div class='subtitle'>Enter your 6-digit family code to unlock 🔒</div>",
                    unsafe_allow_html=True)
        cols = st.columns([1, 2, 1])
        with cols[1]:
            if not _locked("pcode"):
                with st.form("code_form"):
                    entered = st.text_input("6-digit code", max_chars=PIN_LEN)
                    do_unlock = st.form_submit_button("Unlock", type="primary", width="stretch")
                if do_unlock and entered.strip():
                    if entered.strip() in {k.get("pin") for k in kids}:
                        _reset_fails("pcode")
                        st.session_state.parent_pin = entered.strip()
                        st.rerun()
                    else:
                        _record_fail("pcode")
                        st.error("That code didn't match. Double-check with Mrs. Y.")
            security_reminder()
            if st.button("Log out", key="logout_code"):
                _parent_logout()
                st.rerun()
        return

    names = ", ".join(k["name"] for k in kids)
    my_cohorts = {k["cohort"] for k in kids if k["cohort"]}
    st.markdown(f"<div class='subtitle'>Welcome, family of {names}! 👋</div>", unsafe_allow_html=True)

    t_home, t_daily, t_news, t_profile, t_book, t_contact = st.tabs(
        ["🏠 Home", "📋 Daily Report", "📣 News", "🪪 Profile", "📖 Scrapbook", "📇 Contact"]
    )
    with t_home:
        for k in kids:
            if k["child_photo"]:
                st.markdown(id_card_html(k, S.now_local(TZ)), unsafe_allow_html=True)
        st.markdown("#### Today at a glance")
        render_parent_daily(kids)
    with t_daily:
        render_parent_daily(kids)
    with t_news:
        render_news(my_cohorts)
    with t_profile:
        for k in kids:
            parent_profile_form(k)
    with t_book:
        render_scrapbook(kids)
    with t_contact:
        contact_and_handbook()
        if st.button("Sign out"):
            _parent_logout()
            st.rerun()


# ------------------------------------------------------------------ HOME
def _reset_valid(k) -> bool:
    exp = k.get("reset_expires") or ""
    if not exp:
        return False
    try:
        dt = datetime.strptime(exp, "%Y-%m-%d %H:%M:%S")
        return S.now_local(TZ).replace(tzinfo=None) < dt
    except Exception:
        return False


def view_reset():
    st.markdown(css(), unsafe_allow_html=True)
    logo_header()
    st.markdown("<div class='subtitle'>Reset your password 🔒</div>", unsafe_allow_html=True)
    cols = st.columns([1, 2, 1])
    with cols[1]:
        token = st.query_params.get("token", "")
        kids = [k for k in store.list_kids()
                if token and (k.get("reset_token") or "") == token and _reset_valid(k)]
        if not kids:
            st.error("This reset link is invalid or has expired. "
                     "Please request a new one from the login page.")
            st.link_button("🔑 Back to login", f"{APP_URL}/?view=parent", width="stretch")
            return
        with st.form("reset_form"):
            npw = st.text_input("New password", type="password")
            npw2 = st.text_input("Confirm new password", type="password")
            done = st.form_submit_button("Set new password", type="primary", width="stretch")
        if done:
            if not npw:
                st.error("Please enter a new password.")
            elif npw != npw2:
                st.error("The passwords don't match.")
            else:
                for k in kids:
                    store.update_kid(k["id"], {"login_password": npw,
                                               "reset_token": "", "reset_expires": ""})
                st.success("Password updated! 🎉 Tap below to log in with your new password.")
        st.link_button("🔑 Back to login", f"{APP_URL}/?view=parent", width="stretch")
        security_reminder()


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
    "parent": view_parent, "reset": view_reset, "home": view_home,
}
ROUTES.get(st.query_params.get("view", "home"), view_home)()
