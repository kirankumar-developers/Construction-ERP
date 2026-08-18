from functools import wraps
from flask import session, request, redirect, url_for, flash, abort, jsonify

def login_required(f):
    """
    Decorator to ensure the user is logged in before accessing a route.
    Redirects to the login page if not logged in.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def role_required(*roles):
    """
    Decorator to restrict access to specific roles.
    Assumes login_required is run beforehand or incorporates login checking.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('auth.login', next=request.url))
            
            user_role = session.get('role')
            if user_role not in roles:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.path.startswith('/api/'):
                    return jsonify({'error': 'Forbidden: Insufficient permissions'}), 403
                abort(403) # Raises 403 Forbidden which will render our custom 403 template
            return f(*args, **kwargs)
        return decorated_function
    return decorator
