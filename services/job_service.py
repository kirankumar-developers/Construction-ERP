import logging
from datetime import datetime
from bson import ObjectId
from database.mongodb import get_db
from utils.helpers import to_object_id, generate_job_number
from utils.constants import JobStatus, ServiceRequestStatus, Priority
from services.notification_service import create_notification
from services.email_service import send_assignment_email, send_status_update_email

logger = logging.getLogger(__name__)

def log_activity(user_id_str, action):
    """Logs actions to activity_logs for audit trails."""
    db = get_db()
    db.activity_logs.insert_one({
        'user_id': to_object_id(user_id_str),
        'action': action,
        'timestamp': datetime.utcnow()
    })

# Service Request Logic
def create_service_request(customer_id_str, title, description, service_category, priority, address, lat=0.0, lng=0.0, preferred_date=None):
    db = get_db()
    customer_id = to_object_id(customer_id_str)
    
    preferred_dt = None
    if preferred_date:
        try:
            preferred_dt = datetime.fromisoformat(preferred_date)
        except ValueError:
            pass

    request_doc = {
        'customer_id': customer_id,
        'title': title,
        'description': description,
        'service_category': service_category,
        'priority': priority or Priority.MEDIUM,
        'location': {
            'lat': float(lat) if lat else 0.0,
            'lng': float(lng) if lng else 0.0,
            'address': address
        },
        'preferred_date': preferred_dt or datetime.utcnow(),
        'status': ServiceRequestStatus.PENDING,
        'created_at': datetime.utcnow(),
        'updated_at': datetime.utcnow()
    }
    
    result = db.service_requests.insert_one(request_doc)
    request_doc['_id'] = result.inserted_id
    
    # Notify Admin(s)
    admins = list(db.users.find({'role': 'admin'}))
    for admin in admins:
        create_notification(
            str(admin['_id']),
            "New Service Request",
            f"Customer request '{title}' has been submitted.",
            'service_request'
        )
        
    return request_doc

def get_service_requests_by_customer(customer_id_str):
    db = get_db()
    cid = to_object_id(customer_id_str)
    return list(db.service_requests.find({'customer_id': cid}).sort('created_at', -1))

def get_all_service_requests():
    db = get_db()
    requests = list(db.service_requests.find().sort('created_at', -1))
    for req in requests:
        cust = db.customers.find_one({'_id': req['customer_id']})
        if cust:
            req['customer_name'] = cust['customer_name']
        else:
            req['customer_name'] = "Unknown"
    return requests

# Job Logic
def create_job(creator_id_str, customer_id_str, title, description, priority, scheduled_date, due_date, address, lat=0.0, lng=0.0, service_request_id_str=None):
    db = get_db()
    customer_id = to_object_id(customer_id_str)
    creator_id = to_object_id(creator_id_str)
    req_id = to_object_id(service_request_id_str)
    
    sched_dt = None
    if scheduled_date:
        try:
            sched_dt = datetime.fromisoformat(scheduled_date)
        except ValueError:
            pass
            
    due_dt = None
    if due_date:
        try:
            due_dt = datetime.fromisoformat(due_date)
        except ValueError:
            pass

    job_num = generate_job_number()
    job_doc = {
        'job_number': job_num,
        'customer_id': customer_id,
        'service_request_id': req_id,
        'title': title,
        'description': description,
        'priority': priority or Priority.MEDIUM,
        'scheduled_date': sched_dt or datetime.utcnow(),
        'due_date': due_dt or datetime.utcnow(),
        'location': {
            'lat': float(lat) if lat else 0.0,
            'lng': float(lng) if lng else 0.0,
            'address': address
        },
        'status': JobStatus.PENDING,
        'created_by': creator_id,
        'created_at': datetime.utcnow(),
        'updated_at': datetime.utcnow()
    }
    
    db.jobs.insert_one(job_doc)
    
    # Log activity
    log_activity(creator_id_str, f"Created job {job_num}")
    
    # If this matches a service request, mark it as approved
    if req_id:
        db.service_requests.update_one(
            {'_id': req_id},
            {'$set': {'status': ServiceRequestStatus.APPROVED, 'updated_at': datetime.utcnow()}}
        )
        
    return job_doc

def assign_employee_to_job(job_id_str, employee_id_str, assigner_id_str):
    db = get_db()
    jid = to_object_id(job_id_str)
    eid = to_object_id(employee_id_str)
    aid = to_object_id(assigner_id_str)
    
    # 1. Update job status to assigned
    db.jobs.update_one(
        {'_id': jid},
        {'$set': {'status': JobStatus.ASSIGNED, 'updated_at': datetime.utcnow()}}
    )
    
    # 2. Add or update job assignment
    assignment = {
        'job_id': jid,
        'employee_id': eid,
        'assigned_by': aid,
        'assigned_at': datetime.utcnow(),
        'assignment_status': 'assigned'
    }
    db.job_assignments.update_one(
        {'job_id': jid},
        {'$set': assignment},
        upsert=True
    )
    
    job = db.jobs.find_one({'_id': jid})
    emp = db.employees.find_one({'_id': eid})
    
    if emp and job:
        # Update employee status
        db.employees.update_one({'_id': eid}, {'$set': {'current_status': 'on_job'}})
        
        emp_user = db.users.find_one({'_id': emp['user_id']})
        if emp_user:
            # Create system notification
            create_notification(
                str(emp_user['_id']),
                "Job Assigned",
                f"You have been assigned to job {job['job_number']}: '{job['title']}'. Please accept or decline.",
                'job_assigned'
            )
            # Send assignment email
            send_assignment_email(
                emp_user['email'],
                emp_user['name'],
                job['job_number'],
                job['title']
            )
            
    log_activity(assigner_id_str, f"Assigned job {job.get('job_number')} to employee {emp.get('employee_id') if emp else 'Unknown'}")
    return True

def update_job_status(job_id_str, new_status, employee_id_str=None, notes="", attachments=None):
    """
    Updates the status of a job.
    Logs the update in job_updates.
    Sends notifications/emails where appropriate.
    """
    db = get_db()
    jid = to_object_id(job_id_str)
    eid = to_object_id(employee_id_str)
    
    job = db.jobs.find_one({'_id': jid})
    if not job:
        return False, "Job not found."
        
    old_status = job['status']
    
    # Update Job Document
    db.jobs.update_one(
        {'_id': jid},
        {'$set': {'status': new_status, 'updated_at': datetime.utcnow()}}
    )
    
    # Record Update History
    update_doc = {
        'job_id': jid,
        'employee_id': eid,
        'status': new_status,
        'notes': notes,
        'attachments': attachments or [],
        'updated_at': datetime.utcnow()
    }
    db.job_updates.insert_one(update_doc)
    
    # Notify Customer about status change
    cust = db.customers.find_one({'_id': job['customer_id']})
    if cust:
        cust_user = db.users.find_one({'_id': cust['user_id']})
        if cust_user:
            create_notification(
                str(cust_user['_id']),
                "Job Status Updated",
                f"Your job {job['job_number']} status has changed from {old_status} to {new_status}.",
                'job_status'
            )
            send_status_update_email(
                cust_user['email'],
                cust_user['name'],
                job['job_number'],
                new_status
            )
            
    # Notify Admins
    admins = list(db.users.find({'role': 'admin'}))
    for admin in admins:
        create_notification(
            str(admin['_id']),
            "Job Updated",
            f"Job {job['job_number']} updated to {new_status} by employee.",
            'job_status'
        )
        
    # If completed, and there is an associated request, complete that too
    if new_status == JobStatus.COMPLETED and job.get('service_request_id'):
        db.service_requests.update_one(
            {'_id': job['service_request_id']},
            {'$set': {'status': ServiceRequestStatus.COMPLETED, 'updated_at': datetime.utcnow()}}
        )
        
    # Log activity
    emp = db.employees.find_one({'_id': eid}) if eid else None
    actor_id_str = str(emp['user_id']) if emp else str(job['created_by'])
    log_activity(actor_id_str, f"Updated job {job['job_number']} status to {new_status}")
    
    return True, None

def get_job_by_id(job_id_str):
    db = get_db()
    jid = to_object_id(job_id_str)
    if not jid:
        return None
    job = db.jobs.find_one({'_id': jid})
    if not job:
        return None
        
    # Populate related info
    cust = db.customers.find_one({'_id': job['customer_id']})
    if cust:
        job['customer_name'] = cust['customer_name']
        job['customer_phone'] = cust['phone']
        job['customer_email'] = cust['email']
        job['customer_address'] = cust['address']
    
    assignment = db.job_assignments.find_one({'job_id': jid})
    if assignment:
        job['assignment'] = assignment
        emp = db.employees.find_one({'_id': assignment['employee_id']})
        if emp:
            emp_user = db.users.find_one({'_id': emp['user_id']})
            job['employee_name'] = emp_user['name'] if emp_user else "Unknown"
            job['employee_id_val'] = emp['employee_id']
            job['employee_phone'] = emp['phone']
            job['employee_obj_id'] = str(emp['_id'])
            
    # Load updates
    updates = list(db.job_updates.find({'job_id': jid}).sort('updated_at', -1))
    for update in updates:
        if update.get('employee_id'):
            emp = db.employees.find_one({'_id': update['employee_id']})
            if emp:
                emp_user = db.users.find_one({'_id': emp['user_id']})
                update['by_name'] = emp_user['name'] if emp_user else "Employee"
        else:
            update['by_name'] = "System/Admin"
    job['updates'] = updates
    
    return job

def get_jobs_by_employee(employee_id_str):
    db = get_db()
    eid = to_object_id(employee_id_str)
    
    assignments = db.job_assignments.find({'employee_id': eid})
    job_ids = [ass['job_id'] for ass in assignments]
    
    jobs = list(db.jobs.find({'_id': {'$in': job_ids}}).sort('scheduled_date', 1))
    for job in jobs:
        cust = db.customers.find_one({'_id': job['customer_id']})
        if cust:
            job['customer_name'] = cust['customer_name']
            job['customer_phone'] = cust['phone']
    return jobs

def get_jobs_by_customer(customer_id_str):
    db = get_db()
    cid = to_object_id(customer_id_str)
    jobs = list(db.jobs.find({'customer_id': cid}).sort('created_at', -1))
    for job in jobs:
        assignment = db.job_assignments.find_one({'job_id': job['_id']})
        if assignment:
            emp = db.employees.find_one({'_id': assignment['employee_id']})
            if emp:
                emp_user = db.users.find_one({'_id': emp['user_id']})
                job['employee_name'] = emp_user['name'] if emp_user else "Assigned"
                job['employee_phone'] = emp['phone']
    return jobs

def get_all_jobs():
    db = get_db()
    jobs = list(db.jobs.find().sort('created_at', -1))
    for job in jobs:
        cust = db.customers.find_one({'_id': job['customer_id']})
        job['customer_name'] = cust['customer_name'] if cust else "Unknown"
        
        assignment = db.job_assignments.find_one({'job_id': job['_id']})
        if assignment:
            emp = db.employees.find_one({'_id': assignment['employee_id']})
            if emp:
                emp_user = db.users.find_one({'_id': emp['user_id']})
                job['employee_name'] = emp_user['name'] if emp_user else "Assigned"
                job['employee_status'] = assignment['assignment_status']
    return jobs

def get_dashboard_metrics():
    """
    Returns metrics summary for admin dashboard.
    """
    db = get_db()
    
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    
    total_customers = db.customers.count_documents({})
    total_employees = db.employees.count_documents({})
    total_jobs = db.jobs.count_documents({})
    
    pending_jobs = db.jobs.count_documents({'status': JobStatus.PENDING})
    assigned_jobs = db.jobs.count_documents({'status': JobStatus.ASSIGNED})
    accepted_jobs = db.jobs.count_documents({'status': JobStatus.ACCEPTED})
    inprogress_jobs = db.jobs.count_documents({'status': JobStatus.IN_PROGRESS})
    onhold_jobs = db.jobs.count_documents({'status': JobStatus.ON_HOLD})
    completed_jobs = db.jobs.count_documents({'status': JobStatus.COMPLETED})
    cancelled_jobs = db.jobs.count_documents({'status': JobStatus.CANCELLED})
    
    today_jobs = db.jobs.count_documents({
        'scheduled_date': {'$gte': today_start}
    })
    
    # Active attendance count
    today_attendance = db.attendance.count_documents({
        'check_in_time': {'$gte': today_start}
    })
    
    # Recent Activities
    recent_logs = list(db.activity_logs.find().sort('timestamp', -1).limit(10))
    for log in recent_logs:
        user = db.users.find_one({'_id': log['user_id']})
        log['user_name'] = user['name'] if user else "System"
        
    return {
        'total_customers': total_customers,
        'total_employees': total_employees,
        'total_jobs': total_jobs,
        'pending_jobs': pending_jobs,
        'assigned_jobs': assigned_jobs,
        'accepted_jobs': accepted_jobs,
        'inprogress_jobs': inprogress_jobs,
        'onhold_jobs': onhold_jobs,
        'completed_jobs': completed_jobs,
        'cancelled_jobs': cancelled_jobs,
        'today_jobs': today_jobs,
        'today_attendance': today_attendance,
        'recent_activities': recent_logs
    }
