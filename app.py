import os
import logging
from flask import Flask, render_template, session, redirect, url_for, flash
from config import Config
from database.mongodb import init_db
from database.indexes import create_indexes
from routes import register_blueprints
from utils import init_utils

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config.from_object(Config)

# Register Jinja helpers / Filters
init_utils(app)

# Initialize Database and Indexes
with app.app_context():
    try:
        init_db(app)
        create_indexes()
    except Exception as e:
        logger.error(f"Failed to initialize database during startup: {e}")

# Register Blueprints
register_blueprints(app)

# Inject current user notifications count globally in Jinja templates
@app.context_processor
def inject_notifications():
    if 'user_id' in session:
        try:
            from services.notification_service import get_unread_count, get_user_notifications
            return {
                'unread_count': get_unread_count(session['user_id']),
                'navbar_notifications': get_user_notifications(session['user_id'], limit=5)
            }
        except Exception:
            pass
    return {'unread_count': 0, 'navbar_notifications': []}

# Navigation redirection index route
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard.index'))
    return redirect(url_for('auth.login'))

# System Notifications Route (For viewing all in-app notifications)
@app.route('/notifications')
def notifications():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    from services.notification_service import get_user_notifications, mark_all_notifications_as_read
    notifs = get_user_notifications(session['user_id'], limit=100)
    mark_all_notifications_as_read(session['user_id'])
    return render_template('notifications.html', notifications=notifs)

# Custom Error Handling
@app.errorhandler(403)
def forbidden(e):
    return render_template('errors/403.html'), 403

@app.errorhandler(404)
def not_found(e):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('errors/500.html'), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
