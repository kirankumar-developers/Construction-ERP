from flask import Blueprint, render_template, redirect, url_for, flash, request
from database.mongodb import get_db
from utils.decorators import login_required, role_required
from utils.constants import Roles, SiteStatus
from utils.helpers import to_object_id, generate_site_code
from bson import ObjectId
from datetime import datetime

sites_bp = Blueprint('sites', __name__, url_prefix='/sites')

@sites_bp.route('/')
@login_required
def index():
    db = get_db()
    sites = list(db.sites.find())
    for s in sites:
        p = db.projects.find_one({'_id': s.get('project_id')})
        eng = db.users.find_one({'_id': s.get('engineer_id')})
        sup = db.users.find_one({'_id': s.get('supervisor_id')})
        s['project_name'] = p['name'] if p else 'N/A'
        s['engineer_name'] = eng['name'] if eng else 'N/A'
        s['supervisor_name'] = sup['name'] if sup else 'N/A'
    return render_template('sites/list.html', sites=sites)

@sites_bp.route('/add', methods=['GET', 'POST'])
@login_required
@role_required(Roles.SUPER_ADMIN, Roles.ADMIN, Roles.PROJECT_MANAGER)
def add():
    db = get_db()
    projects = list(db.projects.find())
    engineers = list(db.users.find({'role': Roles.SITE_ENGINEER}))
    supervisors = list(db.users.find({'role': Roles.SUPERVISOR}))
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        project_id = to_object_id(request.form.get('project_id'))
        address = request.form.get('address', '')
        lat = float(request.form.get('lat', 0.0) or 0)
        lng = float(request.form.get('lng', 0.0) or 0)
        engineer_id = to_object_id(request.form.get('engineer_id'))
        supervisor_id = to_object_id(request.form.get('supervisor_id'))
        
        if not name or not project_id or not engineer_id:
            flash("Site Name, Project, and Site Engineer are required.", "danger")
            return redirect(url_for('sites.add'))
            
        site_code = generate_site_code()
        
        site_doc = {
            'site_code': site_code,
            'name': name,
            'project_id': project_id,
            'address': address,
            'lat': lat,
            'lng': lng,
            'engineer_id': engineer_id,
            'supervisor_id': supervisor_id,
            'status': SiteStatus.ACTIVE,
            'created_at': datetime.utcnow()
        }
        
        db.sites.insert_one(site_doc)
        flash("Site created successfully!", "success")
        return redirect(url_for('sites.index'))
        
    return render_template('sites/add.html', projects=projects, engineers=engineers, supervisors=supervisors)

@sites_bp.route('/edit/<site_id>', methods=['GET', 'POST'])
@login_required
@role_required(Roles.SUPER_ADMIN, Roles.ADMIN, Roles.PROJECT_MANAGER)
def edit(site_id):
    db = get_db()
    oid = to_object_id(site_id)
    if not oid:
        flash("Invalid site ID.", "danger")
        return redirect(url_for('sites.index'))
        
    site = db.sites.find_one({'_id': oid})
    if not site:
        flash("Site not found.", "danger")
        return redirect(url_for('sites.index'))
        
    projects = list(db.projects.find())
    engineers = list(db.users.find({'role': Roles.SITE_ENGINEER}))
    supervisors = list(db.users.find({'role': Roles.SUPERVISOR}))
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        project_id = to_object_id(request.form.get('project_id'))
        address = request.form.get('address', '')
        lat = float(request.form.get('lat', 0.0) or 0)
        lng = float(request.form.get('lng', 0.0) or 0)
        engineer_id = to_object_id(request.form.get('engineer_id'))
        supervisor_id = to_object_id(request.form.get('supervisor_id'))
        status = request.form.get('status', SiteStatus.ACTIVE)
        
        if not name or not project_id or not engineer_id:
            flash("Site Name, Project, and Site Engineer are required.", "danger")
            return redirect(url_for('sites.edit', site_id=site_id))
            
        db.sites.update_one({'_id': oid}, {'$set': {
            'name': name,
            'project_id': project_id,
            'address': address,
            'lat': lat,
            'lng': lng,
            'engineer_id': engineer_id,
            'supervisor_id': supervisor_id,
            'status': status
        }})
        
        flash("Site updated successfully!", "success")
        return redirect(url_for('sites.index'))
        
    return render_template('sites/edit.html', site=site, projects=projects, engineers=engineers, supervisors=supervisors, SiteStatus=SiteStatus)

@sites_bp.route('/delete/<site_id>', methods=['POST'])
@login_required
@role_required(Roles.SUPER_ADMIN, Roles.ADMIN)
def delete(site_id):
    db = get_db()
    oid = to_object_id(site_id)
    if not oid:
        flash("Invalid site ID.", "danger")
        return redirect(url_for('sites.index'))
        
    site = db.sites.find_one({'_id': oid})
    if site:
        db.sites.delete_one({'_id': oid})
        flash(f"Site {site['name']} deleted successfully.", "success")
    else:
        flash("Site not found.", "danger")
    return redirect(url_for('sites.index'))
