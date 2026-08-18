from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from utils.decorators import role_required
from utils.constants import Roles, JobStatus
from database.mongodb import get_db
from services.auth_service import get_employee_by_user_id
from services.job_service import get_jobs_by_employee, get_job_by_id, update_job_status
from services.attendance_service import check_in_employee, check_out_employee, get_employee_attendance_history
from services.upload_service import upload_file
from utils.helpers import to_object_id
from datetime import datetime

employee_bp = Blueprint('employee', __name__, url_prefix='/employee')

@employee_bp.route('/dashboard')
@role_required(Roles.EMPLOYEE)
def dashboard():
    """
    Employee dashboard. Shows assigned jobs and current check-in state.
    """
    db = get_db()
    emp = get_employee_by_user_id(session['user_id'])
    if not emp:
        flash("Employee profile not found.", "danger")
        return redirect(url_for('auth.login'))
        
    jobs = get_jobs_by_employee(str(emp['_id']))
    
    # Check if currently checked in somewhere
    active_attendance = db.attendance.find_one({
        'employee_id': emp['_id'],
        'check_out_time': None
    })
    
    active_job = None
    if active_attendance:
        active_job = db.jobs.find_one({'_id': active_attendance['job_id']})
        
    return render_template(
        'employee/dashboard.html', 
        jobs=jobs, 
        active_attendance=active_attendance, 
        active_job=active_job
    )

@employee_bp.route('/jobs/<job_id>')
@role_required(Roles.EMPLOYEE)
def job_detail(job_id):
    """
    Displays the details for an assigned job, mapping, check-in options.
    """
    emp = get_employee_by_user_id(session['user_id'])
    if not emp:
        flash("Employee profile not found.", "danger")
        return redirect(url_for('auth.login'))
        
    job = get_job_by_id(job_id)
    if not job:
        flash("Job not found.", "danger")
        return redirect(url_for('employee.dashboard'))
        
    # Check current attendance record for this job
    db = get_db()
    active_attendance = db.attendance.find_one({
        'employee_id': emp['_id'],
        'job_id': to_object_id(job_id),
        'check_out_time': None
    })
    
    return render_template(
        'employee/job_detail.html', 
        job=job, 
        active_attendance=active_attendance,
        employee_id=str(emp['_id'])
    )

@employee_bp.route('/jobs/<job_id>/accept')
@role_required(Roles.EMPLOYEE)
def accept_job(job_id):
    """
    Employee accepts the assigned job.
    """
    db = get_db()
    emp = get_employee_by_user_id(session['user_id'])
    if not emp:
        flash("Employee profile not found.", "danger")
        return redirect(url_for('auth.login'))
        
    jid = to_object_id(job_id)
    
    # Update job assignments status
    db.job_assignments.update_one(
        {'job_id': jid, 'employee_id': emp['_id']},
        {'$set': {'assignment_status': 'accepted'}}
    )
    
    # Update job status
    update_job_status(job_id, JobStatus.ACCEPTED, str(emp['_id']), notes="Job accepted by employee.")
    
    flash("Job status updated to Accepted.", "success")
    return redirect(url_for('employee.job_detail', job_id=job_id))

@employee_bp.route('/jobs/<job_id>/decline')
@role_required(Roles.EMPLOYEE)
def decline_job(job_id):
    """
    Employee declines the job. Re-opens job assignment.
    """
    db = get_db()
    emp = get_employee_by_user_id(session['user_id'])
    if not emp:
        flash("Employee profile not found.", "danger")
        return redirect(url_for('auth.login'))
        
    jid = to_object_id(job_id)
    
    # Update job assignments status
    db.job_assignments.update_one(
        {'job_id': jid, 'employee_id': emp['_id']},
        {'$set': {'assignment_status': 'declined'}}
    )
    
    # Update job status back to PENDING and release employee status
    update_job_status(job_id, JobStatus.PENDING, str(emp['_id']), notes="Job declined by employee.")
    db.employees.update_one({'_id': emp['_id']}, {'$set': {'current_status': 'active'}})
    
    flash("Job declined. Re-routed back to pending jobs.", "info")
    return redirect(url_for('employee.dashboard'))

@employee_bp.route('/jobs/<job_id>/check_in', methods=['POST'])
@role_required(Roles.EMPLOYEE)
def check_in(job_id):
    """
    Logs check-in GPS coordinates and starts job status timer.
    """
    emp = get_employee_by_user_id(session['user_id'])
    if not emp:
        return jsonify({'error': 'Employee profile not found.'}), 404
        
    lat = request.form.get('lat')
    lng = request.form.get('lng')
    address = request.form.get('address', 'Checked-in via Mobile GPS')
    
    success, err = check_in_employee(str(emp['_id']), job_id, lat, lng, address)
    if success:
        flash("Checked in successfully. Work time tracking started.", "success")
        return jsonify({'success': True})
    else:
        return jsonify({'error': err}), 400

@employee_bp.route('/jobs/<job_id>/check_out', methods=['POST'])
@role_required(Roles.EMPLOYEE)
def check_out(job_id):
    """
    Logs check-out GPS coordinates and calculates total duration.
    """
    emp = get_employee_by_user_id(session['user_id'])
    if not emp:
        return jsonify({'error': 'Employee profile not found.'}), 404
        
    lat = request.form.get('lat')
    lng = request.form.get('lng')
    address = request.form.get('address', 'Checked-out via Mobile GPS')
    
    success, err = check_out_employee(str(emp['_id']), job_id, lat, lng, address)
    if success:
        flash("Checked out successfully. Work session saved.", "success")
        return jsonify({'success': True})
    else:
        return jsonify({'error': err}), 400

@employee_bp.route('/jobs/<job_id>/update', methods=['POST'])
@role_required(Roles.EMPLOYEE)
def update_job(job_id):
    """
    Allows employee to upload proof documents and submit updates (notes, status).
    """
    emp = get_employee_by_user_id(session['user_id'])
    if not emp:
        flash("Employee profile not found.", "danger")
        return redirect(url_for('auth.login'))
        
    status = request.form.get('status')
    notes = request.form.get('notes', '').strip()
    files = request.files.getlist('attachments')
    
    attachments = []
    for f in files:
        if f and f.filename:
            url, filename = upload_file(f)
            if url:
                attachments.append({
                    'filename': filename,
                    'url': url,
                    'uploaded_at': datetime.utcnow()
                })
            else:
                flash(f"File upload error: {filename}", "danger")
                
    success, err = update_job_status(
        job_id, 
        status, 
        employee_id_str=str(emp['_id']), 
        notes=notes, 
        attachments=attachments
    )
    
    if success:
        # If job completed, free up employee status
        if status == JobStatus.COMPLETED or status == JobStatus.CANCELLED:
            db = get_db()
            db.employees.update_one({'_id': emp['_id']}, {'$set': {'current_status': 'active'}})
        flash("Job status updated successfully.", "success")
    else:
        flash(err, "danger")
        
    return redirect(url_for('employee.job_detail', job_id=job_id))

@employee_bp.route('/history')
@role_required(Roles.EMPLOYEE)
def history():
    """
    Displays personal attendance and job updates logs history.
    """
    emp = get_employee_by_user_id(session['user_id'])
    if not emp:
        flash("Employee profile not found.", "danger")
        return redirect(url_for('auth.login'))
        
    attendance_records = get_employee_attendance_history(str(emp['_id']))
    return render_template('employee/history.html', attendance=attendance_records)
