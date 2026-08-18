from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from database.mongodb import get_db
from utils.decorators import login_required, role_required
from utils.constants import Roles, ExpenseStatus
from utils.helpers import to_object_id
from services.upload_service import upload_file
from bson import ObjectId
from datetime import datetime

expenses_bp = Blueprint('expenses', __name__, url_prefix='/expenses')

@expenses_bp.route('/')
@login_required
def index():
    db = get_db()
    role = session.get('role')
    user_id = to_object_id(session.get('user_id'))
    
    if role in [Roles.SUPER_ADMIN, Roles.ADMIN]:
        expenses = list(db.expenses.find())
    elif role == Roles.PROJECT_MANAGER:
        projects = list(db.projects.find({'manager_id': user_id}))
        pids = [p['_id'] for p in projects]
        expenses = list(db.expenses.find({'project_id': {'$in': pids}}))
    else:
        expenses = list(db.expenses.find({'created_by': user_id}))
        
    for e in expenses:
        p = db.projects.find_one({'_id': e.get('project_id')})
        s = db.sites.find_one({'_id': e.get('site_id')})
        e['project_name'] = p['name'] if p else 'N/A'
        e['site_name'] = s['name'] if s else 'N/A'
        
    return render_template('finance/expense_list.html', expenses=expenses, ExpenseStatus=ExpenseStatus, Roles=Roles)

@expenses_bp.route('/add', methods=['GET', 'POST'])
@login_required
@role_required(Roles.SUPER_ADMIN, Roles.ADMIN, Roles.PROJECT_MANAGER, Roles.SITE_ENGINEER)
def add():
    db = get_db()
    projects = list(db.projects.find())
    sites = list(db.sites.find())
    
    if request.method == 'POST':
        project_id = to_object_id(request.form.get('project_id'))
        site_id = to_object_id(request.form.get('site_id'))
        amount = float(request.form.get('amount', 0.0) or 0)
        category = request.form.get('category', 'Other')
        desc = request.form.get('description', '').strip()
        date_str = request.form.get('expense_date') or datetime.utcnow().strftime('%Y-%m-%d')
        file = request.files.get('receipt')
        
        if not project_id or not site_id or amount <= 0:
            flash("Project, Site, and Positive Amount are required.", "danger")
            return redirect(url_for('expenses.add'))
            
        file_path = None
        if file and file.filename:
            file_path, err = upload_file(file)
            if err:
                flash(err, "danger")
                return redirect(url_for('expenses.add'))
                
        # auto-approve if submitted by Admin/PM
        status = ExpenseStatus.APPROVED if session.get('role') in [Roles.ADMIN, Roles.SUPER_ADMIN, Roles.PROJECT_MANAGER] else ExpenseStatus.PENDING
        
        db.expenses.insert_one({
            'project_id': project_id,
            'site_id': site_id,
            'amount': amount,
            'category': category,
            'description': desc,
            'expense_date': date_str,
            'receipt_image': file_path,
            'status': status,
            'created_by': to_object_id(session.get('user_id')),
            'created_at': datetime.utcnow()
        })
        
        flash("Expense recorded successfully!", "success")
        return redirect(url_for('expenses.index'))
        
    return render_template('finance/add_expense.html', projects=projects, sites=sites)

@expenses_bp.route('/approve/<expense_id>', methods=['POST'])
@login_required
@role_required(Roles.SUPER_ADMIN, Roles.ADMIN, Roles.PROJECT_MANAGER)
def approve(expense_id):
    db = get_db()
    oid = to_object_id(expense_id)
    action = request.form.get('action') # approve, reject
    
    status = ExpenseStatus.APPROVED if action == 'approve' else ExpenseStatus.REJECTED
    db.expenses.update_one({'_id': oid}, {'$set': {'status': status}})
    
    flash(f"Expense has been {status}.", "success")
    return redirect(url_for('expenses.index'))
