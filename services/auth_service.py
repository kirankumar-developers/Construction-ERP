import logging
from datetime import datetime
from bson import ObjectId
from database.mongodb import get_db
from utils.helpers import hash_password, check_password, to_object_id, generate_employee_id, generate_labor_id
from utils.constants import Roles

logger = logging.getLogger(__name__)

def register_user(name, email, password, role, is_active=True, company_id=None):
    """
    Creates a base user record.
    """
    db = get_db()
    existing_user = db.users.find_one({'email': email.lower()})
    if existing_user:
        return None, "Email is already registered."
        
    pw_hash = hash_password(password)
    user_doc = {
        'name': name,
        'email': email.lower(),
        'password_hash': pw_hash,
        'role': role,
        'company_id': to_object_id(company_id),
        'is_active': is_active,
        'created_at': datetime.utcnow(),
        'updated_at': datetime.utcnow()
    }
    
    result = db.users.insert_one(user_doc)
    user_doc['_id'] = result.inserted_id
    return user_doc, None

def register_employee(name, email, password, role, department, designation, phone, address, company_id=None):
    db = get_db()
    user, err = register_user(name, email, password, role, company_id=company_id)
    if err:
        return None, err
        
    emp_id = generate_employee_id()
    employee_doc = {
        'user_id': user['_id'],
        'employee_id': emp_id,
        'department': department,
        'designation': designation,
        'phone': phone,
        'address': address,
        'current_status': 'active',
        'created_at': datetime.utcnow()
    }
    db.employees.insert_one(employee_doc)
    return user, None

def register_client(name, email, password, company_name, phone, address, gst_details=None, company_id=None):
    db = get_db()
    user, err = register_user(name, email, password, Roles.CLIENT, company_id=company_id)
    if err:
        return None, err
        
    client_doc = {
        'user_id': user['_id'],
        'client_name': name,
        'company_name': company_name,
        'email': email.lower(),
        'phone': phone,
        'address': address,
        'gst_details': gst_details or '',
        'created_at': datetime.utcnow()
    }
    db.clients.insert_one(client_doc)
    return user, None

def register_vendor_profile(name, email, password, company_name, phone, address, gst_details=None, categories=None, company_id=None):
    db = get_db()
    user, err = register_user(name, email, password, Roles.VENDOR, company_id=company_id)
    if err:
        return None, err
        
    vendor_doc = {
        'user_id': user['_id'],
        'company_name': company_name,
        'contact_person': name,
        'email': email.lower(),
        'phone': phone,
        'address': address,
        'gst_details': gst_details or '',
        'categories': categories or [],
        'outstanding_amount': 0.0,
        'created_at': datetime.utcnow()
    }
    db.vendors.insert_one(vendor_doc)
    return user, None

def register_subcontractor_profile(name, email, password, company_name, phone, address, work_category, contract_value=0.0, company_id=None):
    db = get_db()
    user, err = register_user(name, email, password, Roles.SUBCONTRACTOR, company_id=company_id)
    if err:
        return None, err
        
    subcon_doc = {
        'user_id': user['_id'],
        'company_name': company_name,
        'contact_person': name,
        'email': email.lower(),
        'phone': phone,
        'address': address,
        'work_category': work_category,
        'contract_value': float(contract_value),
        'created_at': datetime.utcnow()
    }
    db.subcontractors.insert_one(subcon_doc)
    return user, None

def register_labour_profile(name, email, password, category, daily_wage, project_id=None, site_id=None, company_id=None):
    db = get_db()
    user, err = register_user(name, email, password, Roles.LABOUR, company_id=company_id)
    if err:
        return None, err
        
    labour_id = generate_labor_id()
    labour_doc = {
        'user_id': user['_id'],
        'labour_id': labour_id,
        'name': name,
        'category': category,
        'project_id': to_object_id(project_id),
        'site_id': to_object_id(site_id),
        'daily_wage': float(daily_wage),
        'status': 'active',
        'created_at': datetime.utcnow()
    }
    db.labours.insert_one(labour_doc)
    return user, None

def login_user(email, password):
    db = get_db()
    user = db.users.find_one({'email': email.lower()})
    
    if not user:
        return None, "Invalid email or password."
        
    if not user.get('is_active', True):
        return None, "Your account has been deactivated. Please contact the administrator."
        
    if not check_password(user['password_hash'], password):
        return None, "Invalid email or password."
        
    return user, None

def get_user_by_id(user_id):
    db = get_db()
    oid = to_object_id(user_id)
    if not oid:
        return None
    return db.users.find_one({'_id': oid})

def get_employee_by_user_id(user_id):
    db = get_db()
    oid = to_object_id(user_id)
    if not oid:
        return None
    return db.employees.find_one({'user_id': oid})

def get_client_by_user_id(user_id):
    db = get_db()
    oid = to_object_id(user_id)
    if not oid:
        return None
    return db.clients.find_one({'user_id': oid})

def get_vendor_by_user_id(user_id):
    db = get_db()
    oid = to_object_id(user_id)
    if not oid:
        return None
    return db.vendors.find_one({'user_id': oid})

def get_subcontractor_by_user_id(user_id):
    db = get_db()
    oid = to_object_id(user_id)
    if not oid:
        return None
    return db.subcontractors.find_one({'user_id': oid})

def get_labour_by_user_id(user_id):
    db = get_db()
    oid = to_object_id(user_id)
    if not oid:
        return None
    return db.labours.find_one({'user_id': oid})

def get_user_profile(user_id, role):
    if role in [Roles.SUPER_ADMIN, Roles.ADMIN, Roles.PROJECT_MANAGER, Roles.SITE_ENGINEER, Roles.SUPERVISOR, Roles.EMPLOYEE]:
        return get_employee_by_user_id(user_id)
    elif role == Roles.CLIENT:
        return get_client_by_user_id(user_id)
    elif role == Roles.VENDOR:
        return get_vendor_by_user_id(user_id)
    elif role == Roles.SUBCONTRACTOR:
        return get_subcontractor_by_user_id(user_id)
    elif role == Roles.LABOUR:
        return get_labour_by_user_id(user_id)
    return None

def get_all_users():
    db = get_db()
    return list(db.users.find())
