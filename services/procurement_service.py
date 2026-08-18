import logging
from database.mongodb import get_db
from utils.helpers import to_object_id

logger = logging.getLogger(__name__)

def get_pending_pos():
    db = get_db()
    return list(db.purchase_orders.find({'status': 'pending'}))

def get_rfq_details(rfq_id):
    db = get_db()
    oid = to_object_id(rfq_id)
    rfq = db.rfqs.find_one({'_id': oid})
    if rfq:
        req = db.material_requests.find_one({'_id': rfq.get('request_id')})
        rfq['request_number'] = req['request_number'] if req else 'N/A'
    return rfq
