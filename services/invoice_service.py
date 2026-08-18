import logging
from datetime import datetime
from database.mongodb import get_db
from utils.helpers import to_object_id, generate_invoice_number

logger = logging.getLogger(__name__)

def create_client_invoice(project_id, client_id, items, tax_rate=18.0):
    db = get_db()
    pid = to_object_id(project_id)
    cid = to_object_id(client_id)
    
    subtotal = 0.0
    for item in items:
        qty = float(item.get('quantity', 0))
        rate = float(item.get('rate', 0))
        tot = qty * rate
        item['total'] = tot
        subtotal += tot
        
    tax_amt = subtotal * (tax_rate / 100.0)
    total_amt = subtotal + tax_amt
    
    inv_no = generate_invoice_number()
    invoice_doc = {
        'invoice_number': inv_no,
        'project_id': pid,
        'client_id': cid,
        'items': items,
        'tax_rate': tax_rate,
        'tax_amount': tax_amt,
        'total_amount': total_amt,
        'status': 'draft',
        'created_at': datetime.utcnow()
    }
    
    res = db.invoices.insert_one(invoice_doc)
    invoice_doc['_id'] = res.inserted_id
    
    # notify Client
    c = db.clients.find_one({'_id': cid})
    if c and c.get('user_id'):
        db.notifications.insert_one({
            'user_id': c['user_id'],
            'title': "New Invoice Raised",
            'message': f"A new invoice {inv_no} has been raised for your project.",
            'type': "invoice_created",
            'link': "/invoices/",
            'is_read': False,
            'created_at': datetime.utcnow()
        })
        
    return invoice_doc
