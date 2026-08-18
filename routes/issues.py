from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from database.mongodb import get_db
from utils.decorators import login_required
from utils.constants import Roles, IssueStatus, TaskPriority
from utils.helpers import to_object_id, generate_issue_number
from services.upload_service import upload_file
from bson import ObjectId
from datetime import datetime

issues_bp = Blueprint('issues', __name__, url_prefix='/issues')

@issues_bp.route('/')
@login_required
def index():
    db = get_db()
    role = session.get('role')
    user_id = to_object_id(session.get('user_id'))
    
    if role in [Roles.SUPER_ADMIN, Roles.ADMIN]:
        issues = list(db.issues.find())
    elif role == Roles.PROJECT_MANAGER:
        projects = list(db.projects.find({'manager_id': user_id}))
        pids = [p['_id'] for p in projects]
        issues = list(db.issues.find({'project_id': {'$in': pids}}))
    elif role in [Roles.SITE_ENGINEER, Roles.SUPERVISOR, Roles.EMPLOYEE]:
        issues = list(db.issues.find({'$or': [{'reported_by': user_id}, {'assigned_to': user_id}]}))
    else:
        issues = []
        
    for issue in issues:
        p = db.projects.find_one({'_id': issue.get('project_id')})
        s = db.sites.find_one({'_id': issue.get('site_id')})
        rep = db.users.find_one({'_id': issue.get('reported_by')})
        ass = db.users.find_one({'_id': issue.get('assigned_to')})
        issue['project_name'] = p['name'] if p else 'N/A'
        issue['site_name'] = s['name'] if s else 'N/A'
        issue['reporter_name'] = rep['name'] if rep else 'N/A'
        issue['assignee_name'] = ass['name'] if ass else 'N/A'
        
    return render_template('quality/issue_list.html', issues=issues, IssueStatus=IssueStatus)

@issues_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    db = get_db()
    projects = list(db.projects.find())
    sites = list(db.sites.find())
    staff = list(db.users.find({'role': {'$in': [Roles.PROJECT_MANAGER, Roles.SITE_ENGINEER, Roles.SUPERVISOR, Roles.EMPLOYEE]}}))
    
    if request.method == 'POST':
        project_id = to_object_id(request.form.get('project_id'))
        site_id = to_object_id(request.form.get('site_id'))
        title = request.form.get('title', '').strip()
        desc = request.form.get('description', '')
        assigned_to = to_object_id(request.form.get('assigned_to'))
        priority = request.form.get('priority', TaskPriority.MEDIUM)
        due_date = request.form.get('due_date')
        file = request.files.get('photo')
        
        if not project_id or not site_id or not title:
            flash("Project, Site, and Title are required.", "danger")
            return redirect(url_for('issues.add'))
            
        file_path = None
        if file and file.filename:
            file_path, err = upload_file(file)
            if err:
                flash(err, "danger")
                return redirect(url_for('issues.add'))
                
        issue_no = generate_issue_number()
        db.issues.insert_one({
            'issue_number': issue_no,
            'project_id': project_id,
            'site_id': site_id,
            'title': title,
            'description': desc,
            'reported_by': to_object_id(session.get('user_id')),
            'assigned_to': assigned_to,
            'priority': priority,
            'status': IssueStatus.OPEN,
            'due_date': due_date,
            'photos': [file_path] if file_path else [],
            'created_at': datetime.utcnow()
        })
        
        # notify assignee
        if assigned_to:
            db.notifications.insert_one({
                'user_id': assigned_to,
                'title': "New Issue/Snag Assigned",
                'message': f"You have been assigned to Snag {issue_no}: {title}",
                'type': "issue_assigned",
                'link': "/issues/",
                'is_read': False,
                'created_at': datetime.utcnow()
            })
            
        flash(f"Snag {issue_no} reported successfully!", "success")
        return redirect(url_for('issues.index'))
        
    return render_template('quality/add_issue.html', projects=projects, sites=sites, staff=staff, TaskPriority=TaskPriority)

@issues_bp.route('/update/<issue_id>', methods=['POST'])
@login_required
def update_status(issue_id):
    db = get_db()
    oid = to_object_id(issue_id)
    status = request.form.get('status')
    
    db.issues.update_one({'_id': oid}, {'$set': {'status': status}})
    flash("Snag status updated successfully!", "success")
    return redirect(url_for('issues.index'))
