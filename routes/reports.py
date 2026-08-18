from flask import Blueprint, render_template, request, session, jsonify
from database.mongodb import get_db
from utils.decorators import login_required, role_required
from utils.constants import Roles
from utils.helpers import to_object_id
from datetime import datetime, timedelta

reports_bp = Blueprint('reports', __name__, url_prefix='/reports')

@reports_bp.route('/')
@login_required
def index():
    db = get_db()
    projects = list(db.projects.find())
    return render_template('reports/dashboard.html', projects=projects)

@reports_bp.route('/data')
@login_required
def get_report_data():
    db = get_db()
    project_id = to_object_id(request.args.get('project_id'))
    date_filter = request.args.get('date_filter', 'this_month')
    
    # 1. Date Range filtering
    end_date = datetime.utcnow()
    if date_filter == 'today':
        start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
    elif date_filter == 'this_week':
        start_date = end_date - timedelta(days=7)
    elif date_filter == 'this_month':
        start_date = end_date - timedelta(days=30)
    elif date_filter == 'this_year':
        start_date = end_date - timedelta(days=365)
    else: # default to all time / custom
        start_date = datetime(2000, 1, 1)
        
    query_p = {}
    query_e = {'expense_date': {'$gte': start_date.strftime('%Y-%m-%d'), '$lte': end_date.strftime('%Y-%m-%d')}}
    
    if project_id:
        query_p['_id'] = project_id
        query_e['project_id'] = project_id
        
    # Project progress and budgets
    projects = list(db.projects.find(query_p))
    project_names = [p['name'] for p in projects]
    project_progress = [p.get('progress', 0) for p in projects]
    project_budgets = [p.get('budget', 0.0) for p in projects]
    
    # Category-wise expenses
    expenses = list(db.expenses.find(query_e))
    categories = ['Material', 'Labour', 'Equipment', 'Subcontractor', 'Transport', 'Maintenance', 'Other']
    expense_data = {cat: 0.0 for cat in categories}
    for e in expenses:
        cat = e.get('category', 'Other')
        expense_data[cat] = expense_data.get(cat, 0.0) + e.get('amount', 0.0)
        
    # Actual cost vs Budget per project
    actual_project_costs = []
    for p in projects:
        p_exps = list(db.expenses.find({'project_id': p['_id'], 'status': 'approved'}))
        actual_project_costs.append(sum([e.get('amount', 0.0) for e in p_exps]))
        
    # Material consumption levels
    materials = list(db.materials.find().limit(10))
    material_names = [m['name'] for m in materials]
    material_stocks = []
    for m in materials:
        inventory_items = list(db.inventory.find({'material_id': m['_id']}))
        material_stocks.append(sum([item.get('quantity', 0.0) for item in inventory_items]))
        
    # Client invoices vs payments
    invoices = list(db.invoices.find())
    total_invoiced = sum([inv.get('total_amount', 0.0) for inv in invoices])
    payments = list(db.payments.find({'payment_status': 'paid'}))
    total_revenue = sum([p.get('amount', 0.0) for p in payments if p.get('reference_type') == 'Invoice'])
    
    profitability = {
        'revenue': total_revenue,
        'expenses': sum([e.get('amount', 0.0) for e in db.expenses.find({'status': 'approved'})])
    }
    
    return jsonify({
        'projects': project_names,
        'progress': project_progress,
        'budgets': project_budgets,
        'actual_costs': actual_project_costs,
        'expenses_categories': {
            'labels': list(expense_data.keys()),
            'values': list(expense_data.values())
        },
        'materials': {
            'labels': material_names,
            'stocks': material_stocks
        },
        'financials': {
            'invoiced': total_invoiced,
            'collected': total_revenue
        },
        'profitability': profitability
    })
