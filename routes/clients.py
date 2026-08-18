import secrets
from datetime import datetime
from flask import Blueprint, jsonify, request, session
from database.mongodb import get_db
from utils.decorators import login_required, role_required
from utils.constants import Roles
from services.auth_service import register_client
from utils.helpers import to_object_id

clients_bp = Blueprint('clients', __name__, url_prefix='/clients')

@clients_bp.route('/create-quick', methods=['POST'])
@login_required
@role_required(Roles.SUPER_ADMIN, Roles.ADMIN)
def create_quick():
    db = get_db()
    name = request.form.get('client_name', '').strip()
    company_name = request.form.get('company_name', '').strip()
    email = request.form.get('email', '').strip().lower()
    phone = request.form.get('phone', '').strip()
    address = request.form.get('address', '').strip()
    city = request.form.get('city', '').strip()
    state = request.form.get('state', '').strip()
    country = request.form.get('country', '').strip()
    gst_details = request.form.get('gst_details', '').strip()
    
    if not name:
        return jsonify({'success': False, 'message': 'Client Name is required'}), 400
    if not email:
        return jsonify({'success': False, 'message': 'Email is required'}), 400
        
    # Check if email is already registered
    existing_user = db.users.find_one({'email': email})
    if existing_user:
        return jsonify({'success': False, 'message': 'Email is already registered'}), 400
        
    # Generate a random secure password for the client user account
    password = secrets.token_urlsafe(12)
    company_id = session.get('company_id')
    
    # Register client user & profile
    user, err = register_client(
        name=name,
        email=email,
        password=password,
        company_name=company_name,
        phone=phone,
        address=address,
        gst_details=gst_details,
        company_id=company_id
    )
    
    if err:
        return jsonify({'success': False, 'message': err}), 400
        
    # Enrich the client profile with city, state, country
    db.clients.update_one({'user_id': user['_id']}, {'$set': {
        'city': city,
        'state': state,
        'country': country
    }})
    
    # Retrieve the inserted client profile to obtain its ObjectId
    client_doc = db.clients.find_one({'user_id': user['_id']})
    if not client_doc:
        return jsonify({'success': False, 'message': 'Failed to retrieve created client profile'}), 500
        
    return jsonify({
        'success': True,
        'message': 'Client created successfully',
        'client': {
            'id': str(client_doc['_id']),
            'name': name
        }
    })

@clients_bp.route('/list', methods=['GET'])
@login_required
@role_required(Roles.SUPER_ADMIN, Roles.ADMIN)
def list_clients():
    db = get_db()
    clients = list(db.clients.find())
    clients_list = []
    for c in clients:
        clients_list.append({
            'id': str(c['_id']),
            'client_name': c.get('client_name', ''),
            'company_name': c.get('company_name', '')
        })
    return jsonify({
        'success': True,
        'clients': clients_list
    })
