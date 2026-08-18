from flask import Blueprint, render_template, redirect, url_for, flash, request
from database.mongodb import get_db
from utils.decorators import login_required, role_required
from utils.constants import Roles
from utils.helpers import to_object_id, generate_boq_number
from bson import ObjectId
from datetime import datetime

boq_bp = Blueprint('boq', __name__, url_prefix='/boq')

@boq_bp.route('/')
@login_required
def index():
    db = get_db()
    boqs = list(db.boq.find())
    for b in boqs:
        p = db.projects.find_one({'_id': b.get('project_id')})
        b['project_name'] = p['name'] if p else 'N/A'
        
        # Calculate consumed actual costs from expenses
        actual_expenses = list(db.expenses.find({'project_id': b.get('project_id'), 'status': 'approved'}))
        b['actual_cost'] = sum([e.get('amount', 0.0) for e in actual_expenses])
        b['remaining_amount'] = b.get('total_amount', 0.0) - b['actual_cost']
        
    return render_template('boq/list.html', boqs=boqs)

@boq_bp.route('/add', methods=['GET', 'POST'])
@login_required
@role_required(Roles.SUPER_ADMIN, Roles.ADMIN, Roles.PROJECT_MANAGER)
def add():
    db = get_db()
    projects = list(db.projects.find())
    
    if request.method == 'POST':
        project_id = to_object_id(request.form.get('project_id'))
        category = request.form.get('category', 'Civil Work').strip()
        
        # Parse items
        item_descriptions = request.form.getlist('description[]')
        item_units = request.form.getlist('unit[]')
        item_quantities = request.form.getlist('quantity[]')
        item_rates = request.form.getlist('rate[]')
        
        if not project_id or not item_descriptions:
            flash("Project and at least one item description are required.", "danger")
            return redirect(url_for('boq.add'))
            
        items = []
        total_amount = 0.0
        
        for i in range(len(item_descriptions)):
            desc = item_descriptions[i].strip()
            if not desc:
                continue
            unit = item_units[i].strip()
            qty = float(item_quantities[i] or 0)
            rate = float(item_rates[i] or 0)
            amt = qty * rate
            total_amount += amt
            
            items.append({
                'item_id': str(ObjectId()),
                'description': desc,
                'unit': unit,
                'quantity': qty,
                'rate': rate,
                'amount': amt
            })
            
        boq_no = generate_boq_number()
        boq_doc = {
            'boq_number': boq_no,
            'project_id': project_id,
            'category': category,
            'items': items,
            'total_amount': total_amount,
            'created_at': datetime.utcnow()
        }
        
        db.boq.insert_one(boq_doc)
        flash(f"BOQ {boq_no} created successfully!", "success")
        return redirect(url_for('boq.index'))
        
    return render_template('boq/add.html', projects=projects)

@boq_bp.route('/view/<boq_id>')
@login_required
def view(boq_id):
    db = get_db()
    oid = to_object_id(boq_id)
    if not oid:
        flash("Invalid BOQ ID.", "danger")
        return redirect(url_for('boq.index'))
        
    boq = db.boq.find_one({'_id': oid})
    if not boq:
        flash("BOQ not found.", "danger")
        return redirect(url_for('boq.index'))
        
    p = db.projects.find_one({'_id': boq.get('project_id')})
    boq['project_name'] = p['name'] if p else 'N/A'
    
    # Calculate actual consumed cost
    actual_expenses = list(db.expenses.find({'project_id': boq.get('project_id'), 'status': 'approved'}))
    actual_cost = sum([e.get('amount', 0.0) for e in actual_expenses])
    remaining = boq.get('total_amount', 0.0) - actual_cost
    
    return render_template('boq/view.html', boq=boq, actual_cost=actual_cost, remaining=remaining)
