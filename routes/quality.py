from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from database.mongodb import get_db
from utils.decorators import login_required, role_required
from utils.constants import Roles, InspectionResult
from utils.helpers import to_object_id
from services.upload_service import upload_file
from bson import ObjectId
from datetime import datetime

quality_bp = Blueprint('quality', __name__, url_prefix='/quality')

@quality_bp.route('/')
@login_required
def index():
    db = get_db()
    inspections = list(db.inspections.find().sort('inspection_date', -1))
    for ins in inspections:
        p = db.projects.find_one({'_id': ins.get('project_id')})
        s = db.sites.find_one({'_id': ins.get('site_id')})
        u = db.users.find_one({'_id': ins.get('inspector_id')})
        ins['project_name'] = p['name'] if p else 'N/A'
        ins['site_name'] = s['name'] if s else 'N/A'
        ins['inspector_name'] = u['name'] if u else 'N/A'
        
    return render_template('quality/list.html', inspections=inspections, InspectionResult=InspectionResult)

@quality_bp.route('/add', methods=['GET', 'POST'])
@login_required
@role_required(Roles.SUPER_ADMIN, Roles.ADMIN, Roles.PROJECT_MANAGER, Roles.SITE_ENGINEER)
def add():
    db = get_db()
    projects = list(db.projects.find())
    sites = list(db.sites.find())
    
    if request.method == 'POST':
        project_id = to_object_id(request.form.get('project_id'))
        site_id = to_object_id(request.form.get('site_id'))
        date_str = request.form.get('inspection_date') or datetime.utcnow().strftime('%Y-%m-%d')
        remarks = request.form.get('remarks', '')
        
        # Parse checklist items
        items = request.form.getlist('checklist_item[]')
        statuses = request.form.getlist('checklist_status[]')
        
        checklist = []
        for i in range(len(items)):
            itm = items[i].strip()
            if itm:
                checklist.append({
                    'item': itm,
                    'status': statuses[i]
                })
                
        # Overall result based on checklist items: if any fail, need correction
        result = InspectionResult.APPROVED
        for item in checklist:
            if item['status'] in ['Fail', 'Needs Correction']:
                result = InspectionResult.NEEDS_CORRECTION
                break
                
        file = request.files.get('photo')
        file_path = None
        if file and file.filename:
            file_path, err = upload_file(file)
            if err:
                flash(err, "danger")
                return redirect(url_for('quality.add'))
                
        db.inspections.insert_one({
            'project_id': project_id,
            'site_id': site_id,
            'inspector_id': to_object_id(session.get('user_id')),
            'inspection_date': date_str,
            'checklist': checklist,
            'result': result,
            'remarks': remarks,
            'photos': [file_path] if file_path else [],
            'created_at': datetime.utcnow()
        })
        
        flash("Inspection checklist recorded successfully!", "success")
        return redirect(url_for('quality.index'))
        
    return render_template('quality/add.html', projects=projects, sites=sites)
