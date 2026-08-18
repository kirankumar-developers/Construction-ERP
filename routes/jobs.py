from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from utils.decorators import role_required, login_required
from utils.constants import Roles, Priority, JobStatus
from services.job_service import (
    create_job, assign_employee_to_job, get_job_by_id, get_all_jobs, update_job_status
)
from services.auth_service import get_all_customers, get_all_employees
from database.mongodb import get_db
from utils.helpers import to_object_id

jobs_bp = Blueprint('jobs', __name__, url_prefix='/jobs')

@jobs_bp.route('/')
@role_required(Roles.ADMIN)
def list_jobs():
    """
    Renders listing of all jobs.
    """
    jobs = get_all_jobs()
    return render_template('jobs/list.html', jobs=jobs)

@jobs_bp.route('/<job_id>')
@login_required
def detail(job_id):
    """
    Renders specific details about a job. Visible to authenticated users.
    """
    job = get_job_by_id(job_id)
    if not job:
        flash("Job not found.", "danger")
        if session.get('role') == Roles.ADMIN:
            return redirect(url_for('jobs.list_jobs'))
        elif session.get('role') == Roles.EMPLOYEE:
            return redirect(url_for('employee.dashboard'))
        else:
            return redirect(url_for('customer.dashboard'))
            
    # Access controls: ensure user is Admin, the assigned Employee, or the Customer who owns it
    user_role = session.get('role')
    user_id = session.get('user_id')
    
    db = get_db()
    if user_role == Roles.CUSTOMER:
        cust = db.customers.find_one({'user_id': to_object_id(user_id)})
        if not cust or job['customer_id'] != cust['_id']:
            flash("Unauthorized access.", "danger")
            return redirect(url_for('customer.dashboard'))
            
    elif user_role == Roles.EMPLOYEE:
        emp = db.employees.find_one({'user_id': to_object_id(user_id)})
        if not emp or not job.get('assignment') or job['assignment']['employee_id'] != emp['_id']:
            flash("Unauthorized access.", "danger")
            return redirect(url_for('employee.dashboard'))
            
    # Gather employees for assignment list (Admin only)
    employees = get_all_employees() if user_role == Roles.ADMIN else []
    
    return render_template('jobs/detail.html', job=job, employees=employees)

@jobs_bp.route('/new', methods=['GET', 'POST'])
@role_required(Roles.ADMIN)
def create():
    """
    Renders job creation page and handles form submissions.
    Can be linked to service_request_id.
    """
    db = get_db()
    req_id = request.args.get('request_id')
    req = None
    if req_id:
        req = db.service_requests.find_one({'_id': to_object_id(req_id)})
        
    if request.method == 'POST':
        customer_id = request.form.get('customer_id')
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        priority = request.form.get('priority', Priority.MEDIUM)
        scheduled_date = request.form.get('scheduled_date')
        due_date = request.form.get('due_date')
        address = request.form.get('address', '').strip()
        lat = request.form.get('lat', 0.0)
        lng = request.form.get('lng', 0.0)
        
        if not customer_id or not title or not description or not address:
            flash("Missing required job details.", "danger")
            return render_template('jobs/create.html', customers=get_all_customers(), request_item=req)
            
        job = create_job(
            session['user_id'], 
            customer_id, 
            title, 
            description, 
            priority, 
            scheduled_date, 
            due_date, 
            address, 
            lat, 
            lng, 
            service_request_id_str=req_id
        )
        
        flash(f"Job {job['job_number']} created successfully.", "success")
        return redirect(url_for('jobs.detail', job_id=str(job['_id'])))
        
    customers = get_all_customers()
    return render_template('jobs/create.html', customers=customers, request_item=req)

@jobs_bp.route('/<job_id>/edit', methods=['GET', 'POST'])
@role_required(Roles.ADMIN)
def edit(job_id):
    """
    Allows Admin to edit job description, priority, schedules.
    """
    job = get_job_by_id(job_id)
    if not job:
        flash("Job not found.", "danger")
        return redirect(url_for('jobs.list_jobs'))
        
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        priority = request.form.get('priority')
        scheduled_date = request.form.get('scheduled_date')
        due_date = request.form.get('due_date')
        address = request.form.get('address', '').strip()
        lat = request.form.get('lat', 0.0)
        lng = request.form.get('lng', 0.0)
        status = request.form.get('status')
        
        if not title or not description or not address:
            flash("Please fill in all required fields.", "danger")
            return render_template('jobs/edit.html', job=job)
            
        # Parse Dates
        try:
            sched_dt = datetime.fromisoformat(scheduled_date) if scheduled_date else job['scheduled_date']
            due_dt = datetime.fromisoformat(due_date) if due_date else job['due_date']
        except Exception:
            sched_dt = job['scheduled_date']
            due_dt = job['due_date']
            
        db = get_db()
        db.jobs.update_one(
            {'_id': to_object_id(job_id)},
            {'$set': {
                'title': title,
                'description': description,
                'priority': priority,
                'scheduled_date': sched_dt,
                'due_date': due_dt,
                'location': {
                    'lat': float(lat) if lat else 0.0,
                    'lng': float(lng) if lng else 0.0,
                    'address': address
                },
                'status': status,
                'updated_at': datetime.utcnow()
            }}
        )
        
        flash("Job details updated successfully.", "success")
        return redirect(url_for('jobs.detail', job_id=job_id))
        
    return render_template('jobs/edit.html', job=job)

@jobs_bp.route('/<job_id>/assign', methods=['POST'])
@role_required(Roles.ADMIN)
def assign(job_id):
    """
    Assigns an employee to a job.
    """
    employee_id = request.form.get('employee_id')
    if not employee_id:
        flash("Please select an employee.", "danger")
        return redirect(url_for('jobs.detail', job_id=job_id))
        
    assign_employee_to_job(job_id, employee_id, session['user_id'])
    flash("Job assigned and notifications dispatched.", "success")
    return redirect(url_for('jobs.detail', job_id=job_id))
