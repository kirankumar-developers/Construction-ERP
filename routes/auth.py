from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from services.auth_service import login_user
from utils.constants import Roles

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        
        if not email or not password:
            flash("All fields are required.", "danger")
            return render_template('auth/login.html')
            
        user, err = login_user(email, password)
        if err:
            flash(err, "danger")
            return render_template('auth/login.html')
            
        # Set session details
        session['user_id'] = str(user['_id'])
        session['name'] = user['name']
        session['email'] = user['email']
        session['role'] = user['role']
        if user.get('company_id'):
            session['company_id'] = str(user['company_id'])
        
        flash(f"Welcome back, {user['name']}!", "success")
        
        next_url = request.args.get('next')
        if next_url:
            return redirect(next_url)
            
        return redirect(url_for('dashboard.index'))
            
    return render_template('auth/login.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash("You have successfully logged out.", "info")
    return redirect(url_for('auth.login'))
