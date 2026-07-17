"""Create all Airtable fields/tables needed for profiles, announcements, and
daily updates. Idempotent: skips anything that already exists. Requires the
token to have the schema.bases:write scope."""
import tomllib

try:
    import truststore
    truststore.inject_into_ssl()
except Exception:
    pass

import pyairtable
from pyairtable import Api

print("pyairtable version:", pyairtable.__version__)

with open(".streamlit/secrets.toml", "rb") as f:
    secrets = tomllib.load(f)
at = secrets["airtable"]
api = Api(at["token"])
base = api.base(at["base_id"])

COHORTS = [{"name": "Mon/Wed"}, {"name": "Tues/Thurs"}, {"name": "Full-Time"}]
YESNO = [{"name": "Yes"}, {"name": "No"}]

# --- fields to ensure on the Kids table -------------------------------------
KIDS_NEW_FIELDS = [
    ("Address", "singleLineText", None),
    ("Mother Name", "singleLineText", None),
    ("Mother Phone", "singleLineText", None),
    ("Father Name", "singleLineText", None),
    ("Father Phone", "singleLineText", None),
    ("Emergency Contact 1", "singleLineText", None),
    ("Emergency Phone 1", "singleLineText", None),
    ("Emergency Contact 2", "singleLineText", None),
    ("Emergency Phone 2", "singleLineText", None),
    ("Cohort", "singleSelect", {"choices": COHORTS}),
    ("Photo Social Media OK", "singleSelect", {"choices": YESNO}),
    ("Photo Blur Face", "singleSelect", {"choices": YESNO}),
    ("Physician Name", "singleLineText", None),
    ("Physician Phone", "singleLineText", None),
    ("Hospital", "singleLineText", None),
    ("Hospital Phone", "singleLineText", None),
    ("Insurance", "singleLineText", None),
    ("Policy Number", "singleLineText", None),
    ("Family Code", "singleLineText", None),
    ("Enrollment Form", "multipleAttachments", None),
    ("Medications", "multilineText", None),
    ("Authorized Pickups", "multilineText", None),
    ("Child Photo", "multipleAttachments", None),
    ("PIN", "singleLineText", None),
]

# --- new tables --------------------------------------------------------------
NEW_TABLES = {
    "Announcements": [
        {"name": "Title", "type": "singleLineText"},
        {"name": "Message", "type": "multilineText"},
        {"name": "Posted Date", "type": "singleLineText"},
    ],
    "Daily Updates": [
        {"name": "Date", "type": "singleLineText"},
        {"name": "Note", "type": "multilineText"},
        {"name": "Cohort", "type": "singleSelect",
         "options": {"choices": COHORTS + [{"name": "All"}]}},
        {"name": "Photos", "type": "multipleAttachments"},
    ],
}


def ensure_kids_fields():
    schema = base.schema()
    kids_tbl = None
    for t in schema.tables:
        if t.name == "Kids":
            kids_tbl = t
    if kids_tbl is None:
        print("!! No 'Kids' table found — aborting field creation.")
        return
    existing = {f.name for f in kids_tbl.fields}
    table = base.table(kids_tbl.id)  # schema ops need the table ID, not name
    for name, ftype, options in KIDS_NEW_FIELDS:
        if name in existing:
            print(f"   Kids.{name}: exists, skip")
            continue
        table.create_field(name, ftype, options=options)
        print(f"   Kids.{name}: CREATED ({ftype})")


def ensure_tables():
    existing = {t.name for t in base.schema().tables}
    for name, fields in NEW_TABLES.items():
        if name in existing:
            print(f"   Table {name!r}: exists, skip")
            continue
        base.create_table(name, fields=fields)
        print(f"   Table {name!r}: CREATED")


try:
    print("\nEnsuring Kids fields...")
    ensure_kids_fields()
    print("\nEnsuring new tables...")
    ensure_tables()
    print("\nDONE.")
except Exception as e:
    print("\nERROR:", type(e).__name__, e)
    print("If this mentions permissions/scope, the token still needs "
          "'schema.bases:write'.")
