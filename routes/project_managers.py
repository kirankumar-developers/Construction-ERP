import secrets
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, session, abort
from database.mongodb import get_db
from utils.decorators import login_required, role_required, super_admin_required
from utils.constants import Roles
from utils.helpers import to_object_id, hash_password

project_managers_bp = Blueprint('project_managers', __name__, url_prefix='/project-managers')

@project_managers_bp.route('/')
@login_required
@role_required(Roles.SUPER_ADMIN, Roles.ADMIN)
def index():
    db = get_db()
    managers = list(db.users.find({'role': 'project_manager'}))
    
    for m in managers:
        emp = db.employees.find_one({'user_id': m['_id']})
        m['employee_id'] = emp.get('employee_id', 'N/A') if emp else m.get('employee_id', 'N/A')
        m['department'] = emp.get('department', 'N/A') if emp else m.get('department', 'N/A')
        
        # Get assigned projects
        projects = list(db.projects.find({'manager_id': m['_id']}))
        m['assigned_projects'] = projects
        
    return render_template('project_managers/list.html', project_managers=managers)

@project_managers_bp.route('/add', methods=['GET', 'POST'])
@login_required
@role_required(Roles.SUPER_ADMIN, Roles.ADMIN)
def add():
    if request.method == 'POST':
        db = get_db()
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        employee_id = request.form.get('employee_id', '').strip()
        department = request.form.get('department', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        if not name or not email or not password or not confirm_password:
            flash("Full Name, Email, Password, and Confirm Password are required.", "danger")
            return render_template('project_managers/add.html', form=request.form)
            
        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template('project_managers/add.html', form=request.form)
            
        # Check duplicate email
        if db.users.find_one({'email': email}):
            flash("Email already exists.", "danger")
            return render_template('project_managers/add.html', form=request.form)
            
        # Check duplicate employee_id
        if employee_id:
            existing_emp_user = db.users.find_one({'employee_id': employee_id})
            existing_emp_record = db.employees.find_one({'employee_id': employee_id})
            if existing_emp_user or existing_emp_record:
                flash("Employee ID already exists.", "danger")
                return render_template('project_managers/add.html', form=request.form)
                
        password_hash = hash_password(password)
        company_id = session.get('company_id')
        
        # Save to users collection
        user_doc = {
            'name': name,
            'email': email,
            'phone': phone,
            'employee_id': employee_id,
            'department': department,
            'password_hash': password_hash,
            'role': 'project_manager',
            'status': 'active',
            'is_active': True,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        if company_id:
            user_doc['company_id'] = to_object_id(company_id)
            
        result = db.users.insert_one(user_doc)
        user_id = result.inserted_id
        
        # Save corresponding employee profile
        db.employees.insert_one({
            'user_id': user_id,
            'employee_id': employee_id or f"EMP-{datetime.now().strftime('%Y')}-{str(user_id)[-4:]}",
            'department': department or 'General',
            'designation': 'Project Manager',
            'phone': phone,
            'address': '',
            'current_status': 'active',
            'created_at': datetime.utcnow()
        })
        
        flash("Project Manager created successfully!", "success")
        return redirect(url_for('project_managers.index'))
        
    return render_template('project_managers/add.html')

@project_managers_bp.route('/<manager_id>/view')
@login_required
@role_required(Roles.SUPER_ADMIN, Roles.ADMIN)
def view(manager_id):
    db = get_db()
    oid = to_object_id(manager_id)
    if not oid:
        flash("Invalid ID.", "danger")
        return redirect(url_for('project_managers.index'))
        
    manager = db.users.find_one({'_id': oid})
    if not manager:
        flash("Project Manager not found.", "danger")
        return redirect(url_for('project_managers.index'))
        
    emp = db.employees.find_one({'user_id': oid})
    if emp:
        manager['employee_id'] = emp.get('employee_id', manager.get('employee_id', 'N/A'))
        manager['department'] = emp.get('department', manager.get('department', 'N/A'))
        
    projects = list(db.projects.find({'manager_id': oid}))
    
    return render_template('project_managers/view.html', manager=manager, projects=projects)

@project_managers_bp.route('/<manager_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required(Roles.SUPER_ADMIN, Roles.ADMIN)
def edit(manager_id):
    db = get_db()
    oid = to_object_id(manager_id)
    if not oid:
        flash("Invalid ID.", "danger")
        return redirect(url_for('project_managers.index'))
        
    manager = db.users.find_one({'_id': oid})
    if not manager:
        flash("Project Manager not found.", "danger")
        return redirect(url_for('project_managers.index'))
        
    emp = db.employees.find_one({'user_id': oid})
    if emp:
        manager['employee_id'] = emp.get('employee_id', manager.get('employee_id', ''))
        manager['department'] = emp.get('department', manager.get('department', ''))
        
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        employee_id = request.form.get('employee_id', '').strip()
        department = request.form.get('department', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        if not name or not email:
            flash("Full Name and Email are required.", "danger")
            return render_template('project_managers/edit.html', manager=manager)
            
        # Check duplicate email
        if db.users.find_one({'email': email, '_id': {'$ne': oid}}):
            flash("Email already registered by another account.", "danger")
            return render_template('project_managers/edit.html', manager=manager)
            
        # Check duplicate employee_id
        if employee_id:
            existing_emp_user = db.users.find_one({'employee_id': employee_id, '_id': {'$ne': oid}})
            existing_emp_record = db.employees.find_one({'employee_id': employee_id, 'user_id': {'$ne': oid}})
            if existing_emp_user or existing_emp_record:
                flash("Employee ID already registered by another account.", "danger")
                return render_template('project_managers/edit.html', manager=manager)
                
        update_data = {
            'name': name,
            'email': email,
            'phone': phone,
            'employee_id': employee_id,
            'department': department,
            'updated_at': datetime.utcnow()
        }
        
        if password:
            if password != confirm_password:
                flash("Passwords do not match.", "danger")
                return render_template('project_managers/edit.html', manager=manager)
            update_data['password_hash'] = hash_password(password)
            
        db.users.update_one({'_id': oid}, {'$set': update_data})
        
        # Update or insert employee profile
        db.employees.update_one({'user_id': oid}, {'$set': {
            'employee_id': employee_id,
            'department': department,
            'phone': phone
        }}, upsert=True)
        
        flash("Project Manager updated successfully!", "success")
        return redirect(url_for('project_managers.index'))
        
    return render_template('project_managers/edit.html', manager=manager)

@project_managers_bp.route('/<manager_id>/toggle-status', methods=['POST'])
@login_required
@role_required(Roles.SUPER_ADMIN, Roles.ADMIN)
def toggle_status(manager_id):
    db = get_db()
    oid = to_object_id(manager_id)
    if not oid:
        flash("Invalid ID.", "danger")
        return redirect(url_for('project_managers.index'))
        
    manager = db.users.find_one({'_id': oid})
    if not manager:
        flash("Project Manager not found.", "danger")
        return redirect(url_for('project_managers.index'))
        
    new_is_active = not manager.get('is_active', True)
    new_status = 'active' if new_is_active else 'inactive'
    
    db.users.update_one({'_id': oid}, {'$set': {
        'is_active': new_is_active,
        'status': new_status,
        'updated_at': datetime.utcnow()
    }})
    db.employees.update_one({'user_id': oid}, {'$set': {
        'current_status': new_status
    }}, upsert=True)
    
    flash(f"Project Manager {manager['name']} has been {'activated' if new_is_active else 'deactivated'}.", "success")
    return redirect(url_for('project_managers.index'))

@project_managers_bp.route('/<manager_id>/delete', methods=['POST'])
@login_required
@super_admin_required
def delete(manager_id):
    db = get_db()
    oid = to_object_id(manager_id)
    if not oid:
        flash("Invalid ID.", "danger")
        return redirect(url_for('project_managers.index'))
        
    # Check if they are trying to delete their own account
    if str(oid) == session.get('user_id'):
        flash("You cannot delete your own logged-in account.", "danger")
        return redirect(url_for('project_managers.index'))
        
    db.users.delete_one({'_id': oid})
    db.employees.delete_one({'user_id': oid})
    
    flash("Project Manager account deleted successfully.", "success")
    return redirect(url_for('project_managers.index'))

@project_managers_bp.route('/quick-create', methods=['POST'])
@login_required
@role_required(Roles.SUPER_ADMIN, Roles.ADMIN)
def quick_create():
    db = get_db()
    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip().lower()
    phone = request.form.get('phone', '').strip()
    employee_id = request.form.get('employee_id', '').strip()
    department = request.form.get('department', '').strip()
    password = request.form.get('password', '')
    confirm_password = request.form.get('confirm_password', '')
    
    if not name:
        return jsonify({'success': False, 'message': 'Full Name is required'}), 400
    if not email:
        return jsonify({'success': False, 'message': 'Email is required'}), 400
    if not password or not confirm_password:
        return jsonify({'success': False, 'message': 'Password and Confirm Password are required'}), 400
    if password != confirm_password:
        return jsonify({'success': False, 'message': 'Passwords do not match'}), 400
        
    # Check duplicate email
    if db.users.find_one({'email': email}):
        return jsonify({'success': False, 'message': 'Email already exists'}), 400
        
    # Check duplicate employee_id
    if employee_id:
        existing_emp_user = db.users.find_one({'employee_id': employee_id})
        existing_emp_record = db.employees.find_one({'employee_id': employee_id})
        if existing_emp_user or existing_emp_record:
            return jsonify({'success': False, 'message': 'Employee ID already exists'}), 400
            
    password_hash = hash_password(password)
    company_id = session.get('company_id')
    
    user_doc = {
        'name': name,
        'email': email,
        'phone': phone,
        'employee_id': employee_id,
        'department': department,
        'password_hash': password_hash,
        'role': 'project_manager',
        'status': 'active',
        'is_active': True,
        'created_at': datetime.utcnow(),
        'updated_at': datetime.utcnow()
    }
    if company_id:
        user_doc['company_id'] = to_object_id(company_id)
        
    result = db.users.insert_one(user_doc)
    user_id = result.inserted_id
    
    # Save employee record
    db.employees.insert_one({
        'user_id': user_id,
        'employee_id': employee_id or f"EMP-{datetime.now().strftime('%Y')}-{str(user_id)[-4:]}",
        'department': department or 'General',
        'designation': 'Project Manager',
        'phone': phone,
        'address': '',
        'current_status': 'active',
        'created_at': datetime.utcnow()
    })
    
    return jsonify({
        'success': True,
        'message': 'Project Manager created successfully',
        'project_manager': {
            'id': str(user_id),
            'name': name
        }
    })
