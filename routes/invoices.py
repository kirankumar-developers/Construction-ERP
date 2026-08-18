from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from database.mongodb import get_db
from utils.decorators import login_required, role_required
from utils.constants import Roles, InvoiceStatus
from utils.helpers import to_object_id
from services.invoice_service import create_client_invoice
from bson import ObjectId
from datetime import datetime

invoices_bp = Blueprint('invoices', __name__, url_prefix='/invoices')

@invoices_bp.route('/')
@login_required
def index():
    db = get_db()
    role = session.get('role')
    user_id = to_object_id(session.get('user_id'))
    
    if role in [Roles.SUPER_ADMIN, Roles.ADMIN]:
        invoices = list(db.invoices.find())
    elif role == Roles.PROJECT_MANAGER:
        projects = list(db.projects.find({'manager_id': user_id}))
        pids = [p['_id'] for p in projects]
        invoices = list(db.invoices.find({'project_id': {'$in': pids}}))
    elif role == Roles.CLIENT:
        c = db.clients.find_one({'user_id': user_id})
        invoices = list(db.invoices.find({'client_id': c['_id']})) if c else []
    else:
        invoices = []
        
    for inv in invoices:
        p = db.projects.find_one({'_id': inv.get('project_id')})
        c = db.clients.find_one({'_id': inv.get('client_id')})
        inv['project_name'] = p['name'] if p else 'N/A'
        inv['client_name'] = c['company_name'] if c else 'N/A'
        
    return render_template('invoices/list.html', invoices=invoices, Roles=Roles)

@invoices_bp.route('/add', methods=['GET', 'POST'])
@login_required
@role_required(Roles.SUPER_ADMIN, Roles.ADMIN, Roles.PROJECT_MANAGER)
def add():
    db = get_db()
    projects = list(db.projects.find())
    clients = list(db.clients.find())
    
    if request.method == 'POST':
        project_id = request.form.get('project_id')
        client_id = request.form.get('client_id')
        tax_rate = float(request.form.get('tax_rate', 18.0) or 18)
        
        # parse items
        descriptions = request.form.getlist('description[]')
        quantities = request.form.getlist('quantity[]')
        rates = request.form.getlist('rate[]')
        
        items = []
        for i in range(len(descriptions)):
            desc = descriptions[i].strip()
            qty = float(quantities[i] or 0)
            rate = float(rates[i] or 0)
            if desc and qty > 0:
                items.append({
                    'description': desc,
                    'quantity': qty,
                    'rate': rate
                })
                
        if not project_id or not client_id or not items:
            flash("Project, Client, and at least one item are required.", "danger")
            return redirect(url_for('invoices.add'))
            
        create_client_invoice(project_id, client_id, items, tax_rate)
        flash("Invoice generated successfully!", "success")
        return redirect(url_for('invoices.index'))
        
    return render_template('invoices/create.html', projects=projects, clients=clients)

@invoices_bp.route('/view/<invoice_id>')
@login_required
def view(invoice_id):
    db = get_db()
    oid = to_object_id(invoice_id)
    if not oid:
        flash("Invalid invoice ID.", "danger")
        return redirect(url_for('invoices.index'))
        
    invoice = db.invoices.find_one({'_id': oid})
    if not invoice:
        flash("Invoice not found.", "danger")
        return redirect(url_for('invoices.index'))
        
    p = db.projects.find_one({'_id': invoice.get('project_id')})
    c = db.clients.find_one({'_id': invoice.get('client_id')})
    invoice['project_name'] = p['name'] if p else 'N/A'
    invoice['client_name'] = c['company_name'] if c else 'N/A'
    invoice['client_address'] = c['address'] if c else ''
    invoice['client_phone'] = c['phone'] if c else ''
    
    return render_template('invoices/view.html', invoice=invoice)

@invoices_bp.route('/po/bill/<po_id>', methods=['POST'])
@login_required
@role_required(Roles.VENDOR)
def submit_bill(po_id):
    db = get_db()
    po_oid = to_object_id(po_id)
    po = db.purchase_orders.find_one({'_id': po_oid})
    if not po:
        flash("Purchase Order not found.", "danger")
        return redirect(url_for('procurement.po_list'))
        
    db.purchase_orders.update_one({'_id': po_oid}, {'$set': {'bill_submitted': True, 'bill_date': datetime.utcnow()}})
    flash("Invoice/Bill submitted to the client successfully!", "success")
    return redirect(url_for('procurement.po_list'))
