"""Data layer for The Tot Spot.

Two interchangeable backends:
  - LocalStore    : a JSON file on disk (+ data/uploads for attachments).
                    Used automatically when no Airtable credentials are set.
  - AirtableStore : the real thing. Used when [airtable] secrets are present.

Above this layer, app.py only sees plain dicts. Attachments are represented as
lists of {"filename": str, "url": str} (Airtable temp URLs, or local paths).
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

# On corporate networks that do TLS inspection (e.g. Cox), Python must trust the
# OS certificate store rather than its bundled certs. truststore makes the whole
# process (including pyairtable's requests calls) use the Windows trust store.
# Harmless off-network, so we always try it.
try:
    import truststore

    truststore.inject_into_ssl()
except Exception:
    pass

# --- Table + field names, kept in one place so base and app agree ------------
KIDS_TABLE = "Kids"
CHECKINS_TABLE = "Check-Ins"
ANNOUNCEMENTS_TABLE = "Announcements"
UPDATES_TABLE = "Daily Updates"
LOGS_TABLE = "Daily Logs"
ALBUM_TABLE = "Album"

# Daily-log field names + option lists (shared with the app UI)
LOG_FIELDS = {
    "date": "Date", "kid_id": "Child ID", "potty_type": "Potty Type",
    "potty_progress": "Potty Progress", "snack": "Snack", "injury": "Injury",
    "mood": "Mood", "behavior": "Behavior Notes",
}
POTTY_TYPE = ["Pee", "Poo"]
POTTY_PROGRESS = ["Toilet independently", "Tried", "Accident",
                  "Wet diaper change", "BM diaper change"]
SNACK = ["Ate all", "Ate some", "Ate none"]
MOOD = ["Happy", "Calm", "Sad", "Tired", "Fussy", "Not feeling well"]

KID_FIELDS = {
    "name": "Child Name",
    "birthdate": "Birthdate",
    "parent_name": "Parent Name",
    "phone": "Parent Phone",
    "email": "Parent Email",
    "notes": "Notes/Allergies",
    "status": "Status",
    "signup_date": "Signup Date",
    "address": "Address",
    "mother_name": "Mother Name",
    "mother_phone": "Mother Phone",
    "father_name": "Father Name",
    "father_phone": "Father Phone",
    "emergency1": "Emergency Contact 1",
    "emergency1_phone": "Emergency Phone 1",
    "emergency2": "Emergency Contact 2",
    "emergency2_phone": "Emergency Phone 2",
    "cohort": "Cohort",
    "photo_social": "Photo Social Media OK",
    "photo_blur": "Photo Blur Face",
    "physician": "Physician Name",
    "physician_phone": "Physician Phone",
    "hospital": "Hospital",
    "hospital_phone": "Hospital Phone",
    "insurance": "Insurance",
    "policy_number": "Policy Number",
    "family_code": "Family Code",
    "medications": "Medications",
    "authorized_pickups": "Authorized Pickups",
    "pin": "PIN",
    "gender": "Gender",
    "school_year": "School Year",
    "parent2_name": "Parent 2 Name",
    "parent2_phone": "Parent 2 Phone",
    "parent2_email": "Parent 2 Email",
    "login_password": "Login Password",
    "login_email": "Login Email",
    "reset_token": "Reset Token",
    "reset_expires": "Reset Expires",
    "special_needs": "Special Needs",
    "structured_env": "Structured Environment",
    "heard_about": "Heard About Us",
    "heard_about_detail": "Heard About Detail",
    "anything_else": "Anything Else",
}
KID_ATTACH_FIELD = "Enrollment Form"
KID_PHOTO_FIELD = "Child Photo"

CHECKIN_FIELDS = {
    "kid_id": "Child",
    "date": "Date",
    "check_in": "Check-In Time",
    "check_out": "Check-Out Time",
}


# --- Time helpers -------------------------------------------------------------
def now_local(tz: str) -> datetime:
    return datetime.now(ZoneInfo(tz))


def today_iso(tz: str) -> str:
    return now_local(tz).strftime("%Y-%m-%d")


def time_str(tz: str) -> str:
    return now_local(tz).strftime("%I:%M %p").lstrip("0")


def stamp(tz: str) -> str:
    """Sortable timestamp string, e.g. '2026-07-17 09:02'."""
    return now_local(tz).strftime("%Y-%m-%d %H:%M")


def new_family_code() -> str:
    """A short, human-friendly family code (no ambiguous chars)."""
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    raw = uuid.uuid4().int
    out = []
    for _ in range(6):
        out.append(alphabet[raw % len(alphabet)])
        raw //= len(alphabet)
    return "".join(out)


def new_pin(existing: set[str]) -> str:
    """A 6-digit code not already in `existing`."""
    for _ in range(200000):
        pin = f"{uuid.uuid4().int % 1000000:06d}"
        if pin not in existing:
            return pin
    return "000000"


# ============================================================ LOCAL BACKEND
class LocalStore:
    """Persists to a single JSON file. Attachments saved under data/uploads."""

    def __init__(self, path: str = "data/local_db.json"):
        self.path = Path(path)
        self.uploads = self.path.parent / "uploads"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.uploads.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write({"kids": [], "checkins": [], "announcements": [], "updates": []})

    def _read(self) -> dict:
        db = json.loads(self.path.read_text(encoding="utf-8"))
        for key in ("kids", "checkins", "announcements", "updates", "daily_logs", "album"):
            db.setdefault(key, [])
        return db

    def _write(self, db: dict) -> None:
        self.path.write_text(json.dumps(db, indent=2), encoding="utf-8")

    def _save_file(self, filename: str, content: bytes) -> dict:
        safe = f"{uuid.uuid4().hex}_{filename}"
        dest = self.uploads / safe
        dest.write_bytes(content)
        return {"filename": filename, "url": str(dest)}

    # kids
    def list_kids(self) -> list[dict]:
        return sorted(self._read()["kids"], key=lambda k: k.get("signup_date", ""))

    def add_kid(self, data: dict) -> dict:
        db = self._read()
        kid = {"id": str(uuid.uuid4()), "enrollment_form": [], "child_photo": [], **data}
        db["kids"].append(kid)
        self._write(db)
        return kid

    def update_kid_status(self, kid_id: str, status: str) -> None:
        self.update_kid(kid_id, {"status": status})

    def update_kid(self, kid_id: str, data: dict) -> None:
        db = self._read()
        for k in db["kids"]:
            if k["id"] == kid_id:
                k.update(data)
        self._write(db)

    def delete_kid(self, kid_id: str) -> None:
        db = self._read()
        db["kids"] = [k for k in db["kids"] if k["id"] != kid_id]
        db["checkins"] = [c for c in db["checkins"] if c.get("kid_id") != kid_id]
        self._write(db)

    def upload_enrollment_form(self, kid_id: str, filename: str, content: bytes) -> None:
        self._append_attachment(kid_id, "enrollment_form", filename, content)

    def set_child_photo(self, kid_id: str, filename: str, content: bytes) -> None:
        # a child has one photo — replace any existing
        att = self._save_file(filename, content)
        db = self._read()
        for k in db["kids"]:
            if k["id"] == kid_id:
                k["child_photo"] = [att]
        self._write(db)

    def _append_attachment(self, kid_id: str, key: str, filename: str, content: bytes) -> None:
        att = self._save_file(filename, content)
        db = self._read()
        for k in db["kids"]:
            if k["id"] == kid_id:
                k.setdefault(key, []).append(att)
        self._write(db)

    # check-ins
    def list_checkins_for_date(self, date_iso: str) -> list[dict]:
        return [c for c in self._read()["checkins"] if c.get("date") == date_iso]

    def add_checkin(self, kid_id: str, date_iso: str, tstr: str) -> dict:
        db = self._read()
        rec = {"id": str(uuid.uuid4()), "kid_id": kid_id, "date": date_iso,
               "check_in": tstr, "check_out": ""}
        db["checkins"].append(rec)
        self._write(db)
        return rec

    def set_checkout(self, checkin_id: str, tstr: str) -> None:
        db = self._read()
        for c in db["checkins"]:
            if c["id"] == checkin_id:
                c["check_out"] = tstr
        self._write(db)

    # announcements
    def list_announcements(self) -> list[dict]:
        return sorted(self._read()["announcements"],
                      key=lambda a: a.get("created", ""), reverse=True)

    def add_announcement(self, title: str, message: str, posted_date: str, created: str) -> dict:
        db = self._read()
        rec = {"id": str(uuid.uuid4()), "title": title, "message": message,
               "posted_date": posted_date, "created": created, "photos": []}
        db["announcements"].append(rec)
        self._write(db)
        return rec

    def add_announcement_photos(self, ann_id: str, files: list[tuple[str, bytes]]) -> None:
        db = self._read()
        for a in db["announcements"]:
            if a["id"] == ann_id:
                for filename, content in files:
                    a.setdefault("photos", []).append(self._save_file(filename, content))
        self._write(db)

    def delete_announcement(self, ann_id: str) -> None:
        db = self._read()
        db["announcements"] = [a for a in db["announcements"] if a["id"] != ann_id]
        self._write(db)

    # daily updates
    def list_updates(self) -> list[dict]:
        return sorted(self._read()["updates"], key=lambda u: u.get("date", ""), reverse=True)

    def add_update(self, date_iso: str, note: str, cohort: str) -> dict:
        db = self._read()
        rec = {"id": str(uuid.uuid4()), "date": date_iso, "note": note,
               "cohort": cohort, "photos": []}
        db["updates"].append(rec)
        self._write(db)
        return rec

    def add_update_photos(self, update_id: str, files: list[tuple[str, bytes]]) -> None:
        db = self._read()
        for u in db["updates"]:
            if u["id"] == update_id:
                for filename, content in files:
                    u.setdefault("photos", []).append(self._save_file(filename, content))
        self._write(db)

    # daily logs (per child, per day)
    def get_daily_log(self, kid_id: str, date_iso: str):
        for lg in self._read()["daily_logs"]:
            if lg["kid_id"] == kid_id and lg["date"] == date_iso:
                return lg
        return None

    def upsert_daily_log(self, kid_id: str, date_iso: str, data: dict) -> dict:
        db = self._read()
        for lg in db["daily_logs"]:
            if lg["kid_id"] == kid_id and lg["date"] == date_iso:
                lg.update(data)
                self._write(db)
                return lg
        rec = {"id": str(uuid.uuid4()), "kid_id": kid_id, "date": date_iso, **data}
        db["daily_logs"].append(rec)
        self._write(db)
        return rec

    def list_daily_logs(self, kid_id: str) -> list[dict]:
        logs = [lg for lg in self._read()["daily_logs"] if lg["kid_id"] == kid_id]
        return sorted(logs, key=lambda lg: lg.get("date", ""), reverse=True)

    # album / scrapbook
    def add_album_photo(self, kid_id: str, date_iso: str, caption: str,
                        filename: str, content: bytes) -> dict:
        db = self._read()
        rec = {"id": str(uuid.uuid4()), "kid_id": kid_id, "date": date_iso,
               "caption": caption, "photos": [self._save_file(filename, content)]}
        db["album"].append(rec)
        self._write(db)
        return rec

    def list_album(self, kid_id: str) -> list[dict]:
        items = [a for a in self._read()["album"] if a["kid_id"] == kid_id]
        return sorted(items, key=lambda a: a.get("date", ""), reverse=True)

    def delete_album_photo(self, item_id: str) -> None:
        db = self._read()
        db["album"] = [a for a in db["album"] if a["id"] != item_id]
        self._write(db)


# ============================================================ AIRTABLE BACKEND
class AirtableStore:
    def __init__(self, token: str, base_id: str):
        from pyairtable import Api

        # Fail fast instead of hanging: when Airtable is rate-limited or over its
        # monthly cap it returns 429, and pyairtable's default retry backs off for
        # many seconds per call — which freezes the whole app. Retry at most once,
        # briefly (and only for safe/idempotent methods, so writes aren't doubled),
        # with a hard timeout.
        try:
            from urllib3.util.retry import Retry
            _retry = Retry(total=1, backoff_factor=0.3,
                           status_forcelist=(429, 500, 502, 503, 504))
            api = Api(token, retry_strategy=_retry, timeout=(5, 20))
        except TypeError:
            try:
                api = Api(token, timeout=(5, 20))
            except TypeError:
                api = Api(token)
        self.kids = api.table(base_id, KIDS_TABLE)
        self.checkins = api.table(base_id, CHECKINS_TABLE)
        self.announcements = api.table(base_id, ANNOUNCEMENTS_TABLE)
        self.updates = api.table(base_id, UPDATES_TABLE)
        self.logs = api.table(base_id, LOGS_TABLE)
        self.album = api.table(base_id, ALBUM_TABLE)

    @staticmethod
    def _attachments(value) -> list[dict]:
        out = []
        for a in value or []:
            out.append({"filename": a.get("filename", ""), "url": a.get("url", "")})
        return out

    @classmethod
    def _kid_from_record(cls, rec: dict) -> dict:
        f = {k.strip(): v for k, v in rec.get("fields", {}).items()}
        kid = {"id": rec["id"]}
        for key, col in KID_FIELDS.items():
            kid[key] = f.get(col, "")
        kid["status"] = kid["status"] or "Waitlist"
        kid["enrollment_form"] = cls._attachments(f.get(KID_ATTACH_FIELD, []))
        kid["child_photo"] = cls._attachments(f.get(KID_PHOTO_FIELD, []))
        return kid

    @staticmethod
    def _checkin_from_record(rec: dict) -> dict:
        f = {k.strip(): v for k, v in rec.get("fields", {}).items()}
        linked = f.get(CHECKIN_FIELDS["kid_id"], [])
        return {
            "id": rec["id"],
            "kid_id": linked[0] if linked else "",
            "date": f.get(CHECKIN_FIELDS["date"], ""),
            "check_in": f.get(CHECKIN_FIELDS["check_in"], ""),
            "check_out": f.get(CHECKIN_FIELDS["check_out"], ""),
        }

    # kids
    def list_kids(self) -> list[dict]:
        recs = self.kids.all(sort=[KID_FIELDS["signup_date"]])
        return [self._kid_from_record(r) for r in recs]

    def add_kid(self, data: dict) -> dict:
        payload = {KID_FIELDS[k]: v for k, v in data.items()
                   if k in KID_FIELDS and v not in (None, "")}
        return self._kid_from_record(self.kids.create(payload, typecast=True))

    def update_kid_status(self, kid_id: str, status: str) -> None:
        self.kids.update(kid_id, {KID_FIELDS["status"]: status})

    def update_kid(self, kid_id: str, data: dict) -> None:
        payload = {KID_FIELDS[k]: v for k, v in data.items() if k in KID_FIELDS}
        self.kids.update(kid_id, payload, typecast=True)

    def delete_kid(self, kid_id: str) -> None:
        self.kids.delete(kid_id)

    def upload_enrollment_form(self, kid_id: str, filename: str, content: bytes) -> None:
        self.kids.upload_attachment(kid_id, KID_ATTACH_FIELD, filename=filename, content=content)

    def set_child_photo(self, kid_id: str, filename: str, content: bytes) -> None:
        self.kids.update(kid_id, {KID_PHOTO_FIELD: []})  # replace existing photo
        self.kids.upload_attachment(kid_id, KID_PHOTO_FIELD, filename=filename, content=content)

    # check-ins
    def list_checkins_for_date(self, date_iso: str) -> list[dict]:
        formula = "{%s} = '%s'" % (CHECKIN_FIELDS["date"], date_iso)
        return [self._checkin_from_record(r) for r in self.checkins.all(formula=formula)]

    def add_checkin(self, kid_id: str, date_iso: str, tstr: str) -> dict:
        rec = self.checkins.create({
            CHECKIN_FIELDS["kid_id"]: [kid_id],
            CHECKIN_FIELDS["date"]: date_iso,
            CHECKIN_FIELDS["check_in"]: tstr,
        })
        return self._checkin_from_record(rec)

    def set_checkout(self, checkin_id: str, tstr: str) -> None:
        self.checkins.update(checkin_id, {CHECKIN_FIELDS["check_out"]: tstr})

    # announcements
    def list_announcements(self) -> list[dict]:
        recs = self.announcements.all()
        out = [{
            "id": r["id"],
            "title": r["fields"].get("Title", ""),
            "message": r["fields"].get("Message", ""),
            "posted_date": r["fields"].get("Posted Date", ""),
            "created": r.get("createdTime", ""),
            "photos": self._attachments(r["fields"].get("Photos", [])),
        } for r in recs]
        return sorted(out, key=lambda a: a["created"], reverse=True)

    def add_announcement(self, title: str, message: str, posted_date: str, created: str) -> dict:
        rec = self.announcements.create({
            "Title": title, "Message": message, "Posted Date": posted_date,
        })
        return {"id": rec["id"], "title": title, "message": message,
                "posted_date": posted_date, "created": rec.get("createdTime", "")}

    def add_announcement_photos(self, ann_id: str, files: list[tuple[str, bytes]]) -> None:
        for filename, content in files:
            self.announcements.upload_attachment(ann_id, "Photos", filename=filename, content=content)

    def delete_announcement(self, ann_id: str) -> None:
        self.announcements.delete(ann_id)

    # daily updates
    def list_updates(self) -> list[dict]:
        recs = self.updates.all()
        out = [{
            "id": r["id"],
            "date": r["fields"].get("Date", ""),
            "note": r["fields"].get("Note", ""),
            "cohort": r["fields"].get("Cohort", ""),
            "photos": self._attachments(r["fields"].get("Photos", [])),
        } for r in recs]
        return sorted(out, key=lambda u: u["date"], reverse=True)

    def add_update(self, date_iso: str, note: str, cohort: str) -> dict:
        payload = {"Date": date_iso, "Note": note}
        if cohort:
            payload["Cohort"] = cohort
        rec = self.updates.create(payload)
        return {"id": rec["id"], "date": date_iso, "note": note, "cohort": cohort, "photos": []}

    def add_update_photos(self, update_id: str, files: list[tuple[str, bytes]]) -> None:
        for filename, content in files:
            self.updates.upload_attachment(update_id, "Photos", filename=filename, content=content)

    # daily logs (per child, per day)
    @staticmethod
    def _log_from_record(rec: dict) -> dict:
        f = {k.strip(): v for k, v in rec.get("fields", {}).items()}
        return {
            "id": rec["id"],
            "kid_id": f.get(LOG_FIELDS["kid_id"], ""),
            "date": f.get(LOG_FIELDS["date"], ""),
            "potty_type": f.get(LOG_FIELDS["potty_type"], []) or [],
            "potty_progress": f.get(LOG_FIELDS["potty_progress"], []) or [],
            "snack": f.get(LOG_FIELDS["snack"], ""),
            "injury": f.get(LOG_FIELDS["injury"], ""),
            "mood": f.get(LOG_FIELDS["mood"], []) or [],
            "behavior": f.get(LOG_FIELDS["behavior"], ""),
        }

    @staticmethod
    def _log_payload(data: dict) -> dict:
        keys = ("potty_type", "potty_progress", "snack", "injury", "mood", "behavior")
        return {LOG_FIELDS[k]: data[k] for k in keys if k in data}

    def get_daily_log(self, kid_id: str, date_iso: str):
        formula = "AND({%s}='%s',{%s}='%s')" % (
            LOG_FIELDS["kid_id"], kid_id, LOG_FIELDS["date"], date_iso)
        recs = self.logs.all(formula=formula)
        return self._log_from_record(recs[0]) if recs else None

    def upsert_daily_log(self, kid_id: str, date_iso: str, data: dict) -> dict:
        existing = self.get_daily_log(kid_id, date_iso)
        payload = self._log_payload(data)
        if existing:
            self.logs.update(existing["id"], payload, typecast=True)
            return {**existing, **data}
        payload[LOG_FIELDS["kid_id"]] = kid_id
        payload[LOG_FIELDS["date"]] = date_iso
        return self._log_from_record(self.logs.create(payload, typecast=True))

    def list_daily_logs(self, kid_id: str) -> list[dict]:
        recs = self.logs.all(formula="{%s}='%s'" % (LOG_FIELDS["kid_id"], kid_id))
        return sorted([self._log_from_record(r) for r in recs],
                      key=lambda lg: lg["date"], reverse=True)

    # album / scrapbook
    def add_album_photo(self, kid_id: str, date_iso: str, caption: str,
                        filename: str, content: bytes) -> dict:
        rec = self.album.create({"Child ID": kid_id, "Date": date_iso, "Caption": caption})
        self.album.upload_attachment(rec["id"], "Photo", filename=filename, content=content)
        return {"id": rec["id"], "kid_id": kid_id, "date": date_iso, "caption": caption, "photos": []}

    def list_album(self, kid_id: str) -> list[dict]:
        recs = self.album.all(formula="{Child ID}='%s'" % kid_id)
        out = [{
            "id": r["id"], "kid_id": kid_id,
            "date": r["fields"].get("Date", ""),
            "caption": r["fields"].get("Caption", ""),
            "photos": self._attachments(r["fields"].get("Photo", [])),
        } for r in recs]
        return sorted(out, key=lambda a: a["date"], reverse=True)

    def delete_album_photo(self, item_id: str) -> None:
        self.album.delete(item_id)


# --- Backend selection --------------------------------------------------------
def get_store(secrets) -> tuple[object, bool]:
    """Return (store, is_live). Uses Airtable if creds exist, else LocalStore."""
    try:
        at = secrets.get("airtable", None)
    except Exception:
        at = None
    if at and at.get("token") and at.get("base_id"):
        return AirtableStore(at["token"], at["base_id"]), True
    return LocalStore(), False
