from flask import Blueprint, render_template, redirect, url_for, session
from database.mongodb import get_db
from utils.decorators import login_required
from utils.constants import Roles, ProjectStatus, TaskStatus, IssueStatus, POStatus, ExpenseStatus
from bson import ObjectId
from datetime import datetime

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/dashboard')
@login_required
def index():
    db = get_db()
    role = session.get('role')
    user_id = ObjectId(session.get('user_id'))
    
    if role == Roles.SUPER_ADMIN:
        # Super Admin Analytics
        total_users = db.users.count_documents({})
        total_projects = db.projects.count_documents({})
        active_projects = db.projects.count_documents({'status': ProjectStatus.ACTIVE})
        completed_projects = db.projects.count_documents({'status': ProjectStatus.COMPLETED})
        
        # Calculate financials
        payments = list(db.payments.find({'payment_status': 'paid'}))
        total_revenue = sum([p.get('amount', 0.0) for p in payments if p.get('reference_type') == 'Invoice'])
        
        expenses = list(db.expenses.find({'status': ExpenseStatus.APPROVED}))
        total_expenses = sum([e.get('amount', 0.0) for e in expenses])
        
        recent_activity = list(db.activity_logs.find().sort('timestamp', -1).limit(10))
        for act in recent_activity:
            u = db.users.find_one({'_id': act.get('user_id')})
            act['user_name'] = u.get('name') if u else 'System'
            
        return render_template('dashboard/super_admin.html',
                               total_users=total_users,
                               total_projects=total_projects,
                               active_projects=active_projects,
                               completed_projects=completed_projects,
                               total_revenue=total_revenue,
                               total_expenses=total_expenses,
                               recent_activity=recent_activity)
                               
    elif role == Roles.ADMIN:
        # Admin Analytics
        projects_count = db.projects.count_documents({})
        sites_count = db.sites.count_documents({})
        employees_count = db.employees.count_documents({})
        labour_count = db.labours.count_documents({})
        
        pending_requests = db.material_requests.count_documents({'status': 'pending'})
        pending_expenses = db.expenses.count_documents({'status': ExpenseStatus.PENDING})
        pending_approvals = pending_requests + pending_expenses
        
        # Aggregate stocks
        inventory_items = list(db.inventory.find())
        stock_count = sum([item.get('quantity', 0) for item in inventory_items])
        
        expenses = list(db.expenses.find({'status': ExpenseStatus.APPROVED}))
        total_expenses = sum([e.get('amount', 0.0) for e in expenses])
        
        payments = list(db.payments.find({'payment_status': 'paid'}))
        total_payments = sum([p.get('amount', 0.0) for p in payments])
        
        return render_template('dashboard/admin.html',
                               projects_count=projects_count,
                               sites_count=sites_count,
                               employees_count=employees_count,
                               labour_count=labour_count,
                               pending_approvals=pending_approvals,
                               stock_count=stock_count,
                               total_expenses=total_expenses,
                               total_payments=total_payments)
                               
    elif role == Roles.PROJECT_MANAGER:
        # PM Analytics
        assigned_projects = list(db.projects.find({'manager_id': user_id}))
        project_ids = [p['_id'] for p in assigned_projects]
        
        projects_count = len(assigned_projects)
        delayed_tasks = db.tasks.count_documents({
            'project_id': {'$in': project_ids},
            'status': TaskStatus.DELAYED
        })
        
        # Budget vs Actual logic for projects
        total_budget = sum([p.get('budget', 0.0) for p in assigned_projects])
        expenses = list(db.expenses.find({'project_id': {'$in': project_ids}, 'status': ExpenseStatus.APPROVED}))
        actual_cost = sum([e.get('amount', 0.0) for e in expenses])
        
        pending_issues = db.issues.count_documents({
            'project_id': {'$in': project_ids},
            'status': {'$ne': IssueStatus.CLOSED}
        })
        
        pending_dprs = db.dpr.count_documents({
            'project_id': {'$in': project_ids},
            'status': 'pending'
        })
        
        return render_template('dashboard/project_manager.html',
                               assigned_projects=assigned_projects,
                               projects_count=projects_count,
                               delayed_tasks=delayed_tasks,
                               total_budget=total_budget,
                               actual_cost=actual_cost,
                               pending_issues=pending_issues,
                               pending_dprs=pending_dprs)
                               
    elif role == Roles.SITE_ENGINEER:
        # Site Engineer Analytics
        assigned_sites = list(db.sites.find({'engineer_id': user_id}))
        site_ids = [s['_id'] for s in assigned_sites]
        
        # Today's tasks
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_tasks = list(db.tasks.find({
            'site_id': {'$in': site_ids},
            'status': {'$in': [TaskStatus.NOT_STARTED, TaskStatus.IN_PROGRESS]}
        }))
        
        today_dpr = db.dpr.find_one({
            'site_id': {'$in': site_ids},
            'date': today_start.strftime('%Y-%m-%d')
        })
        dpr_submitted = True if today_dpr else False
        
        # Labour count on site today
        labour_on_site = db.labours.count_documents({
            'site_id': {'$in': site_ids},
            'status': 'active'
        })
        
        pending_requests = db.material_requests.count_documents({
            'site_id': {'$in': site_ids},
            'status': 'pending'
        })
        
        open_issues = db.issues.count_documents({
            'site_id': {'$in': site_ids},
            'status': {'$in': [IssueStatus.OPEN, IssueStatus.ASSIGNED, IssueStatus.IN_PROGRESS]}
        })
        
        return render_template('dashboard/site_engineer.html',
                               assigned_sites=assigned_sites,
                               today_tasks=today_tasks,
                               dpr_submitted=dpr_submitted,
                               labour_on_site=labour_on_site,
                               pending_requests=pending_requests,
                               open_issues=open_issues)
                               
    elif role in [Roles.EMPLOYEE, Roles.SUPERVISOR]:
        # Employee / Supervisor Dashboard
        assigned_tasks = list(db.tasks.find({
            'assigned_employee_ids': user_id
        }))
        
        pending_tasks_count = sum(1 for t in assigned_tasks if t.get('status') != TaskStatus.COMPLETED)
        completed_tasks_count = sum(1 for t in assigned_tasks if t.get('status') == TaskStatus.COMPLETED)
        
        # Attendance today
        today_str = datetime.utcnow().strftime('%Y-%m-%d')
        attendance_today = db.attendance.find_one({
            'employee_type': 'Employee',
            'ref_id': user_id,
            'date': today_str
        })
        
        return render_template('dashboard/employee.html',
                               assigned_tasks=assigned_tasks,
                               pending_tasks_count=pending_tasks_count,
                               completed_tasks_count=completed_tasks_count,
                               attendance_today=attendance_today)
                               
    elif role == Roles.CLIENT:
        # Client Dashboard
        client = db.clients.find_one({'user_id': user_id})
        projects = []
        invoices = []
        if client:
            projects = list(db.projects.find({'client_id': client['_id']}))
            project_ids = [p['_id'] for p in projects]
            invoices = list(db.invoices.find({'project_id': {'$in': project_ids}}))
            
        total_invoiced = sum([inv.get('total_amount', 0.0) for inv in invoices])
        total_paid = sum([inv.get('total_amount', 0.0) for inv in invoices if inv.get('status') == 'paid'])
        outstanding = total_invoiced - total_paid
        
        return render_template('dashboard/client.html',
                               client=client,
                               projects=projects,
                               invoices=invoices,
                               total_invoiced=total_invoiced,
                               total_paid=total_paid,
                               outstanding=outstanding)
                               
    elif role == Roles.VENDOR:
        # Vendor Dashboard
        vendor = db.vendors.find_one({'user_id': user_id})
        rfqs = []
        quotations = []
        purchase_orders = []
        if vendor:
            rfqs = list(db.rfqs.find({'vendor_ids': vendor['_id']}))
            quotations = list(db.vendor_quotations.find({'vendor_id': vendor['_id']}))
            purchase_orders = list(db.purchase_orders.find({'vendor_id': vendor['_id']}))
            
        pending_quotes_count = len(rfqs) - len(quotations)
        approved_po_count = sum(1 for po in purchase_orders if po.get('status') == POStatus.APPROVED)
        
        return render_template('dashboard/vendor.html',
                               vendor=vendor,
                               rfqs=rfqs,
                               quotations=quotations,
                               purchase_orders=purchase_orders,
                               pending_quotes_count=pending_quotes_count,
                               approved_po_count=approved_po_count)
                               
    elif role == Roles.SUBCONTRACTOR:
        # Subcontractor Dashboard
        subcontractor = db.subcontractors.find_one({'user_id': user_id})
        work_orders = []
        if subcontractor:
            work_orders = list(db.work_orders.find({'subcontractor_id': subcontractor['_id']}))
            
        wo_count = len(work_orders)
        active_wo_count = sum(1 for wo in work_orders if wo.get('status') == 'In Progress')
        contract_value = subcontractor.get('contract_value', 0.0) if subcontractor else 0.0
        
        return render_template('dashboard/subcontractor.html',
                               subcontractor=subcontractor,
                               work_orders=work_orders,
                               wo_count=wo_count,
                               active_wo_count=active_wo_count,
                               contract_value=contract_value)
                               
    elif role == Roles.LABOUR:
        # Labour dashboard (attendance and wages)
        labour = db.labours.find_one({'user_id': user_id})
        attendance_logs = []
        if labour:
            attendance_logs = list(db.attendance.find({
                'employee_type': 'Labour',
                'ref_id': labour['_id']
            }).sort('date', -1).limit(30))
            
        return render_template('dashboard/labour.html',
                               labour=labour,
                               attendance_logs=attendance_logs)
                               
    return redirect(url_for('auth.login'))
