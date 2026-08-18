import re
import random
from datetime import datetime
from bson import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
from database.mongodb import get_db

def hash_password(password):
    """
    Hashes a password using Werkzeug's default password hashing (scrypt/pbkdf2).
    """
    return generate_password_hash(password)

def check_password(password_hash, password):
    """
    Checks a password hash against a plain text password.
    """
    if not password_hash or not password:
        return False
    return check_password_hash(password_hash, password)

def to_object_id(id_str):
    """
    Safely converts a string to a BSON ObjectId.
    Returns None if the string is invalid.
    """
    if not id_str:
        return None
    try:
        return ObjectId(id_str)
    except Exception:
        return None

def format_datetime(value, format="%Y-%m-%d %H:%M"):
    """
    Formats a datetime object or string to a human-readable format.
    """
    if not value:
        return ""
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except ValueError:
            return value
    return value.strftime(format)

def generate_project_code():
    db = get_db()
    try:
        count = db.projects.count_documents({})
        return f"PRJ-{datetime.now().strftime('%Y')}-{count + 1:04d}"
    except Exception:
        return f"PRJ-{datetime.now().strftime('%Y')}-{random.randint(1000, 9999)}"

def generate_site_code():
    db = get_db()
    try:
        count = db.sites.count_documents({})
        return f"STE-{count + 1:04d}"
    except Exception:
        return f"STE-{random.randint(1000, 9999)}"

def generate_boq_number():
    db = get_db()
    try:
        count = db.boq.count_documents({})
        return f"BOQ-{datetime.now().strftime('%Y')}-{count + 1:04d}"
    except Exception:
        return f"BOQ-{datetime.now().strftime('%Y')}-{random.randint(1000, 9999)}"

def generate_request_number():
    db = get_db()
    try:
        count = db.material_requests.count_documents({})
        return f"MR-{datetime.now().strftime('%Y')}-{count + 1:04d}"
    except Exception:
        return f"MR-{datetime.now().strftime('%Y')}-{random.randint(1000, 9999)}"

def generate_rfq_number():
    db = get_db()
    try:
        count = db.rfqs.count_documents({})
        return f"RFQ-{datetime.now().strftime('%Y')}-{count + 1:04d}"
    except Exception:
        return f"RFQ-{datetime.now().strftime('%Y')}-{random.randint(1000, 9999)}"

def generate_po_number():
    db = get_db()
    try:
        count = db.purchase_orders.count_documents({})
        return f"PO-{datetime.now().strftime('%Y')}-{count + 1:04d}"
    except Exception:
        return f"PO-{datetime.now().strftime('%Y')}-{random.randint(1000, 9999)}"

def generate_grn_number():
    db = get_db()
    try:
        count = db.grn.count_documents({})
        return f"GRN-{datetime.now().strftime('%Y')}-{count + 1:04d}"
    except Exception:
        return f"GRN-{datetime.now().strftime('%Y')}-{random.randint(1000, 9999)}"

def generate_labor_id():
    db = get_db()
    try:
        count = db.labours.count_documents({})
        return f"LAB-{count + 1001:04d}"
    except Exception:
        return f"LAB-{random.randint(1000, 9999)}"

def generate_employee_id():
    db = get_db()
    try:
        count = db.employees.count_documents({})
        return f"EMP-{count + 1001:04d}"
    except Exception:
        return f"EMP-{random.randint(1000, 9999)}"

def generate_equipment_id():
    db = get_db()
    try:
        count = db.equipment.count_documents({})
        return f"EQP-{count + 1001:04d}"
    except Exception:
        return f"EQP-{random.randint(1000, 9999)}"

def generate_work_order_number():
    db = get_db()
    try:
        count = db.work_orders.count_documents({})
        return f"WO-{datetime.now().strftime('%Y')}-{count + 1:04d}"
    except Exception:
        return f"WO-{datetime.now().strftime('%Y')}-{random.randint(1000, 9999)}"

def generate_invoice_number():
    db = get_db()
    try:
        count = db.invoices.count_documents({})
        return f"INV-{datetime.now().strftime('%Y')}-{count + 1:04d}"
    except Exception:
        return f"INV-{datetime.now().strftime('%Y')}-{random.randint(1000, 9999)}"

def generate_issue_number():
    db = get_db()
    try:
        count = db.issues.count_documents({})
        return f"ISS-{datetime.now().strftime('%Y')}-{count + 1:04d}"
    except Exception:
        return f"ISS-{datetime.now().strftime('%Y')}-{random.randint(1000, 9999)}"

def generate_job_number():
    return f"JOB-{datetime.now().strftime('%Y')}-{random.randint(1000, 9999)}"
