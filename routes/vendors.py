from flask import Blueprint, render_template, redirect, url_for, flash, request
from database.mongodb import get_db
from utils.decorators import login_required, role_required
from utils.constants import Roles
from utils.helpers import to_object_id
from datetime import datetime

vendors_bp = Blueprint('vendors', __name__, url_prefix='/vendors')

@vendors_bp.route('/')
@login_required
def index():
    db = get_db()
    vendors = list(db.vendors.find())
    return render_template('vendors/list.html', vendors=vendors)

@vendors_bp.route('/view/<vendor_id>')
@login_required
def view(vendor_id):
    db = get_db()
    oid = to_object_id(vendor_id)
    if not oid:
        flash("Invalid vendor ID.", "danger")
        return redirect(url_for('vendors.index'))
        
    vendor = db.vendors.find_one({'_id': oid})
    if not vendor:
        flash("Vendor not found.", "danger")
        return redirect(url_for('vendors.index'))
        
    # Fetch PO history
    orders = list(db.purchase_orders.find({'vendor_id': oid}))
    for o in orders:
        p = db.projects.find_one({'_id': o.get('project_id')})
        o['project_name'] = p['name'] if p else 'N/A'
        
    return render_template('vendors/view.html', vendor=vendor, orders=orders)
