import logging
from datetime import datetime
from database.mongodb import get_db
from utils.helpers import to_object_id

logger = logging.getLogger(__name__)

def get_employee_attendance(user_id):
    db = get_db()
    return list(db.attendance.find({
        'employee_type': 'Employee',
        'ref_id': to_object_id(user_id)
    }).sort('date', -1))

def get_labour_attendance(labour_id):
    db = get_db()
    return list(db.attendance.find({
        'employee_type': 'Labour',
        'ref_id': to_object_id(labour_id)
    }).sort('date', -1))
