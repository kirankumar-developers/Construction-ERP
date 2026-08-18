from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from database.mongodb import get_db
from utils.decorators import login_required
from utils.constants import Roles, DocumentCategory
from utils.helpers import to_object_id
from services.upload_service import upload_file
from bson import ObjectId
from datetime import datetime

documents_bp = Blueprint('documents', __name__, url_prefix='/documents')

@documents_bp.route('/')
@login_required
def index():
    db = get_db()
    
    # Filter inputs
    project_id = to_object_id(request.args.get('project_id'))
    site_id = to_object_id(request.args.get('site_id'))
    category = request.args.get('category')
    
    query = {}
    if project_id:
        query['project_id'] = project_id
    if site_id:
        query['site_id'] = site_id
    if category:
        query['category'] = category
        
    docs = list(db.documents.find(query).sort('upload_date', -1))
    
    for d in docs:
        p = db.projects.find_one({'_id': d.get('project_id')})
        s = db.sites.find_one({'_id': d.get('site_id')})
        u = db.users.find_one({'_id': d.get('uploaded_by')})
        d['project_name'] = p['name'] if p else 'N/A'
        d['site_name'] = s['name'] if s else 'N/A'
        d['uploader_name'] = u['name'] if u else 'Unknown'
        
    projects = list(db.projects.find())
    sites = list(db.sites.find())
    
    return render_template('documents/list.html',
                           documents=docs,
                           projects=projects,
                           sites=sites,
                           DocumentCategory=DocumentCategory,
                           selected_project=project_id,
                           selected_site=site_id,
                           selected_category=category)

@documents_bp.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    db = get_db()
    projects = list(db.projects.find())
    sites = list(db.sites.find())
    
    if request.method == 'POST':
        project_id = to_object_id(request.form.get('project_id'))
        site_id = to_object_id(request.form.get('site_id'))
        category = request.form.get('category', DocumentCategory.OTHER)
        file = request.files.get('document')
        
        if not file or not file.filename:
            flash("Please select a file to upload.", "danger")
            return redirect(url_for('documents.upload'))
            
        file_path, err = upload_file(file)
        if err:
            flash(err, "danger")
            return redirect(url_for('documents.upload'))
            
        db.documents.insert_one({
            'name': file.filename,
            'original_name': file.filename,
            'file_path': file_path,
            'file_type': file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else 'unknown',
            'category': category,
            'uploaded_by': to_object_id(session.get('user_id')),
            'upload_date': datetime.utcnow(),
            'project_id': project_id,
            'site_id': site_id
        })
        
        flash("Document uploaded successfully!", "success")
        return redirect(url_for('documents.index'))
        
    return render_template('documents/upload.html', projects=projects, sites=sites, DocumentCategory=DocumentCategory)
