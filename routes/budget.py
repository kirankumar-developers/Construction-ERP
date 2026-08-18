from flask import Blueprint, render_template, redirect, url_for, flash, request
from database.mongodb import get_db
from utils.decorators import login_required, role_required
from utils.constants import Roles, ExpenseStatus
from utils.helpers import to_object_id
from datetime import datetime

budget_bp = Blueprint('budget', __name__, url_prefix='/budget')

@budget_bp.route('/')
@login_required
def index():
    db = get_db()
    projects = list(db.projects.find())
    
    # Calculate budget summary for each project
    for p in projects:
        # Category budgets
        budgets = list(db.budgets.find({'project_id': p['_id']}))
        p['budget_categories'] = {b['category']: b['amount'] for b in budgets}
        p['total_budget'] = sum([b['amount'] for b in budgets])
        
        # Calculate actual cost per category
        expenses = list(db.expenses.find({'project_id': p['_id'], 'status': ExpenseStatus.APPROVED}))
        p['actual_categories'] = {}
        for e in expenses:
            cat = e.get('category', 'Other')
            p['actual_categories'][cat] = p['actual_categories'].get(cat, 0.0) + e.get('amount', 0.0)
            
        p['total_actual'] = sum([e.get('amount', 0.0) for e in expenses])
        p['variance'] = p['total_budget'] - p['total_actual']
        p['overrun'] = p['total_actual'] > p['total_budget'] if p['total_budget'] > 0 else False
        
    return render_template('budget/list.html', projects=projects)

@budget_bp.route('/manage/<project_id>', methods=['GET', 'POST'])
@login_required
@role_required(Roles.SUPER_ADMIN, Roles.ADMIN, Roles.PROJECT_MANAGER)
def manage(project_id):
    db = get_db()
    poid = to_object_id(project_id)
    project = db.projects.find_one({'_id': poid})
    if not project:
        flash("Project not found.", "danger")
        return redirect(url_for('budget.index'))
        
    categories = ['Material', 'Labour', 'Equipment', 'Subcontractor', 'Transport', 'Maintenance', 'Other']
    
    if request.method == 'POST':
        for cat in categories:
            val = float(request.form.get(f'budget_{cat}', 0.0) or 0)
            db.budgets.update_one(
                {'project_id': poid, 'category': cat},
                {'$set': {'amount': val}},
                upsert=True
            )
            
        # Update project total budget field as helper
        total_b = sum([float(request.form.get(f'budget_{cat}', 0.0) or 0) for cat in categories])
        db.projects.update_one({'_id': poid}, {'$set': {'budget': total_b}})
        
        flash("Budgets updated successfully!", "success")
        return redirect(url_for('budget.index'))
        
    # Fetch existing budgets
    existing = {b['category']: b['amount'] for b in db.budgets.find({'project_id': poid})}
    
    return render_template('budget/manage.html', project=project, categories=categories, existing=existing)
