from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from database.mongodb import get_db
from utils.decorators import login_required, role_required
from utils.constants import Roles, IndentStatus, RFQStatus, QuoteStatus, POStatus
from utils.helpers import (
    to_object_id, generate_request_number, generate_rfq_number,
    generate_po_number, generate_grn_number
)
from services.inventory_service import update_stock
from bson import ObjectId
from datetime import datetime

procurement_bp = Blueprint('procurement', __name__, url_prefix='/procurement')

# ----------------- 1. INDENT / MATERIAL REQUESTS -----------------
@procurement_bp.route('/')
@login_required
def index():
    db = get_db()
    role = session.get('role')
    user_id = to_object_id(session.get('user_id'))
    
    if role in [Roles.SUPER_ADMIN, Roles.ADMIN]:
        requests_list = list(db.material_requests.find().sort('created_at', -1))
    elif role == Roles.PROJECT_MANAGER:
        projects = list(db.projects.find({'manager_id': user_id}))
        pids = [p['_id'] for p in projects]
        requests_list = list(db.material_requests.find({'project_id': {'$in': pids}}).sort('created_at', -1))
    elif role == Roles.SITE_ENGINEER:
        requests_list = list(db.material_requests.find({'requested_by': user_id}).sort('created_at', -1))
    else:
        requests_list = []
        
    for r in requests_list:
        p = db.projects.find_one({'_id': r.get('project_id')})
        s = db.sites.find_one({'_id': r.get('site_id')})
        req = db.users.find_one({'_id': r.get('requested_by')})
        r['project_name'] = p['name'] if p else 'N/A'
        r['site_name'] = s['name'] if s else 'N/A'
        r['requested_by_name'] = req['name'] if req else 'N/A'
        
    return render_template('procurement/requests_list.html', requests=requests_list, Roles=Roles)

@procurement_bp.route('/request/add', methods=['GET', 'POST'])
@login_required
@role_required(Roles.SUPER_ADMIN, Roles.ADMIN, Roles.SITE_ENGINEER)
def add_request():
    db = get_db()
    user_id = to_object_id(session.get('user_id'))
    
    if session.get('role') == Roles.ADMIN:
        sites = list(db.sites.find())
    else:
        sites = list(db.sites.find({'$or': [{'engineer_id': user_id}, {'supervisor_id': user_id}]}))
        
    materials = list(db.materials.find())
    
    if request.method == 'POST':
        site_id = to_object_id(request.form.get('site_id'))
        req_date = request.form.get('required_date')
        
        # parse site
        site = db.sites.find_one({'_id': site_id})
        if not site:
            flash("Invalid site selected.", "danger")
            return redirect(url_for('procurement.add_request'))
            
        # Parse items
        mat_ids = request.form.getlist('material_id[]')
        mat_qtys = request.form.getlist('quantity[]')
        
        items = []
        for i in range(len(mat_ids)):
            mid = to_object_id(mat_ids[i])
            qty = float(mat_qtys[i] or 0)
            if mid and qty > 0:
                m = db.materials.find_one({'_id': mid})
                items.append({
                    'material_id': mid,
                    'name': m['name'] if m else 'Unknown',
                    'quantity': qty
                })
                
        if not items:
            flash("At least one material must be added.", "danger")
            return redirect(url_for('procurement.add_request'))
            
        req_no = generate_request_number()
        
        db.material_requests.insert_one({
            'request_number': req_no,
            'requested_by': user_id,
            'project_id': site['project_id'],
            'site_id': site_id,
            'items': items,
            'required_date': req_date,
            'status': IndentStatus.PENDING,
            'created_at': datetime.utcnow()
        })
        
        # notify PM
        proj = db.projects.find_one({'_id': site['project_id']})
        if proj and proj.get('manager_id'):
            db.notifications.insert_one({
                'user_id': proj['manager_id'],
                'title': "New Material Indent",
                'message': f"New material request {req_no} has been submitted.",
                'type': "material_request",
                'link': "/procurement/",
                'is_read': False,
                'created_at': datetime.utcnow()
            })
            
        flash(f"Material Request {req_no} submitted!", "success")
        return redirect(url_for('procurement.index'))
        
    return render_template('procurement/add_request.html', sites=sites, materials=materials)

@procurement_bp.route('/request/review/<request_id>', methods=['POST'])
@login_required
@role_required(Roles.SUPER_ADMIN, Roles.ADMIN, Roles.PROJECT_MANAGER)
def review_request(request_id):
    db = get_db()
    oid = to_object_id(request_id)
    action = request.form.get('action') # approve, reject
    
    if action not in ['approve', 'reject']:
        flash("Invalid action.", "danger")
        return redirect(url_for('procurement.index'))
        
    status = IndentStatus.APPROVED if action == 'approve' else IndentStatus.REJECTED
    db.material_requests.update_one({'_id': oid}, {'$set': {'status': status}})
    
    flash(f"Material request status set to {status}.", "success")
    return redirect(url_for('procurement.index'))


# ----------------- 2. RFQ MANAGEMENT -----------------
@procurement_bp.route('/rfq')
@login_required
def rfqs_list():
    db = get_db()
    rfqs = list(db.rfqs.find().sort('created_at', -1))
    for r in rfqs:
        req = db.material_requests.find_one({'_id': r.get('request_id')})
        r['request_number'] = req['request_number'] if req else 'N/A'
    return render_template('procurement/rfqs_list.html', rfqs=rfqs)

@procurement_bp.route('/rfq/create/<request_id>', methods=['GET', 'POST'])
@login_required
@role_required(Roles.SUPER_ADMIN, Roles.ADMIN)
def create_rfq(request_id):
    db = get_db()
    req_oid = to_object_id(request_id)
    req = db.material_requests.find_one({'_id': req_oid})
    if not req:
        flash("Material Request not found.", "danger")
        return redirect(url_for('procurement.index'))
        
    vendors = list(db.vendors.find())
    
    if request.method == 'POST':
        vendor_ids = [to_object_id(vid) for vid in request.form.getlist('vendor_ids') if vid]
        if not vendor_ids:
            flash("Please select at least one vendor.", "danger")
            return redirect(url_for('procurement.create_rfq', request_id=request_id))
            
        rfq_no = generate_rfq_number()
        db.rfqs.insert_one({
            'rfq_number': rfq_no,
            'request_id': req_oid,
            'vendor_ids': vendor_ids,
            'items': req['items'],
            'status': RFQStatus.OPEN,
            'created_at': datetime.utcnow()
        })
        
        db.material_requests.update_one({'_id': req_oid}, {'$set': {'status': IndentStatus.RFQ_CREATED}})
        
        # notify selected vendors
        for vid in vendor_ids:
            v_user = db.users.find_one({'email': db.vendors.find_one({'_id': vid}).get('email')})
            if v_user:
                db.notifications.insert_one({
                    'user_id': v_user['_id'],
                    'title': "New RFQ Request",
                    'message': f"You have been invited to quote for RFQ {rfq_no}.",
                    'type': "rfq_invited",
                    'link': f"/procurement/rfq/bid/{rfq_no}",
                    'is_read': False,
                    'created_at': datetime.utcnow()
                })
                
        flash(f"RFQ {rfq_no} created successfully!", "success")
        return redirect(url_for('procurement.rfqs_list'))
        
    return render_template('procurement/create_rfq.html', request=req, vendors=vendors)


# ----------------- 3. VENDOR QUOTATIONS -----------------
@procurement_bp.route('/rfq/bid/<rfq_no>', methods=['GET', 'POST'])
@login_required
@role_required(Roles.VENDOR, Roles.SUPER_ADMIN, Roles.ADMIN)
def submit_bid(rfq_no):
    db = get_db()
    rfq = db.rfqs.find_one({'rfq_number': rfq_no})
    if not rfq:
        flash("RFQ not found.", "danger")
        return redirect(url_for('dashboard.index'))
        
    vendor = db.vendors.find_one({'email': session['email']})
    
    if request.method == 'POST':
        if not vendor:
            flash("Only registered vendors can submit bids.", "danger")
            return redirect(url_for('dashboard.index'))
            
        mat_ids = request.form.getlist('material_id[]')
        rates = request.form.getlist('rate[]')
        
        items = []
        total_amount = 0.0
        for i in range(len(mat_ids)):
            mid = to_object_id(mat_ids[i])
            rate = float(rates[i] or 0)
            
            # Find item quantity from RFQ
            qty = 0
            for item in rfq['items']:
                if item['material_id'] == mid:
                    qty = item['quantity']
                    break
                    
            amt = qty * rate
            total_amount += amt
            items.append({
                'material_id': mid,
                'rate': rate,
                'quantity': qty,
                'amount': amt
            })
            
        db.vendor_quotations.update_one(
            {'rfq_id': rfq['_id'], 'vendor_id': vendor['_id']},
            {'$set': {
                'items': items,
                'total_amount': total_amount,
                'status': QuoteStatus.RECEIVED,
                'updated_at': datetime.utcnow()
            }},
            upsert=True
        )
        
        flash("Quotation submitted successfully!", "success")
        return redirect(url_for('dashboard.index'))
        
    # Get materials catalog for details
    materials_dict = {m['_id']: m for m in db.materials.find()}
    for item in rfq['items']:
        item['unit'] = materials_dict.get(item['material_id'], {}).get('unit', 'Nos')
        
    return render_template('procurement/submit_bid.html', rfq=rfq, vendor=vendor)


# ----------------- 4. QUOTATION COMPARISON & PO -----------------
@procurement_bp.route('/rfq/compare/<rfq_id>', methods=['GET', 'POST'])
@login_required
@role_required(Roles.SUPER_ADMIN, Roles.ADMIN)
def compare_quotes(rfq_id):
    db = get_db()
    rfq_oid = to_object_id(rfq_id)
    rfq = db.rfqs.find_one({'_id': rfq_oid})
    if not rfq:
        flash("RFQ not found.", "danger")
        return redirect(url_for('procurement.rfqs_list'))
        
    quotes = list(db.vendor_quotations.find({'rfq_id': rfq_oid}))
    for q in quotes:
        v = db.vendors.find_one({'_id': q['vendor_id']})
        q['vendor_name'] = v['company_name'] if v else 'N/A'
        
    req = db.material_requests.find_one({'_id': rfq['request_id']})
    
    if request.method == 'POST':
        selected_quote_id = to_object_id(request.form.get('selected_quote_id'))
        if not selected_quote_id:
            flash("Please select a quotation to approve.", "danger")
            return redirect(url_for('procurement.compare_quotes', rfq_id=rfq_id))
            
        selected_quote = db.vendor_quotations.find_one({'_id': selected_quote_id})
        
        # update status
        db.vendor_quotations.update_one({'_id': selected_quote_id}, {'$set': {'status': QuoteStatus.SELECTED}})
        db.vendor_quotations.update_many({'rfq_id': rfq_oid, '_id': {'$ne': selected_quote_id}}, {'$set': {'status': QuoteStatus.REJECTED}})
        db.rfqs.update_one({'_id': rfq_oid}, {'$set': {'status': RFQStatus.CLOSED}})
        
        # Generate PO
        po_no = generate_po_number()
        po_doc = {
            'po_number': po_no,
            'rfq_id': rfq_oid,
            'vendor_id': selected_quote['vendor_id'],
            'project_id': req['project_id'] if req else None,
            'site_id': req['site_id'] if req else None,
            'items': selected_quote['items'],
            'tax_amount': selected_quote['total_amount'] * 0.18, # 18% tax helper
            'total_amount': selected_quote['total_amount'] * 1.18,
            'delivery_date': req.get('required_date') if req else None,
            'status': POStatus.PENDING,
            'created_at': datetime.utcnow()
        }
        db.purchase_orders.insert_one(po_doc)
        db.material_requests.update_one({'_id': rfq['request_id']}, {'$set': {'status': IndentStatus.PO_CREATED}})
        
        flash(f"Quotation approved! PO {po_no} has been generated.", "success")
        return redirect(url_for('procurement.po_list'))
        
    return render_template('procurement/compare_quotes.html', rfq=rfq, quotes=quotes)


# ----------------- 5. PURCHASE ORDERS -----------------
@procurement_bp.route('/po')
@login_required
def po_list():
    db = get_db()
    pos = list(db.purchase_orders.find().sort('created_at', -1))
    for p in pos:
        v = db.vendors.find_one({'_id': p.get('vendor_id')})
        proj = db.projects.find_one({'_id': p.get('project_id')})
        p['vendor_name'] = v['company_name'] if v else 'N/A'
        p['project_name'] = proj['name'] if proj else 'N/A'
    return render_template('procurement/po_list.html', pos=pos, Roles=Roles)

@procurement_bp.route('/po/approve/<po_id>', methods=['POST'])
@login_required
@role_required(Roles.SUPER_ADMIN, Roles.ADMIN, Roles.PROJECT_MANAGER)
def approve_po(po_id):
    db = get_db()
    po_oid = to_object_id(po_id)
    db.purchase_orders.update_one({'_id': po_oid}, {'$set': {'status': POStatus.APPROVED}})
    
    # Notify Vendor
    po = db.purchase_orders.find_one({'_id': po_oid})
    if po:
        v = db.vendors.find_one({'_id': po['vendor_id']})
        v_user = db.users.find_one({'email': v['email']}) if v else None
        if v_user:
            db.notifications.insert_one({
                'user_id': v_user['_id'],
                'title': "Purchase Order Approved",
                'message': f"Purchase Order {po['po_number']} is approved and issued.",
                'type': "po_approved",
                'link': "/procurement/po",
                'is_read': False,
                'created_at': datetime.utcnow()
            })
            
    flash("Purchase Order approved successfully!", "success")
    return redirect(url_for('procurement.po_list'))


# ----------------- 6. GOODS RECEIPT NOTE (GRN) -----------------
@procurement_bp.route('/grn/create/<po_id>', methods=['GET', 'POST'])
@login_required
@role_required(Roles.SUPER_ADMIN, Roles.ADMIN, Roles.SITE_ENGINEER)
def create_grn(po_id):
    db = get_db()
    po_oid = to_object_id(po_id)
    po = db.purchase_orders.find_one({'_id': po_oid})
    if not po:
        flash("Purchase Order not found.", "danger")
        return redirect(url_for('procurement.po_list'))
        
    materials_dict = {m['_id']: m for m in db.materials.find()}
    for item in po['items']:
        item['name'] = materials_dict.get(item['material_id'], {}).get('name', 'Unknown')
        item['unit'] = materials_dict.get(item['material_id'], {}).get('unit', 'Nos')
        
    if request.method == 'POST':
        mat_ids = request.form.getlist('material_id[]')
        received_qtys = request.form.getlist('received_qty[]')
        damaged_qtys = request.form.getlist('damaged_qty[]')
        
        items = []
        for i in range(len(mat_ids)):
            mid = to_object_id(mat_ids[i])
            rec_qty = float(received_qtys[i] or 0)
            dmg_qty = float(damaged_qtys[i] or 0)
            acc_qty = rec_qty - dmg_qty
            
            if mid and rec_qty > 0:
                items.append({
                    'material_id': mid,
                    'received_qty': rec_qty,
                    'damaged_qty': dmg_qty,
                    'accepted_qty': acc_qty
                })
                
                # UPDATE STOCK IN MONGO
                update_stock(
                    mid, po['project_id'], po['site_id'], 'Main Warehouse', acc_qty,
                    'Stock In', 'GRN Delivery', po_oid, session.get('user_id')
                )
                
        grn_no = generate_grn_number()
        db.grn.insert_one({
            'grn_number': grn_no,
            'po_id': po_oid,
            'received_date': datetime.utcnow().strftime('%Y-%m-%d'),
            'items': items,
            'received_by': to_object_id(session.get('user_id')),
            'created_at': datetime.utcnow()
        })
        
        db.purchase_orders.update_one({'_id': po_oid}, {'$set': {'status': POStatus.DELIVERED}})
        
        # update material request status if links exist
        rfq = db.rfqs.find_one({'_id': po.get('rfq_id')})
        if rfq:
            db.material_requests.update_one({'_id': rfq['request_id']}, {'$set': {'status': IndentStatus.GRN_CREATED}})
            
        flash(f"GRN {grn_no} recorded and inventory updated!", "success")
        return redirect(url_for('procurement.po_list'))
        
    return render_template('procurement/create_grn.html', po=po)
