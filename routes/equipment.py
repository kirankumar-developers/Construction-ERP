from flask import Blueprint, render_template, redirect, url_for, flash, request
from database.mongodb import get_db
from utils.decorators import login_required, role_required
from utils.constants import Roles, EquipmentStatus
from utils.helpers import to_object_id, generate_equipment_id
from bson import ObjectId
from datetime import datetime

equipment_bp = Blueprint('equipment', __name__, url_prefix='/equipment')

@equipment_bp.route('/')
@login_required
def index():
    db = get_db()
    equipments = list(db.equipment.find())
    for eq in equipments:
        p = db.projects.find_one({'_id': eq.get('project_id')})
        s = db.sites.find_one({'_id': eq.get('site_id')})
        eq['project_name'] = p['name'] if p else 'N/A'
        eq['site_name'] = s['name'] if s else 'N/A'
    return render_template('equipment/list.html', equipment=equipments)

@equipment_bp.route('/add', methods=['GET', 'POST'])
@login_required
@role_required(Roles.SUPER_ADMIN, Roles.ADMIN, Roles.PROJECT_MANAGER)
def add():
    db = get_db()
    projects = list(db.projects.find())
    sites = list(db.sites.find())
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        category = request.form.get('category', 'Excavator').strip()
        eq_type = request.form.get('type', 'Purchase')
        cost = float(request.form.get('daily_cost', 0.0) or 0)
        project_id = to_object_id(request.form.get('project_id'))
        site_id = to_object_id(request.form.get('site_id'))
        
        if not name:
            flash("Equipment Name is required.", "danger")
            return redirect(url_for('equipment.add'))
            
        eq_id = generate_equipment_id()
        db.equipment.insert_one({
            'equipment_id': eq_id,
            'name': name,
            'category': category,
            'type': eq_type,
            'daily_cost': cost,
            'project_id': project_id,
            'site_id': site_id,
            'status': EquipmentStatus.AVAILABLE,
            'created_at': datetime.utcnow()
        })
        
        flash("Equipment registered successfully!", "success")
        return redirect(url_for('equipment.index'))
        
    return render_template('equipment/add.html', projects=projects, sites=sites, EquipmentStatus=EquipmentStatus)

@equipment_bp.route('/maintenance/<equipment_id>', methods=['GET', 'POST'])
@login_required
@role_required(Roles.SUPER_ADMIN, Roles.ADMIN, Roles.PROJECT_MANAGER, Roles.SITE_ENGINEER)
def maintenance(equipment_id):
    db = get_db()
    oid = to_object_id(equipment_id)
    eq = db.equipment.find_one({'_id': oid})
    if not eq:
        flash("Equipment not found.", "danger")
        return redirect(url_for('equipment.index'))
        
    if request.method == 'POST':
        desc = request.form.get('description', '').strip()
        cost = float(request.form.get('cost', 0.0) or 0)
        date_str = request.form.get('date') or datetime.utcnow().strftime('%Y-%m-%d')
        
        db.equipment_maintenance.insert_one({
            'equipment_id': oid,
            'date': date_str,
            'description': desc,
            'cost': cost,
            'created_at': datetime.utcnow()
        })
        
        # update status to maintenance
        db.equipment.update_one({'_id': oid}, {'$set': {'status': EquipmentStatus.MAINTENANCE}})
        
        # log expense
        db.expenses.insert_one({
            'expense_date': date_str,
            'amount': cost,
            'project_id': eq.get('project_id'),
            'site_id': eq.get('site_id'),
            'category': 'Maintenance',
            'description': f"Maintenance for {eq['name']} ({eq['equipment_id']}): {desc}",
            'status': 'approved',
            'created_at': datetime.utcnow()
        })
        
        flash("Maintenance record saved!", "success")
        return redirect(url_for('equipment.index'))
        
    records = list(db.equipment_maintenance.find({'equipment_id': oid}).sort('date', -1))
    return render_template('equipment/maintenance.html', equipment=eq, records=records)
