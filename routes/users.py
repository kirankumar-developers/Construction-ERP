from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, session
from database.mongodb import get_db
from utils.decorators import login_required, super_admin_required, role_required
from utils.constants import Roles
from utils.helpers import to_object_id
from services.auth_service import (
    register_employee, register_client, register_vendor_profile,
    register_subcontractor_profile, register_labour_profile
)
from bson import ObjectId
from datetime import datetime

users_bp = Blueprint('users', __name__, url_prefix='/users')

@users_bp.route('/')
@login_required
@super_admin_required
def index():
    db = get_db()
    users = list(db.users.find())
    return render_template('users/list.html', users=users, Roles=Roles)

@users_bp.route('/create/', methods=['GET', 'POST'])
@login_required
@super_admin_required
def create():
    db = get_db()
    projects = list(db.projects.find())
    sites = list(db.sites.find())
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        role = request.form.get('role')
        
        if not name or not email or not password or not role:
            flash("Name, email, password, and role are required.", "danger")
            return redirect(url_for('users.create'))
            
        try:
            if role in [Roles.SUPER_ADMIN, Roles.ADMIN, Roles.PROJECT_MANAGER, Roles.SITE_ENGINEER, Roles.SUPERVISOR, Roles.EMPLOYEE]:
                dept = request.form.get('department', 'General')
                desg = request.form.get('designation', role.replace('_', ' ').title())
                phone = request.form.get('phone', '')
                addr = request.form.get('address', '')
                _, err = register_employee(name, email, password, role, dept, desg, phone, addr)
                
            elif role == Roles.CLIENT:
                comp = request.form.get('company_name', '')
                phone = request.form.get('phone_client', '')
                addr = request.form.get('address_client', '')
                gst = request.form.get('gst_details', '')
                _, err = register_client(name, email, password, comp, phone, addr, gst)
                
            elif role == Roles.VENDOR:
                comp = request.form.get('company_name_vendor', '')
                phone = request.form.get('phone_vendor', '')
                addr = request.form.get('address_vendor', '')
                gst = request.form.get('gst_details_vendor', '')
                cats = request.form.getlist('categories')
                _, err = register_vendor_profile(name, email, password, comp, phone, addr, gst, cats)
                
            elif role == Roles.SUBCONTRACTOR:
                comp = request.form.get('company_name_sub', '')
                phone = request.form.get('phone_sub', '')
                addr = request.form.get('address_sub', '')
                wcat = request.form.get('work_category', '')
                val = float(request.form.get('contract_value', 0.0) or 0)
                _, err = register_subcontractor_profile(name, email, password, comp, phone, addr, wcat, val)
                
            elif role == Roles.LABOUR:
                cat = request.form.get('category', 'Mason')
                wage = float(request.form.get('daily_wage', 0.0) or 0)
                pid = request.form.get('project_id')
                sid = request.form.get('site_id')
                _, err = register_labour_profile(name, email, password, cat, wage, pid, sid)
            else:
                err = "Invalid role specified."
                
            if err:
                flash(err, "danger")
            else:
                flash("User registered successfully!", "success")
                return redirect(url_for('users.index'))
                
        except Exception as e:
            flash(f"Error registering user: {e}", "danger")
            
    return render_template('users/add.html', projects=projects, sites=sites, Roles=Roles)

@users_bp.route('/<user_id>/edit/', methods=['GET', 'POST'])
@login_required
@super_admin_required
def edit(user_id):
    db = get_db()
    oid = to_object_id(user_id)
    if not oid:
        flash("Invalid user ID.", "danger")
        return redirect(url_for('users.index'))
        
    user = db.users.find_one({'_id': oid})
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for('users.index'))
        
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        role = request.form.get('role')
        
        if not name or not email or not role:
            flash("Name, email, and role are required.", "danger")
            return redirect(url_for('users.edit', user_id=user_id))
            
        update_data = {
            'name': name,
            'email': email,
            'role': role,
            'updated_at': datetime.utcnow()
        }
        
        db.users.update_one({'_id': oid}, {'$set': update_data})
        flash("User details updated successfully!", "success")
        return redirect(url_for('users.index'))
        
    return render_template('users/edit.html', user=user, Roles=Roles)

@users_bp.route('/<user_id>/delete/', methods=['POST'])
@login_required
@super_admin_required
def delete(user_id):
    db = get_db()
    oid = to_object_id(user_id)
    if not oid:
        flash("Invalid user ID.", "danger")
        return redirect(url_for('users.index'))
        
    # Check that they aren't deleting themselves
    if str(oid) == request.cookies.get('user_id') or str(oid) == request.environ.get('session', {}).get('user_id', ''):
        flash("You cannot delete your own logged-in account.", "danger")
        return redirect(url_for('users.index'))
        
    res = db.users.delete_one({'_id': oid})
    if res.deleted_count > 0:
        flash("User account deleted successfully.", "success")
    else:
        flash("Failed to delete user account.", "danger")
        
    return redirect(url_for('users.index'))

@users_bp.route('/<user_id>/toggle/', methods=['POST'])
@login_required
@super_admin_required
def toggle_status(user_id):
    db = get_db()
    oid = to_object_id(user_id)
    if not oid:
        flash("Invalid user ID.", "danger")
        return redirect(url_for('users.index'))
        
    user = db.users.find_one({'_id': oid})
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for('users.index'))
        
    new_status = not user.get('is_active', True)
    db.users.update_one({'_id': oid}, {'$set': {'is_active': new_status, 'updated_at': datetime.utcnow()}})
    
    flash(f"User {user['name']} has been {'activated' if new_status else 'deactivated'}.", "success")
    return redirect(url_for('users.index'))

@users_bp.route('/create-project-manager', methods=['POST'])
@login_required
@super_admin_required
def create_project_manager():
    db = get_db()
    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip().lower()
    phone = request.form.get('phone', '').strip()
    employee_id = request.form.get('employee_id', '').strip()
    department = request.form.get('department', '').strip() or 'General'
    password = request.form.get('password', '')
    confirm_password = request.form.get('confirm_password', '')
    
    if not name or not email or not password or not confirm_password:
        return jsonify({'success': False, 'message': 'Full Name, Email, Password, and Confirm Password are required'}), 400
        
    if password != confirm_password:
        return jsonify({'success': False, 'message': 'Passwords do not match'}), 400
        
    # Check if email is already registered
    existing_user = db.users.find_one({'email': email})
    if existing_user:
        return jsonify({'success': False, 'message': 'Email is already registered'}), 400
        
    company_id = session.get('company_id')
    
    # Register project manager as employee
    user, err = register_employee(
        name=name,
        email=email,
        password=password,
        role=Roles.PROJECT_MANAGER,
        department=department,
        designation='Project Manager',
        phone=phone,
        address='',
        company_id=company_id
    )
    
    if err:
        return jsonify({'success': False, 'message': err}), 400
        
    # If custom employee ID is provided, update it
    if employee_id:
        db.employees.update_one({'user_id': user['_id']}, {'$set': {'employee_id': employee_id}})
        
    return jsonify({
        'success': True,
        'message': 'Project Manager created successfully',
        'project_manager': {
            'id': str(user['_id']),
            'name': name
        }
    })

@users_bp.route('/project-managers/list', methods=['GET'])
@login_required
@role_required(Roles.SUPER_ADMIN, Roles.ADMIN)
def list_project_managers():
    db = get_db()
    managers = list(db.users.find({
        'role': Roles.PROJECT_MANAGER,
        '$or': [
            {'is_active': True},
            {'status': 'active'}
        ]
    }))
    managers_list = []
    for m in managers:
        managers_list.append({
            'id': str(m['_id']),
            'name': m.get('name', '')
        })
    return jsonify({
        'success': True,
        'project_managers': managers_list
    })
