from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from utils.decorators import role_required
from utils.constants import Roles, Priority
from services.auth_service import get_customer_by_user_id
from services.job_service import (
    create_service_request, get_service_requests_by_customer, get_jobs_by_customer
)
from services.invoice_service import get_invoices_by_customer, get_invoice_by_id, record_payment
from database.mongodb import get_db
from utils.helpers import to_object_id

customer_bp = Blueprint('customer', __name__, url_prefix='/customer')

@customer_bp.route('/dashboard')
@role_required(Roles.CUSTOMER)
def dashboard():
    """
    Customer portal homepage. Lists requests, jobs, invoices.
    """
    cust = get_customer_by_user_id(session['user_id'])
    if not cust:
        flash("Customer profile not found.", "danger")
        return redirect(url_for('auth.login'))
        
    requests = get_service_requests_by_customer(str(cust['_id']))
    jobs = get_jobs_by_customer(str(cust['_id']))
    invoices = get_invoices_by_customer(str(cust['_id']))
    
    return render_template(
        'customer/dashboard.html', 
        requests=requests, 
        jobs=jobs, 
        invoices=invoices
    )

@customer_bp.route('/requests/new', methods=['GET', 'POST'])
@role_required(Roles.CUSTOMER)
def create_request():
    """
    Handles submitting service requests.
    Supports inputting an address and extracting Leaflet lat/lng parameters.
    """
    cust = get_customer_by_user_id(session['user_id'])
    if not cust:
        flash("Customer profile not found.", "danger")
        return redirect(url_for('auth.login'))
        
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        service_category = request.form.get('service_category', '').strip()
        priority = request.form.get('priority', Priority.MEDIUM)
        address = request.form.get('address', '').strip()
        lat = request.form.get('lat', 0.0)
        lng = request.form.get('lng', 0.0)
        preferred_date = request.form.get('preferred_date')
        
        if not title or not description or not service_category or not address:
            flash("Please fill in all required fields.", "danger")
            return render_template('customer/create_request.html')
            
        create_service_request(
            str(cust['_id']), 
            title, 
            description, 
            service_category, 
            priority, 
            address, 
            lat, 
            lng, 
            preferred_date
        )
        
        flash("Service request submitted successfully! An administrator will review it.", "success")
        return redirect(url_for('customer.dashboard'))
        
    return render_template('customer/create_request.html')

@customer_bp.route('/requests/<req_id>')
@role_required(Roles.CUSTOMER)
def track_request(req_id):
    """
    Displays the status detail of a specific request.
    """
    db = get_db()
    req = db.service_requests.find_one({'_id': to_object_id(req_id)})
    if not req:
        flash("Service request not found.", "danger")
        return redirect(url_for('customer.dashboard'))
        
    # Find matching job if any
    job = db.jobs.find_one({'service_request_id': to_object_id(req_id)})
    
    return render_template('customer/track_request.html', service_request=req, job=job)

@customer_bp.route('/invoices/<invoice_id>/pay', methods=['GET', 'POST'])
@role_required(Roles.CUSTOMER)
def pay_invoice(invoice_id):
    """
    Handles payment submission for invoices.
    """
    invoice = get_invoice_by_id(invoice_id)
    if not invoice:
        flash("Invoice not found.", "danger")
        return redirect(url_for('customer.dashboard'))
        
    if request.method == 'POST':
        amount = request.form.get('amount')
        payment_method = request.form.get('payment_method')
        
        if not amount or not payment_method:
            flash("All billing inputs are required.", "danger")
            return render_template('customer/pay_invoice.html', invoice=invoice)
            
        success, err = record_payment(invoice_id, amount, payment_method)
        if success:
            flash("Payment processed successfully! Invoice updated.", "success")
            return redirect(url_for('customer.dashboard'))
        else:
            flash(err, "danger")
            
    return render_template('customer/pay_invoice.html', invoice=invoice)
