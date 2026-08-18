from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from database.mongodb import get_db
from utils.decorators import login_required, role_required
from utils.constants import Roles
from utils.helpers import to_object_id
from services.upload_service import upload_file
from bson import ObjectId
from datetime import datetime

dpr_bp = Blueprint('dpr', __name__, url_prefix='/dpr')

@dpr_bp.route('/')
@login_required
def index():
    db = get_db()
    role = session.get('role')
    user_id = to_object_id(session.get('user_id'))
    
    if role in [Roles.SUPER_ADMIN, Roles.ADMIN]:
        dprs = list(db.dpr.find().sort('date', -1))
    elif role == Roles.PROJECT_MANAGER:
        projects = list(db.projects.find({'manager_id': user_id}))
        pids = [p['_id'] for p in projects]
        dprs = list(db.dpr.find({'project_id': {'$in': pids}}).sort('date', -1))
    elif role == Roles.SITE_ENGINEER:
        dprs = list(db.dpr.find({'submitted_by': user_id}).sort('date', -1))
    else:
        dprs = []
        
    for d in dprs:
        p = db.projects.find_one({'_id': d.get('project_id')})
        s = db.sites.find_one({'_id': d.get('site_id')})
        sub = db.users.find_one({'_id': d.get('submitted_by')})
        d['project_name'] = p['name'] if p else 'N/A'
        d['site_name'] = s['name'] if s else 'N/A'
        d['submitted_by_name'] = sub['name'] if sub else 'Unknown'
        
    return render_template('dpr/list.html', dprs=dprs, Roles=Roles)

@dpr_bp.route('/add', methods=['GET', 'POST'])
@login_required
@role_required(Roles.SITE_ENGINEER, Roles.SUPERVISOR, Roles.ADMIN)
def add():
    db = get_db()
    role = session.get('role')
    user_id = to_object_id(session.get('user_id'))
    
    # sites assigned to engineer
    if role == Roles.ADMIN:
        sites = list(db.sites.find())
    else:
        sites = list(db.sites.find({'$or': [{'engineer_id': user_id}, {'supervisor_id': user_id}]}))
        
    materials = list(db.materials.find())
    equipments = list(db.equipment.find({'status': 'available'}))
    
    if request.method == 'POST':
        site_id = to_object_id(request.form.get('site_id'))
        date_str = request.form.get('date') or datetime.utcnow().strftime('%Y-%m-%d')
        work_completed = request.form.get('work_completed', '')
        work_wip = request.form.get('work_in_progress', '')
        weather = request.form.get('weather', '')
        issues = request.form.get('issues', '')
        delays = request.form.get('delays', '')
        remarks = request.form.get('remarks', '')
        
        # parse site to get project
        site = db.sites.find_one({'_id': site_id})
        if not site:
            flash("Invalid Site selected.", "danger")
            return redirect(url_for('dpr.add'))
            
        project_id = site['project_id']
        
        # parse labour count
        labours_mason = int(request.form.get('labour_mason', 0) or 0)
        labours_carpenter = int(request.form.get('labour_carpenter', 0) or 0)
        labours_helper = int(request.form.get('labour_helper', 0) or 0)
        labours_other = int(request.form.get('labour_other', 0) or 0)
        labour_details = {
            'Mason': labours_mason,
            'Carpenter': labours_carpenter,
            'Helper': labours_helper,
            'Other': labours_other,
            'total': labours_mason + labours_carpenter + labours_helper + labours_other
        }
        
        # parse material usage
        mat_ids = request.form.getlist('material_id[]')
        mat_qtys = request.form.getlist('material_qty[]')
        material_used = []
        for i in range(len(mat_ids)):
            mid = to_object_id(mat_ids[i])
            qty = float(mat_qtys[i] or 0)
            if mid and qty > 0:
                # Stock validation - verify if they have enough stock (optional warning, or force stock deduction)
                m = db.materials.find_one({'_id': mid})
                material_used.append({
                    'material_id': mid,
                    'name': m['name'] if m else 'Unknown',
                    'quantity': qty
                })
                
                # deduct inventory (site-wise stock)
                db.inventory.update_one(
                    {'material_id': mid, 'site_id': site_id},
                    {'$inc': {'quantity': -qty}},
                    upsert=True
                )
                # transaction record
                db.inventory_transactions.insert_one({
                    'material_id': mid,
                    'project_id': project_id,
                    'site_id': site_id,
                    'type': 'Stock Out', # Consumption
                    'quantity': qty,
                    'reference_type': 'DPR',
                    'created_by': user_id,
                    'created_at': datetime.utcnow()
                })
                
        # parse equipment usage
        eq_ids = request.form.getlist('equipment_id[]')
        eq_hours = request.form.getlist('equipment_hours[]')
        equipment_used = []
        for i in range(len(eq_ids)):
            eqid = to_object_id(eq_ids[i])
            hours = float(eq_hours[i] or 0)
            if eqid and hours > 0:
                eq = db.equipment.find_one({'_id': eqid})
                equipment_used.append({
                    'equipment_id': eqid,
                    'name': eq['name'] if eq else 'Unknown',
                    'hours': hours
                })
                # add to equipment usage cost
                cost = hours * eq.get('daily_cost', 0) / 8.0 # assume 8 hr day
                db.equipment_usage.insert_one({
                    'equipment_id': eqid,
                    'project_id': project_id,
                    'site_id': site_id,
                    'date': date_str,
                    'hours_used': hours,
                    'cost': cost,
                    'created_at': datetime.utcnow()
                })
                
        # Upload photo
        photo_paths = []
        photo_file = request.files.get('photo')
        if photo_file and photo_file.filename:
            file_path, err = upload_file(photo_file)
            if file_path:
                photo_paths.append(file_path)
                
        dpr_doc = {
            'project_id': project_id,
            'site_id': site_id,
            'date': date_str,
            'submitted_by': user_id,
            'work_completed': work_completed,
            'work_in_progress': work_wip,
            'labour_details': labour_details,
            'material_used': material_used,
            'equipment_used': equipment_used,
            'weather': weather,
            'issues': issues,
            'delays': delays,
            'remarks': remarks,
            'photos': photo_paths,
            'status': 'pending',
            'created_at': datetime.utcnow()
        }
        
        db.dpr.insert_one(dpr_doc)
        
        # Notify Project Manager
        pm_user = db.users.find_one({'_id': site.get('engineer_id')}) # Site Engineer or project manager
        proj = db.projects.find_one({'_id': project_id})
        if proj:
            db.notifications.insert_one({
                'user_id': proj.get('manager_id'),
                'title': "DPR Submitted",
                'message': f"DPR submitted for site {site['name']} on {date_str}.",
                'type': "dpr_submitted",
                'link': "/dpr/",
                'is_read': False,
                'created_at': datetime.utcnow()
            })
            
        flash("DPR submitted successfully!", "success")
        return redirect(url_for('dpr.index'))
        
    return render_template('dpr/add.html', sites=sites, materials=materials, equipments=equipments)

@dpr_bp.route('/review/<dpr_id>', methods=['POST'])
@login_required
@role_required(Roles.SUPER_ADMIN, Roles.ADMIN, Roles.PROJECT_MANAGER)
def review(dpr_id):
    db = get_db()
    oid = to_object_id(dpr_id)
    action = request.form.get('action') # approve, reject
    remarks = request.form.get('review_remarks', '')
    
    if not oid or action not in ['approve', 'reject']:
        flash("Invalid action.", "danger")
        return redirect(url_for('dpr.index'))
        
    status = 'approved' if action == 'approve' else 'rejected'
    db.dpr.update_one({'_id': oid}, {'$set': {
        'status': status,
        'review_remarks': remarks,
        'reviewed_by': to_object_id(session.get('user_id')),
        'updated_at': datetime.utcnow()
    }})
    
    flash(f"DPR has been {status}.", "success")
    return redirect(url_for('dpr.index'))
