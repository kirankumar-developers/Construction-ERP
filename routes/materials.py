from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from database.mongodb import get_db
from utils.decorators import login_required, role_required
from utils.constants import Roles
from utils.helpers import to_object_id
from services.inventory_service import update_stock
from datetime import datetime

materials_bp = Blueprint('materials', __name__, url_prefix='/materials')

@materials_bp.route('/')
@login_required
def index():
    db = get_db()
    materials = list(db.materials.find())
    
    # Calculate stock levels per material
    for m in materials:
        cats = db.material_categories.find_one({'_id': m.get('category_id')})
        m['category_name'] = cats['name'] if cats else 'General'
        
        # Aggregate stocks
        stocks = list(db.inventory.find({'material_id': m['_id']}))
        m['total_stock'] = sum([s.get('quantity', 0.0) for s in stocks])
        m['low_stock'] = m['total_stock'] < m.get('min_stock_level', 0.0)
        
    return render_template('inventory/list.html', materials=materials)

@materials_bp.route('/add', methods=['GET', 'POST'])
@login_required
@role_required(Roles.SUPER_ADMIN, Roles.ADMIN, Roles.PROJECT_MANAGER)
def add():
    db = get_db()
    categories = list(db.material_categories.find())
    
    if request.method == 'POST':
        code = request.form.get('material_code', '').strip().upper()
        name = request.form.get('name', '').strip()
        cat_id = to_object_id(request.form.get('category_id'))
        unit = request.form.get('unit', 'Nos').strip()
        min_stock = float(request.form.get('min_stock_level', 0.0) or 0)
        rate = float(request.form.get('purchase_rate', 0.0) or 0)
        
        if not code or not name or not cat_id:
            flash("Material Code, Name, and Category are required.", "danger")
            return redirect(url_for('materials.add'))
            
        # check duplicate code
        existing = db.materials.find_one({'material_code': code})
        if existing:
            flash("Material Code already exists.", "danger")
            return redirect(url_for('materials.add'))
            
        db.materials.insert_one({
            'material_code': code,
            'name': name,
            'category_id': cat_id,
            'unit': unit,
            'min_stock_level': min_stock,
            'purchase_rate': rate,
            'created_at': datetime.utcnow()
        })
        
        flash("Material registered successfully!", "success")
        return redirect(url_for('materials.index'))
        
    return render_template('inventory/add_material.html', categories=categories)

@materials_bp.route('/categories', methods=['GET', 'POST'])
@login_required
@role_required(Roles.SUPER_ADMIN, Roles.ADMIN)
def categories():
    db = get_db()
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        if name:
            db.material_categories.update_one({'name': name}, {'$set': {'name': name}}, upsert=True)
            flash("Category added successfully!", "success")
        return redirect(url_for('materials.categories'))
        
    cats = list(db.material_categories.find())
    return render_template('inventory/categories.html', categories=cats)

@materials_bp.route('/stock-in', methods=['GET', 'POST'])
@login_required
@role_required(Roles.SUPER_ADMIN, Roles.ADMIN, Roles.PROJECT_MANAGER, Roles.SITE_ENGINEER)
def stock_in():
    db = get_db()
    materials = list(db.materials.find())
    projects = list(db.projects.find())
    sites = list(db.sites.find())
    
    if request.method == 'POST':
        material_id = request.form.get('material_id')
        project_id = request.form.get('project_id')
        site_id = request.form.get('site_id')
        warehouse = request.form.get('warehouse_name', 'Main Warehouse').strip()
        qty = float(request.form.get('quantity', 0.0) or 0)
        
        if not material_id or not project_id or not site_id or qty <= 0:
            flash("All fields are required and quantity must be positive.", "danger")
            return redirect(url_for('materials.stock_in'))
            
        update_stock(
            material_id, project_id, site_id, warehouse, qty,
            'Stock In', 'Manual Stock In', None, session.get('user_id')
        )
        
        flash("Stock added successfully!", "success")
        return redirect(url_for('materials.index'))
        
    return render_template('inventory/stock_in.html', materials=materials, projects=projects, sites=sites)

@materials_bp.route('/stock-transfer', methods=['GET', 'POST'])
@login_required
@role_required(Roles.SUPER_ADMIN, Roles.ADMIN, Roles.PROJECT_MANAGER, Roles.SITE_ENGINEER)
def stock_transfer():
    db = get_db()
    materials = list(db.materials.find())
    projects = list(db.projects.find())
    sites = list(db.sites.find())
    
    if request.method == 'POST':
        material_id = request.form.get('material_id')
        from_proj = request.form.get('from_project_id')
        from_site = request.form.get('from_site_id')
        to_proj = request.form.get('to_project_id')
        to_site = request.form.get('to_site_id')
        qty = float(request.form.get('quantity', 0.0) or 0)
        
        if not material_id or not from_site or not to_site or qty <= 0:
            flash("All fields are required and quantity must be positive.", "danger")
            return redirect(url_for('materials.stock_transfer'))
            
        # Deduct from source site
        update_stock(
            material_id, from_proj, from_site, 'Main Warehouse', -qty,
            'Stock Out', 'Material Transfer', None, session.get('user_id')
        )
        
        # Add to destination site
        update_stock(
            material_id, to_proj, to_site, 'Main Warehouse', qty,
            'Stock In', 'Material Transfer', None, session.get('user_id')
        )
        
        flash("Stock transferred successfully!", "success")
        return redirect(url_for('materials.index'))
        
    return render_template('inventory/stock_transfer.html', materials=materials, projects=projects, sites=sites)

@materials_bp.route('/transactions')
@login_required
def transactions():
    db = get_db()
    txs = list(db.inventory_transactions.find().sort('created_at', -1).limit(100))
    for t in txs:
        m = db.materials.find_one({'_id': t.get('material_id')})
        p = db.projects.find_one({'_id': t.get('project_id')})
        s = db.sites.find_one({'_id': t.get('site_id')})
        u = db.users.find_one({'_id': t.get('created_by')})
        t['material_name'] = m['name'] if m else 'N/A'
        t['project_name'] = p['name'] if p else 'N/A'
        t['site_name'] = s['name'] if s else 'N/A'
        t['user_name'] = u['name'] if u else 'N/A'
        
    return render_template('inventory/transactions.html', transactions=txs)
