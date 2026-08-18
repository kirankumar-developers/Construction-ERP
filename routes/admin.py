from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from utils.decorators import role_required
from utils.constants import Roles
from services.auth_service import (
    get_all_employees, get_all_customers, register_employee, update_employee, delete_employee
)
from services.job_service import get_dashboard_metrics, get_all_jobs
from services.attendance_service import get_all_attendance_history
from services.invoice_service import get_all_invoices
from utils.validators import validate_email, validate_password, validate_phone

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/dashboard')
@role_required(Roles.ADMIN)
def dashboard():
    """
    Renders Admin dashboard stats, charts data, and active check-ins.
    """
    metrics = get_dashboard_metrics()
    jobs = get_all_jobs()
    
    # Extract map locations of active jobs
    map_locations = []
    for j in jobs:
        if j.get('location') and j['location'].get('lat') and j['location'].get('lng'):
            map_locations.append({
                'id': str(j['_id']),
                'job_number': j['job_number'],
                'title': j['title'],
                'lat': j['location']['lat'],
                'lng': j['location']['lng'],
                'status': j['status'],
                'address': j['location']['address']
            })
            
    return render_template('admin/dashboard.html', metrics=metrics, map_locations=map_locations)

@admin_bp.route('/employees', methods=['GET', 'POST'])
@role_required(Roles.ADMIN)
def employees():
    """
    Handles employee directory listing and adding a new employee.
    """
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        department = request.form.get('department', '').strip()
        designation = request.form.get('designation', '').strip()
        phone = request.form.get('phone', '').strip()
        address = request.form.get('address', '').strip()
        
        if not name or not email or not password or not department or not designation or not phone or not address:
            flash("All fields are required to register an employee.", "danger")
            return redirect(url_for('admin.employees'))
            
        # Validations
        is_email_ok, email_err = validate_email(email)
        if not is_email_ok:
            flash(email_err, "danger")
            return redirect(url_for('admin.employees'))
            
        is_pw_ok, pw_err = validate_password(password)
        if not is_pw_ok:
            flash(pw_err, "danger")
            return redirect(url_for('admin.employees'))
            
        is_phone_ok, phone_err = validate_phone(phone)
        if not is_phone_ok:
            flash(phone_err, "danger")
            return redirect(url_for('admin.employees'))
            
        user, err = register_employee(name, email, password, department, designation, phone, address)
        if err:
            flash(err, "danger")
        else:
            flash("Employee registered successfully!", "success")
            
        return redirect(url_for('admin.employees'))
        
    all_employees = get_all_employees()
    return render_template('admin/employees.html', employees=all_employees)

@admin_bp.route('/employees/edit/<emp_id>', methods=['POST'])
@role_required(Roles.ADMIN)
def edit_employee(emp_id):
    """
    Updates employee profile details.
    """
    department = request.form.get('department', '').strip()
    designation = request.form.get('designation', '').strip()
    phone = request.form.get('phone', '').strip()
    address = request.form.get('address', '').strip()
    is_active_str = request.form.get('is_active', 'true')
    is_active = is_active_str.lower() == 'true'
    
    if not department or not designation or not phone or not address:
        flash("All fields are required for updates.", "danger")
        return redirect(url_for('admin.employees'))
        
    is_phone_ok, phone_err = validate_phone(phone)
    if not is_phone_ok:
        flash(phone_err, "danger")
        return redirect(url_for('admin.employees'))
        
    success, err = update_employee(emp_id, department, designation, phone, address, is_active)
    if success:
        flash("Employee details updated successfully.", "success")
    else:
        flash(err, "danger")
        
    return redirect(url_for('admin.employees'))

@admin_bp.route('/employees/delete/<emp_id>')
@role_required(Roles.ADMIN)
def delete_employee_route(emp_id):
    """
    Deactivates an employee's access (logical delete).
    """
    success, err = delete_employee(emp_id)
    if success:
        flash("Employee deactivated successfully.", "success")
    else:
        flash(err, "danger")
    return redirect(url_for('admin.employees'))

@admin_bp.route('/customers')
@role_required(Roles.ADMIN)
def customers():
    """
    Displays the customer directory.
    """
    all_customers = get_all_customers()
    return render_template('admin/customers.html', customers=all_customers)

@admin_bp.route('/reports')
@role_required(Roles.ADMIN)
def reports():
    """
    Renders reports and charts analytics dashboard.
    """
    metrics = get_dashboard_metrics()
    invoices = get_all_invoices()
    
    # Financial aggregate calculation
    total_revenue = 0.0
    pending_invoice_amt = 0.0
    for inv in invoices:
        if inv['status'] == 'paid':
            total_revenue += inv['total']
        elif inv['status'] == 'unpaid':
            pending_invoice_amt += inv['total']
            
    # Fetch historical logs for detailed audit
    attendance_logs = get_all_attendance_history()
    
    return render_template(
        'admin/reports.html', 
        metrics=metrics, 
        total_revenue=total_revenue, 
        pending_invoice_amt=pending_invoice_amt,
        attendance_logs=attendance_logs
    )
