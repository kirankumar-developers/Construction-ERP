from flask import Blueprint, render_template, redirect, url_for, flash, request
from database.mongodb import get_db
from utils.decorators import login_required, role_required
from utils.constants import Roles
from utils.helpers import to_object_id, generate_labor_id
from bson import ObjectId
from datetime import datetime

labour_bp = Blueprint('labour', __name__, url_prefix='/labour')

@labour_bp.route('/')
@login_required
def index():
    db = get_db()
    labours = list(db.labours.find())
    for l in labours:
        p = db.projects.find_one({'_id': l.get('project_id')})
        s = db.sites.find_one({'_id': l.get('site_id')})
        l['project_name'] = p['name'] if p else 'N/A'
        l['site_name'] = s['name'] if s else 'N/A'
    return render_template('labour/list.html', labours=labours)

@labour_bp.route('/add', methods=['GET', 'POST'])
@login_required
@role_required(Roles.SUPER_ADMIN, Roles.ADMIN, Roles.PROJECT_MANAGER, Roles.SITE_ENGINEER)
def add():
    db = get_db()
    projects = list(db.projects.find())
    sites = list(db.sites.find())
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        category = request.form.get('category', 'Mason')
        project_id = to_object_id(request.form.get('project_id'))
        site_id = to_object_id(request.form.get('site_id'))
        wage = float(request.form.get('daily_wage', 0.0) or 0)
        
        if not name or not project_id or not site_id:
            flash("Labour Name, Project, and Site are required.", "danger")
            return redirect(url_for('labour.add'))
            
        labor_id = generate_labor_id()
        db.labours.insert_one({
            'labour_id': labor_id,
            'name': name,
            'category': category,
            'project_id': project_id,
            'site_id': site_id,
            'daily_wage': wage,
            'status': 'active',
            'created_at': datetime.utcnow()
        })
        
        flash("Labour registered successfully!", "success")
        return redirect(url_for('labour.index'))
        
    return render_template('labour/add.html', projects=projects, sites=sites)

@labour_bp.route('/attendance', methods=['GET', 'POST'])
@login_required
@role_required(Roles.SUPER_ADMIN, Roles.ADMIN, Roles.PROJECT_MANAGER, Roles.SITE_ENGINEER, Roles.SUPERVISOR)
def log_attendance():
    db = get_db()
    sites = list(db.sites.find())
    selected_site_id = to_object_id(request.args.get('site_id') or request.form.get('site_id'))
    date_str = request.form.get('date') or datetime.utcnow().strftime('%Y-%m-%d')
    
    labours = []
    if selected_site_id:
        labours = list(db.labours.find({'site_id': selected_site_id, 'status': 'active'}))
        # Find existing attendance
        existing_att = {
            str(att['ref_id']): att 
            for att in db.attendance.find({'employee_type': 'Labour', 'date': date_str})
        }
        for l in labours:
            l['att_record'] = existing_att.get(str(l['_id']), {'status': 'Absent', 'working_hours': 0.0, 'overtime': 0.0})
            
    if request.method == 'POST' and selected_site_id:
        labor_ids = request.form.getlist('labor_ids')
        for lid_str in labor_ids:
            lid = to_object_id(lid_str)
            status = request.form.get(f'status_{lid_str}', 'Absent')
            hours = float(request.form.get(f'hours_{lid_str}', 8.0) or 8)
            ot = float(request.form.get(f'ot_{lid_str}', 0.0) or 0)
            
            # calculate wage
            l_doc = db.labours.find_one({'_id': lid})
            daily_w = l_doc.get('daily_wage', 0.0) if l_doc else 0.0
            
            # rate calculations: Half Day gets 0.5, Present gets 1.0, overtime gets extra hourly rate
            base_wage = 0.0
            if status == 'Present':
                base_wage = daily_w
            elif status == 'Half Day':
                base_wage = daily_w * 0.5
                
            hourly_rate = daily_w / 8.0
            ot_wage = ot * hourly_rate * 1.5 # 1.5x OT multiplier
            total_wage = base_wage + ot_wage
            
            db.attendance.update_one(
                {
                    'employee_type': 'Labour',
                    'ref_id': lid,
                    'date': date_str
                },
                {'$set': {
                    'status': status,
                    'working_hours': hours,
                    'overtime': ot,
                    'wage_earned': total_wage,
                    'created_at': datetime.utcnow()
                }},
                upsert=True
            )
            
            # record wage payment transactions
            if total_wage > 0:
                db.payments.update_one(
                    {
                        'reference_type': 'Labour',
                        'reference_id': lid,
                        'payment_date': date_str
                    },
                    {'$set': {
                        'amount': total_wage,
                        'payment_method': 'cash',
                        'payment_status': 'paid'
                    }},
                    upsert=True
                )
                
        flash(f"Labour attendance recorded for {date_str}!", "success")
        return redirect(url_for('labour.log_attendance', site_id=selected_site_id))
        
    return render_template('labour/attendance.html', sites=sites, selected_site_id=selected_site_id, labours=labours, date=date_str)
