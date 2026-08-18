import logging
from datetime import datetime
from database.mongodb import get_db
from utils.helpers import to_object_id

logger = logging.getLogger(__name__)

def update_stock(material_id, project_id, site_id, warehouse_name, qty, transaction_type, reference_type=None, reference_id=None, user_id=None):
    db = get_db()
    mid = to_object_id(material_id)
    pid = to_object_id(project_id)
    sid = to_object_id(site_id)
    
    # 1. Update Inventory Ledger
    db.inventory.update_one(
        {
            'material_id': mid,
            'project_id': pid,
            'site_id': sid,
            'warehouse_name': warehouse_name or 'Main Warehouse'
        },
        {'$inc': {'quantity': qty}},
        upsert=True
    )
    
    # 2. Insert Transaction Log
    db.inventory_transactions.insert_one({
        'material_id': mid,
        'project_id': pid,
        'site_id': sid,
        'warehouse_name': warehouse_name or 'Main Warehouse',
        'type': transaction_type, # 'Stock In', 'Stock Out', 'Transfer', 'Return', 'Consumption'
        'quantity': abs(qty),
        'reference_type': reference_type,
        'reference_id': to_object_id(reference_id),
        'created_by': to_object_id(user_id),
        'created_at': datetime.utcnow()
    })
    
    # 3. Check for low stock
    check_low_stock(mid, pid, sid)

def check_low_stock(material_id, project_id, site_id):
    db = get_db()
    m = db.materials.find_one({'_id': material_id})
    if not m:
        return
        
    min_level = m.get('min_stock_level', 0)
    
    # Calculate total quantity across this project/site
    items = list(db.inventory.find({'material_id': material_id, 'site_id': site_id}))
    total_qty = sum([item.get('quantity', 0) for item in items])
    
    if total_qty < min_level:
        # Create notification for PM and Site Engineer
        site = db.sites.find_one({'_id': site_id})
        msg = f"Low stock alert for {m['name']} at site {site['name'] if site else 'General'}. Current: {total_qty}, Min: {min_level}."
        
        # notify Site Engineer
        if site and site.get('engineer_id'):
            create_notification(site['engineer_id'], "Low Stock Alert", msg, "low_stock", "/materials/")
            
        # notify Project Manager
        proj = db.projects.find_one({'_id': project_id})
        if proj and proj.get('manager_id'):
            create_notification(proj['manager_id'], "Low Stock Alert", msg, "low_stock", "/materials/")

def create_notification(user_id, title, message, notif_type, link=None):
    db = get_db()
    db.notifications.insert_one({
        'user_id': to_object_id(user_id),
        'title': title,
        'message': message,
        'type': notif_type,
        'link': link,
        'is_read': False,
        'created_at': datetime.utcnow()
    })
