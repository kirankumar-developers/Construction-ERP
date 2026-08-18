from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from database.mongodb import get_db
from utils.decorators import login_required
from utils.helpers import to_object_id
from datetime import datetime

attendance_bp = Blueprint('attendance', __name__, url_prefix='/attendance')

@attendance_bp.route('/')
@login_required
def index():
    db = get_db()
    user_id = to_object_id(session.get('user_id'))
    
    # fetch history
    history = list(db.attendance.find({
        'employee_type': 'Employee',
        'ref_id': user_id
    }).sort('date', -1))
    
    # Check if checked in today
    today_str = datetime.utcnow().strftime('%Y-%m-%d')
    today_record = db.attendance.find_one({
        'employee_type': 'Employee',
        'ref_id': user_id,
        'date': today_str
    })
    
    return render_template('attendance/check_in.html', history=history, today_record=today_record)

@attendance_bp.route('/check-in', methods=['POST'])
@login_required
def check_in():
    db = get_db()
    user_id = to_object_id(session.get('user_id'))
    lat = float(request.form.get('lat', 0.0) or 0)
    lng = float(request.form.get('lng', 0.0) or 0)
    today_str = datetime.utcnow().strftime('%Y-%m-%d')
    
    # verify if checked in already
    existing = db.attendance.find_one({
        'employee_type': 'Employee',
        'ref_id': user_id,
        'date': today_str
    })
    
    if existing:
        flash("You are already checked in for today.", "warning")
        return redirect(url_for('attendance.index'))
        
    db.attendance.insert_one({
        'employee_type': 'Employee',
        'ref_id': user_id,
        'date': today_str,
        'check_in_time': datetime.utcnow(),
        'check_in_location': {
            'lat': lat,
            'lng': lng
        },
        'status': 'Present',
        'created_at': datetime.utcnow()
    })
    
    flash("Checked in successfully!", "success")
    return redirect(url_for('attendance.index'))

@attendance_bp.route('/check-out', methods=['POST'])
@login_required
def check_out():
    db = get_db()
    user_id = to_object_id(session.get('user_id'))
    lat = float(request.form.get('lat', 0.0) or 0)
    lng = float(request.form.get('lng', 0.0) or 0)
    today_str = datetime.utcnow().strftime('%Y-%m-%d')
    
    record = db.attendance.find_one({
        'employee_type': 'Employee',
        'ref_id': user_id,
        'date': today_str
    })
    
    if not record:
        flash("No check-in record found for today.", "danger")
        return redirect(url_for('attendance.index'))
        
    check_out_time = datetime.utcnow()
    check_in_time = record.get('check_in_time')
    
    # Calculate working hours
    working_hours = 0.0
    if check_in_time:
        duration = check_out_time - check_in_time
        working_hours = duration.total_seconds() / 3600.0
        
    db.attendance.update_one(
        {'_id': record['_id']},
        {'$set': {
            'check_out_time': check_out_time,
            'check_out_location': {
                'lat': lat,
                'lng': lng
            },
            'working_hours': working_hours
        }}
    )
    
    flash(f"Checked out successfully! Total working hours: {working_hours:.2f} hours.", "success")
    return redirect(url_for('attendance.index'))
