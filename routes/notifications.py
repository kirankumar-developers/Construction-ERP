from flask import Blueprint, render_template, redirect, url_for, flash, session, request
from database.mongodb import get_db
from utils.decorators import login_required
from utils.helpers import to_object_id
from services.notification_service import get_user_notifications, mark_all_notifications_as_read, mark_notification_as_read

notifications_bp = Blueprint('notifications_bp', __name__, url_prefix='/notifications_feed')

@notifications_bp.route('/')
@login_required
def index():
    user_id = session.get('user_id')
    notifs = get_user_notifications(user_id, limit=100)
    mark_all_notifications_as_read(user_id)
    return render_template('notifications.html', notifications=notifs)

@notifications_bp.route('/read/<notif_id>', methods=['POST'])
@login_required
def read_single(notif_id):
    mark_notification_as_read(notif_id)
    return {"status": "success"}
