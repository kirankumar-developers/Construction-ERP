from flask import Blueprint, render_template, redirect, url_for, flash, request
from database.mongodb import get_db
from utils.decorators import login_required, role_required
from utils.constants import Roles, PaymentStatus
from utils.helpers import to_object_id
from datetime import datetime

payments_bp = Blueprint('payments', __name__, url_prefix='/payments')

@payments_bp.route('/')
@login_required
def index():
    db = get_db()
    payments = list(db.payments.find().sort('payment_date', -1))
    
    for p in payments:
        ref_id = p.get('reference_id')
        ref_type = p.get('reference_type')
        p['ref_details'] = 'N/A'
        
        if ref_type == 'Invoice' and ref_id:
            inv = db.invoices.find_one({'_id': ref_id})
            if inv:
                p['ref_details'] = f"Client Invoice {inv['invoice_number']}"
        elif ref_type == 'Vendor' and ref_id:
            v = db.vendors.find_one({'_id': ref_id})
            if v:
                p['ref_details'] = f"Supplier payment to {v['company_name']}"
        elif ref_type == 'Subcontractor' and ref_id:
            sub = db.subcontractors.find_one({'_id': ref_id})
            if sub:
                p['ref_details'] = f"Subcontractor payment to {sub['company_name']}"
        elif ref_type == 'Labour' and ref_id:
            l = db.labours.find_one({'_id': ref_id})
            if l:
                p['ref_details'] = f"Wages payment to {l['name']} ({l['labour_id']})"
                
    return render_template('finance/payment_list.html', payments=payments)

@payments_bp.route('/add', methods=['GET', 'POST'])
@login_required
@role_required(Roles.SUPER_ADMIN, Roles.ADMIN, Roles.PROJECT_MANAGER)
def add():
    db = get_db()
    invoices = list(db.invoices.find({'status': {'$ne': 'paid'}}))
    vendors = list(db.vendors.find())
    subcontractors = list(db.subcontractors.find())
    
    if request.method == 'POST':
        ref_type = request.form.get('reference_type') # Invoice, Vendor, Subcontractor
        amount = float(request.form.get('amount', 0.0) or 0)
        method = request.form.get('payment_method', 'bank_transfer')
        date_str = request.form.get('payment_date') or datetime.utcnow().strftime('%Y-%m-%d')
        
        ref_id = None
        if ref_type == 'Invoice':
            ref_id = to_object_id(request.form.get('invoice_id'))
        elif ref_type == 'Vendor':
            ref_id = to_object_id(request.form.get('vendor_id'))
        elif ref_type == 'Subcontractor':
            ref_id = to_object_id(request.form.get('subcontractor_id'))
            
        if not ref_type or amount <= 0 or not ref_id:
            flash("All fields and positive amount are required.", "danger")
            return redirect(url_for('payments.add'))
            
        db.payments.insert_one({
            'reference_type': ref_type,
            'reference_id': ref_id,
            'amount': amount,
            'payment_method': method,
            'payment_status': 'paid',
            'payment_date': date_str,
            'created_at': datetime.utcnow()
        })
        
        # update states
        if ref_type == 'Invoice':
            db.invoices.update_one({'_id': ref_id}, {'$set': {'status': 'paid'}})
        elif ref_type == 'Vendor':
            db.vendors.update_one({'_id': ref_id}, {'$inc': {'outstanding_amount': -amount}})
            
        flash("Payment recorded successfully!", "success")
        return redirect(url_for('payments.index'))
        
    return render_template('finance/add_payment.html', invoices=invoices, vendors=vendors, subcontractors=subcontractors)
