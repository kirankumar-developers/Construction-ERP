from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from database.mongodb import get_db
from utils.decorators import login_required, role_required
from utils.constants import Roles
from utils.helpers import to_object_id, generate_work_order_number
from bson import ObjectId
from datetime import datetime

subcontractors_bp = Blueprint('subcontractors', __name__, url_prefix='/subcontractors')

@subcontractors_bp.route('/')
@login_required
def index():
    db = get_db()
    subcontractors = list(db.subcontractors.find())
    return render_template('subcontractors/list.html', subcontractors=subcontractors)

@subcontractors_bp.route('/view/<sub_id>')
@login_required
def view(sub_id):
    db = get_db()
    oid = to_object_id(sub_id)
    if not oid:
        flash("Invalid Subcontractor ID.", "danger")
        return redirect(url_for('subcontractors.index'))
        
    sub = db.subcontractors.find_one({'_id': oid})
    if not sub:
        flash("Subcontractor not found.", "danger")
        return redirect(url_for('subcontractors.index'))
        
    # Fetch work orders
    wos = list(db.work_orders.find({'subcontractor_id': oid}))
    for wo in wos:
        p = db.projects.find_one({'_id': wo.get('project_id')})
        wo['project_name'] = p['name'] if p else 'N/A'
        
    return render_template('subcontractors/view.html', subcontractor=sub, work_orders=wos)

@subcontractors_bp.route('/work-orders')
@login_required
def work_orders():
    db = get_db()
    wos = list(db.work_orders.find())
    for wo in wos:
        sub = db.subcontractors.find_one({'_id': wo.get('subcontractor_id')})
        p = db.projects.find_one({'_id': wo.get('project_id')})
        s = db.sites.find_one({'_id': wo.get('site_id')})
        wo['subcontractor_name'] = sub['company_name'] if sub else 'N/A'
        wo['project_name'] = p['name'] if p else 'N/A'
        wo['site_name'] = s['name'] if s else 'N/A'
    return render_template('subcontractors/work_orders.html', work_orders=wos)

@subcontractors_bp.route('/work-order/add', methods=['GET', 'POST'])
@login_required
@role_required(Roles.SUPER_ADMIN, Roles.ADMIN, Roles.PROJECT_MANAGER)
def add_work_order():
    db = get_db()
    projects = list(db.projects.find())
    sites = list(db.sites.find())
    subcontractors = list(db.subcontractors.find())
    
    if request.method == 'POST':
        sub_id = to_object_id(request.form.get('subcontractor_id'))
        project_id = to_object_id(request.form.get('project_id'))
        site_id = to_object_id(request.form.get('site_id'))
        desc = request.form.get('description', '')
        val = float(request.form.get('contract_amount', 0.0) or 0)
        s_date = request.form.get('start_date')
        e_date = request.form.get('end_date')
        
        if not sub_id or not project_id or not site_id:
            flash("Subcontractor, Project, and Site are required.", "danger")
            return redirect(url_for('subcontractors.add_work_order'))
            
        wo_no = generate_work_order_number()
        db.work_orders.insert_one({
            'work_order_number': wo_no,
            'subcontractor_id': sub_id,
            'project_id': project_id,
            'site_id': site_id,
            'description': desc,
            'contract_amount': val,
            'start_date': s_date,
            'end_date': e_date,
            'status': 'In Progress',
            'created_at': datetime.utcnow()
        })
        
        flash(f"Work Order {wo_no} created successfully!", "success")
        return redirect(url_for('subcontractors.work_orders'))
        
    return render_template('subcontractors/add_work_order.html',
                           projects=projects,
                           sites=sites,
                           subcontractors=subcontractors)

@subcontractors_bp.route('/work-order/status/<wo_id>', methods=['POST'])
@login_required
def update_wo_status(wo_id):
    db = get_db()
    oid = to_object_id(wo_id)
    status = request.form.get('status')
    
    db.work_orders.update_one({'_id': oid}, {'$set': {'status': status}})
    flash("Work Order status updated!", "success")
    return redirect(url_for('subcontractors.work_orders'))
