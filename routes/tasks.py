from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from database.mongodb import get_db
from utils.decorators import login_required, role_required
from utils.constants import Roles, TaskStatus, TaskPriority
from utils.helpers import to_object_id
from services.task_service import create_task, add_task_comment
from services.upload_service import upload_file
from bson import ObjectId
from datetime import datetime

tasks_bp = Blueprint('tasks', __name__, url_prefix='/tasks')

@tasks_bp.route('/')
@login_required
def index():
    db = get_db()
    role = session.get('role')
    user_id = to_object_id(session.get('user_id'))
    
    if role in [Roles.SUPER_ADMIN, Roles.ADMIN]:
        tasks = list(db.tasks.find())
    elif role == Roles.PROJECT_MANAGER:
        projects = list(db.projects.find({'manager_id': user_id}))
        pids = [p['_id'] for p in projects]
        tasks = list(db.tasks.find({'project_id': {'$in': pids}}))
    elif role == Roles.SITE_ENGINEER:
        sites = list(db.sites.find({'engineer_id': user_id}))
        sids = [s['_id'] for s in sites]
        tasks = list(db.tasks.find({'site_id': {'$in': sids}}))
    elif role == Roles.SUPERVISOR:
        sites = list(db.sites.find({'supervisor_id': user_id}))
        sids = [s['_id'] for s in sites]
        tasks = list(db.tasks.find({'site_id': {'$in': sids}}))
    else:
        tasks = list(db.tasks.find({'assigned_employee_ids': user_id}))
        
    for t in tasks:
        p = db.projects.find_one({'_id': t.get('project_id')})
        s = db.sites.find_one({'_id': t.get('site_id')})
        t['project_name'] = p['name'] if p else 'N/A'
        t['site_name'] = s['name'] if s else 'N/A'
        
    return render_template('tasks/list.html', tasks=tasks)

@tasks_bp.route('/add', methods=['GET', 'POST'])
@login_required
@role_required(Roles.SUPER_ADMIN, Roles.ADMIN, Roles.PROJECT_MANAGER, Roles.SITE_ENGINEER)
def add():
    db = get_db()
    projects = list(db.projects.find())
    sites = list(db.sites.find())
    employees = list(db.users.find({'role': {'$in': [Roles.SITE_ENGINEER, Roles.SUPERVISOR, Roles.EMPLOYEE]}}))
    parent_tasks = list(db.tasks.find())
    
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '')
        project_id = request.form.get('project_id')
        site_id = request.form.get('site_id')
        assigned = request.form.getlist('assigned_employee_ids')
        start_date = request.form.get('start_date')
        due_date = request.form.get('due_date')
        priority = request.form.get('priority', TaskPriority.MEDIUM)
        parent_id = request.form.get('parent_task_id')
        
        if not title or not project_id or not site_id:
            flash("Task Title, Project, and Site are required.", "danger")
            return redirect(url_for('tasks.add'))
            
        create_task(project_id, site_id, title, description, assigned, start_date, due_date, priority, parent_id)
        flash("Task created successfully!", "success")
        return redirect(url_for('tasks.index'))
        
    return render_template('tasks/add.html',
                           projects=projects,
                           sites=sites,
                           employees=employees,
                           parent_tasks=parent_tasks,
                           TaskPriority=TaskPriority)

@tasks_bp.route('/view/<task_id>', methods=['GET', 'POST'])
@login_required
def view(task_id):
    db = get_db()
    oid = to_object_id(task_id)
    if not oid:
        flash("Invalid task ID.", "danger")
        return redirect(url_for('tasks.index'))
        
    task = db.tasks.find_one({'_id': oid})
    if not task:
        flash("Task not found.", "danger")
        return redirect(url_for('tasks.index'))
        
    p = db.projects.find_one({'_id': task.get('project_id')})
    s = db.sites.find_one({'_id': task.get('site_id')})
    task['project_name'] = p['name'] if p else 'N/A'
    task['site_name'] = s['name'] if s else 'N/A'
    
    # Fetch assignees
    assignees = list(db.users.find({'_id': {'$in': task.get('assigned_employee_ids', [])}}))
    
    # Fetch comments
    comments = list(db.task_comments.find({'task_id': oid}).sort('created_at', 1))
    for c in comments:
        u = db.users.find_one({'_id': c.get('user_id')})
        c['user_name'] = u['name'] if u else 'Unknown'
        c['role'] = u['role'] if u else ''
        
    # Handle Comment Posting
    if request.method == 'POST':
        comment_text = request.form.get('comment', '').strip()
        file = request.files.get('attachment')
        
        file_path = None
        orig_name = None
        if file and file.filename:
            file_path, err = upload_file(file)
            if err:
                flash(err, "danger")
                return redirect(url_for('tasks.view', task_id=task_id))
            orig_name = file.filename
            
        if comment_text or file_path:
            add_task_comment(oid, session['user_id'], comment_text, file_path, orig_name)
            flash("Comment added successfully!", "success")
        return redirect(url_for('tasks.view', task_id=task_id))
        
    subtasks = list(db.tasks.find({'parent_task_id': oid}))
    
    return render_template('tasks/view.html',
                           task=task,
                           assignees=assignees,
                           comments=comments,
                           subtasks=subtasks,
                           TaskStatus=TaskStatus)

@tasks_bp.route('/update_status/<task_id>', methods=['POST'])
@login_required
def update_status(task_id):
    db = get_db()
    oid = to_object_id(task_id)
    status = request.form.get('status')
    progress = int(request.form.get('progress', 0) or 0)
    
    if not status:
        flash("Status is required.", "danger")
        return redirect(url_for('tasks.view', task_id=task_id))
        
    db.tasks.update_one({'_id': oid}, {'$set': {
        'status': status,
        'progress': progress,
        'updated_at': datetime.utcnow()
    }})
    
    flash("Task progress updated successfully!", "success")
    return redirect(url_for('tasks.view', task_id=task_id))
