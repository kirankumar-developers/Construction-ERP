from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from database.mongodb import get_db
from utils.decorators import login_required, role_required
from utils.constants import Roles, ProjectStatus, ProjectPriority
from utils.helpers import to_object_id, generate_project_code
from bson import ObjectId
from datetime import datetime

projects_bp = Blueprint('projects', __name__, url_prefix='/projects')

@projects_bp.route('/')
@login_required
def index():
    db = get_db()
    role = session.get('role')
    user_id = to_object_id(session.get('user_id'))
    
    if role in [Roles.SUPER_ADMIN, Roles.ADMIN]:
        projects = list(db.projects.find())
    elif role == Roles.PROJECT_MANAGER:
        projects = list(db.projects.find({'manager_id': user_id}))
    elif role == Roles.CLIENT:
        client = db.clients.find_one({'user_id': user_id})
        projects = list(db.projects.find({'client_id': client['_id']})) if client else []
    elif role in [Roles.SITE_ENGINEER, Roles.SUPERVISOR]:
        # find sites this engineer is assigned to, then find projects
        sites = list(db.sites.find({'$or': [{'engineer_id': user_id}, {'supervisor_id': user_id}]}))
        pids = list(set([s['project_id'] for s in sites]))
        projects = list(db.projects.find({'_id': {'$in': pids}}))
    else:
        projects = []
        
    # Inject client and manager names
    for p in projects:
        m = db.users.find_one({'_id': p.get('manager_id')})
        c = db.clients.find_one({'_id': p.get('client_id')})
        p['manager_name'] = m['name'] if m else 'N/A'
        p['client_name'] = c['company_name'] if c else 'N/A'
        
    return render_template('projects/list.html', projects=projects)

@projects_bp.route('/add', methods=['GET', 'POST'])
@login_required
@role_required(Roles.SUPER_ADMIN, Roles.ADMIN)
def add():
    db = get_db()
    clients = list(db.clients.find())
    managers = list(db.users.find({'role': Roles.PROJECT_MANAGER}))
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        client_id = to_object_id(request.form.get('client_id'))
        manager_id = to_object_id(request.form.get('manager_id'))
        address = request.form.get('address', '')
        lat = float(request.form.get('lat', 0.0) or 0)
        lng = float(request.form.get('lng', 0.0) or 0)
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        budget = float(request.form.get('budget', 0.0) or 0)
        priority = request.form.get('priority', ProjectPriority.MEDIUM)
        description = request.form.get('description', '')
        
        if not name or not manager_id:
            flash("Project Name and Project Manager are required.", "danger")
            return redirect(url_for('projects.add'))
            
        proj_code = generate_project_code()
        
        proj_doc = {
            'project_code': proj_code,
            'name': name,
            'client_id': client_id,
            'manager_id': manager_id,
            'location': {
                'address': address,
                'lat': lat,
                'lng': lng
            },
            'start_date': start_date,
            'end_date': end_date,
            'budget': budget,
            'status': ProjectStatus.PLANNING,
            'priority': priority,
            'description': description,
            'progress': 0,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        
        db.projects.insert_one(proj_doc)
        
        # log activity
        db.activity_logs.insert_one({
            'user_id': to_object_id(session.get('user_id')),
            'action': f"Created project {proj_code} - {name}",
            'timestamp': datetime.utcnow()
        })
        
        flash("Project created successfully!", "success")
        return redirect(url_for('projects.index'))
        
    return render_template('projects/add.html', clients=clients, managers=managers, ProjectPriority=ProjectPriority)

@projects_bp.route('/view/<project_id>')
@login_required
def view(project_id):
    db = get_db()
    oid = to_object_id(project_id)
    if not oid:
        flash("Invalid project ID.", "danger")
        return redirect(url_for('projects.index'))
        
    project = db.projects.find_one({'_id': oid})
    if not project:
        flash("Project not found.", "danger")
        return redirect(url_for('projects.index'))
        
    manager = db.users.find_one({'_id': project.get('manager_id')})
    client = db.clients.find_one({'_id': project.get('client_id')})
    
    project['manager_name'] = manager['name'] if manager else 'N/A'
    project['client_name'] = client['company_name'] if client else 'N/A'
    
    # Fetch milestones
    milestones = list(db.milestones.find({'project_id': oid}))
    
    # Fetch sites
    sites = list(db.sites.find({'project_id': oid}))
    for s in sites:
        eng = db.users.find_one({'_id': s.get('engineer_id')})
        sup = db.users.find_one({'_id': s.get('supervisor_id')})
        s['engineer_name'] = eng['name'] if eng else 'N/A'
        s['supervisor_name'] = sup['name'] if sup else 'N/A'
        
    # Fetch tasks
    tasks = list(db.tasks.find({'project_id': oid}))
    
    # Fetch issues
    issues = list(db.issues.find({'project_id': oid}))
    
    # Budget tracking
    expenses = list(db.expenses.find({'project_id': oid, 'status': 'approved'}))
    actual_cost = sum([e.get('amount', 0.0) for e in expenses])
    
    # Activity log
    activities = list(db.activity_logs.find({
        'action': {'$regex': project['project_code']}
    }).sort('timestamp', -1).limit(10))
    
    return render_template('projects/view.html',
                           project=project,
                           milestones=milestones,
                           sites=sites,
                           tasks=tasks,
                           issues=issues,
                           actual_cost=actual_cost,
                           activities=activities)

@projects_bp.route('/edit/<project_id>', methods=['GET', 'POST'])
@login_required
@role_required(Roles.SUPER_ADMIN, Roles.ADMIN, Roles.PROJECT_MANAGER)
def edit(project_id):
    db = get_db()
    oid = to_object_id(project_id)
    if not oid:
        flash("Invalid project ID.", "danger")
        return redirect(url_for('projects.index'))
        
    project = db.projects.find_one({'_id': oid})
    if not project:
        flash("Project not found.", "danger")
        return redirect(url_for('projects.index'))
        
    clients = list(db.clients.find())
    managers = list(db.users.find({'role': Roles.PROJECT_MANAGER}))
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        client_id = to_object_id(request.form.get('client_id'))
        manager_id = to_object_id(request.form.get('manager_id'))
        address = request.form.get('address', '')
        lat = float(request.form.get('lat', 0.0) or 0)
        lng = float(request.form.get('lng', 0.0) or 0)
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        budget = float(request.form.get('budget', 0.0) or 0)
        status = request.form.get('status', ProjectStatus.PLANNING)
        priority = request.form.get('priority', ProjectPriority.MEDIUM)
        progress = int(request.form.get('progress', 0) or 0)
        description = request.form.get('description', '')
        
        if not name or not manager_id:
            flash("Project Name and Project Manager are required.", "danger")
            return redirect(url_for('projects.edit', project_id=project_id))
            
        db.projects.update_one({'_id': oid}, {'$set': {
            'name': name,
            'client_id': client_id,
            'manager_id': manager_id,
            'location': {
                'address': address,
                'lat': lat,
                'lng': lng
            },
            'start_date': start_date,
            'end_date': end_date,
            'budget': budget,
            'status': status,
            'priority': priority,
            'progress': progress,
            'description': description,
            'updated_at': datetime.utcnow()
        }})
        
        # log activity
        db.activity_logs.insert_one({
            'user_id': to_object_id(session.get('user_id')),
            'action': f"Updated project {project['project_code']} - {name}",
            'timestamp': datetime.utcnow()
        })
        
        flash("Project updated successfully!", "success")
        return redirect(url_for('projects.view', project_id=project_id))
        
    return render_template('projects/edit.html', project=project, clients=clients, managers=managers, ProjectStatus=ProjectStatus, ProjectPriority=ProjectPriority)

@projects_bp.route('/delete/<project_id>', methods=['POST'])
@login_required
@role_required(Roles.SUPER_ADMIN, Roles.ADMIN)
def delete(project_id):
    db = get_db()
    oid = to_object_id(project_id)
    if not oid:
        flash("Invalid project ID.", "danger")
        return redirect(url_for('projects.index'))
        
    project = db.projects.find_one({'_id': oid})
    if project:
        db.projects.delete_one({'_id': oid})
        flash(f"Project {project['name']} deleted successfully.", "success")
    else:
        flash("Project not found.", "danger")
    return redirect(url_for('projects.index'))

@projects_bp.route('/milestone/add/<project_id>', methods=['POST'])
@login_required
@role_required(Roles.SUPER_ADMIN, Roles.ADMIN, Roles.PROJECT_MANAGER)
def add_milestone(project_id):
    db = get_db()
    poid = to_object_id(project_id)
    title = request.form.get('title', '').strip()
    due_date = request.form.get('due_date')
    
    if not title or not due_date:
        flash("Milestone title and due date are required.", "danger")
        return redirect(url_for('projects.view', project_id=project_id))
        
    db.milestones.insert_one({
        'project_id': poid,
        'title': title,
        'due_date': due_date,
        'status': 'pending',
        'created_at': datetime.utcnow()
    })
    
    flash("Milestone added successfully!", "success")
    return redirect(url_for('projects.view', project_id=project_id))

@projects_bp.route('/milestone/toggle/<milestone_id>', methods=['POST'])
@login_required
@role_required(Roles.SUPER_ADMIN, Roles.ADMIN, Roles.PROJECT_MANAGER, Roles.SITE_ENGINEER)
def toggle_milestone(milestone_id):
    db = get_db()
    moid = to_object_id(milestone_id)
    milestone = db.milestones.find_one({'_id': moid})
    if not milestone:
        flash("Milestone not found.", "danger")
        return redirect(url_for('projects.index'))
        
    new_status = 'completed' if milestone.get('status') == 'pending' else 'pending'
    db.milestones.update_one({'_id': moid}, {'$set': {'status': new_status}})
    
    flash("Milestone status updated!", "success")
    return redirect(url_for('projects.view', project_id=str(milestone['project_id'])))
