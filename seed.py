import logging
from datetime import datetime, timedelta
from database.mongodb import init_db
from utils.helpers import hash_password
from utils.constants import Roles, ProjectStatus, ProjectPriority, SiteStatus, TaskStatus, TaskPriority, IndentStatus, RFQStatus, QuoteStatus, POStatus, EquipmentStatus, ExpenseStatus, InvoiceStatus, PaymentStatus, InspectionResult, IssueStatus

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def seed_db():
    db = init_db()
    
    # 1. Clear existing collections
    logger.info("Clearing existing collections...")
    collections_to_clear = [
        'users', 'companies', 'projects', 'sites', 'tasks', 'task_comments', 'milestones',
        'boq', 'budgets', 'dpr', 'materials', 'material_categories', 'inventory',
        'inventory_transactions', 'material_requests', 'rfqs', 'vendor_quotations',
        'purchase_orders', 'grn', 'vendors', 'employees', 'labours', 'attendance',
        'subcontractors', 'work_orders', 'equipment', 'equipment_usage', 'equipment_maintenance',
        'expenses', 'invoices', 'payments', 'inspections', 'quality_checks', 'issues',
        'documents', 'notifications', 'activity_logs', 'clients'
    ]
    for col in collections_to_clear:
        db[col].delete_many({})
        
    # 2. Insert Company details
    company_doc = {
        'name': 'Titan Construction Corp',
        'logo': '/static/images/logo.png',
        'email': 'contact@titanconstruction.com',
        'phone': '1-800-555-0199',
        'address': '500 Fifth Avenue, New York, NY 10110',
        'created_at': datetime.utcnow()
    }
    comp_res = db.companies.insert_one(company_doc)
    comp_id = comp_res.inserted_id
    
    # 3. Insert Users & Profiles
    logger.info("Inserting role users and profiles...")
    pw_hash = hash_password('admin123')
    
    # Define User Roles
    users_data = [
        {'name': 'Super Administrator', 'email': 'superadmin@onsiteerp.com', 'role': Roles.SUPER_ADMIN},
        {'name': 'Admin User', 'email': 'admin@onsiteerp.com', 'role': Roles.ADMIN},
        {'name': 'Marcus PM', 'email': 'pm@onsiteerp.com', 'role': Roles.PROJECT_MANAGER},
        {'name': 'Dave Engineer', 'email': 'engineer@onsiteerp.com', 'role': Roles.SITE_ENGINEER},
        {'name': 'Steve Supervisor', 'email': 'supervisor@onsiteerp.com', 'role': Roles.SUPERVISOR},
        {'name': 'John Employee', 'email': 'employee@onsiteerp.com', 'role': Roles.EMPLOYEE},
        {'name': 'Apex Vendor', 'email': 'vendor@onsiteerp.com', 'role': Roles.VENDOR},
        {'name': 'Omega Subcontractor', 'email': 'subcon@onsiteerp.com', 'role': Roles.SUBCONTRACTOR},
        {'name': 'Empire Properties Client', 'email': 'client@onsiteerp.com', 'role': Roles.CLIENT},
        {'name': 'Al Labourer', 'email': 'labour@onsiteerp.com', 'role': Roles.LABOUR}
    ]
    
    user_ids = {}
    for ud in users_data:
        user_doc = {
            'name': ud['name'],
            'email': ud['email'],
            'password_hash': pw_hash,
            'role': ud['role'],
            'company_id': comp_id,
            'is_active': True,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        res = db.users.insert_one(user_doc)
        user_ids[ud['role']] = res.inserted_id
        
    # Profile mappings
    # Employee profiles
    employee_roles = [Roles.SUPER_ADMIN, Roles.ADMIN, Roles.PROJECT_MANAGER, Roles.SITE_ENGINEER, Roles.SUPERVISOR, Roles.EMPLOYEE]
    for idx, r in enumerate(employee_roles):
        db.employees.insert_one({
            'user_id': user_ids[r],
            'employee_id': f"EMP-2026-{1001 + idx}",
            'department': 'Operations',
            'designation': r.replace('_', ' ').title(),
            'phone': f"555-010{idx}",
            'address': 'New York Head Office',
            'current_status': 'active',
            'created_at': datetime.utcnow()
        })
        
    # Client profile
    client_res = db.clients.insert_one({
        'user_id': user_ids[Roles.CLIENT],
        'client_name': 'Empire Properties Client',
        'company_name': 'Empire Properties LLC',
        'email': 'client@onsiteerp.com',
        'phone': '555-0155',
        'address': 'Empire State Bldg, NYC',
        'gst_details': 'GST-US-99881',
        'created_at': datetime.utcnow()
    })
    client_id = client_res.inserted_id
    
    # Vendor Profile
    vendor_res = db.vendors.insert_one({
        'user_id': user_ids[Roles.VENDOR],
        'company_name': 'Apex Materials Inc',
        'contact_person': 'Apex Vendor',
        'email': 'vendor@onsiteerp.com',
        'phone': '555-0166',
        'address': 'Brooklyn Materials Yard, NY',
        'gst_details': 'GST-NY-55443',
        'categories': ['Concrete', 'Steel'],
        'outstanding_amount': 25000.0,
        'created_at': datetime.utcnow()
    })
    vendor_id = vendor_res.inserted_id
    
    # Subcontractor Profile
    subcon_res = db.subcontractors.insert_one({
        'user_id': user_ids[Roles.SUBCONTRACTOR],
        'company_name': 'Omega Electricals',
        'contact_person': 'Omega Subcontractor',
        'email': 'subcon@onsiteerp.com',
        'phone': '555-0177',
        'address': 'Queens Office Yard, NY',
        'work_category': 'Electrical Wiring & Power Installation',
        'contract_value': 120000.0,
        'created_at': datetime.utcnow()
    })
    subcon_id = subcon_res.inserted_id
    
    # Labour Profile
    db.labours.insert_one({
        'user_id': user_ids[Roles.LABOUR],
        'labour_id': 'LAB-2026-0001',
        'name': 'Al Labourer',
        'category': 'Mason',
        'daily_wage': 120.0,
        'status': 'active',
        'created_at': datetime.utcnow()
    })
    
    # 4. Insert Project
    logger.info("Inserting project details...")
    proj_doc = {
        'project_code': 'PRJ-2026-0001',
        'name': 'Empire Commercial Office Tower',
        'client_id': client_id,
        'manager_id': user_ids[Roles.PROJECT_MANAGER],
        'location': {
            'address': '350 Fifth Ave, New York, NY 10118',
            'lat': 40.7484,
            'lng': -73.9857
        },
        'start_date': '2026-01-01',
        'end_date': '2026-12-31',
        'budget': 500000.0,
        'status': ProjectStatus.ACTIVE,
        'priority': ProjectPriority.HIGH,
        'description': 'Constructing a multi-story commercial corporate building.',
        'progress': 35,
        'created_at': datetime.utcnow(),
        'updated_at': datetime.utcnow()
    }
    proj_res = db.projects.insert_one(proj_doc)
    proj_id = proj_res.inserted_id
    
    # 5. Insert Site
    logger.info("Inserting construction sites...")
    site_doc = {
        'site_code': 'STE-0001',
        'name': 'Block A Sub-Structure Foundation',
        'project_id': proj_id,
        'address': 'Tower A Site Yard, NYC',
        'lat': 40.7486,
        'lng': -73.9855,
        'engineer_id': user_ids[Roles.SITE_ENGINEER],
        'supervisor_id': user_ids[Roles.SUPERVISOR],
        'status': SiteStatus.ACTIVE,
        'created_at': datetime.utcnow()
    }
    site_res = db.sites.insert_one(site_doc)
    site_id = site_res.inserted_id
    
    # 6. Insert Milestones
    db.milestones.insert_one({
        'project_id': proj_id,
        'title': 'Excavation & Piling Foundations Completed',
        'due_date': '2026-04-15',
        'status': 'completed',
        'created_at': datetime.utcnow()
    })
    db.milestones.insert_one({
        'project_id': proj_id,
        'title': 'Superstructure Block Frame Shell Ready',
        'due_date': '2026-08-30',
        'status': 'pending',
        'created_at': datetime.utcnow()
    })
    
    # 7. Insert Tasks
    logger.info("Inserting task assignments...")
    t1_doc = {
        'project_id': proj_id,
        'site_id': site_id,
        'title': 'Reinforcement Steel Layout Block A',
        'description': 'Assemble high tensile rebars structure details for foundation slab casting.',
        'assigned_employee_ids': [user_ids[Roles.SITE_ENGINEER], user_ids[Roles.SUPERVISOR], user_ids[Roles.EMPLOYEE]],
        'start_date': '2026-08-10',
        'due_date': '2026-08-25',
        'priority': TaskPriority.HIGH,
        'status': TaskStatus.IN_PROGRESS,
        'progress': 65,
        'parent_task_id': None,
        'created_at': datetime.utcnow(),
        'updated_at': datetime.utcnow()
    }
    t1_res = db.tasks.insert_one(t1_doc)
    
    # Subtask
    db.tasks.insert_one({
        'project_id': proj_id,
        'site_id': site_id,
        'title': 'Rebars Binding & Spacers placement',
        'description': 'Place concrete cover block spacers underneath rebar mesh.',
        'assigned_employee_ids': [user_ids[Roles.EMPLOYEE]],
        'start_date': '2026-08-15',
        'due_date': '2026-08-20',
        'priority': TaskPriority.MEDIUM,
        'status': TaskStatus.IN_PROGRESS,
        'progress': 80,
        'parent_task_id': t1_res.inserted_id,
        'created_at': datetime.utcnow(),
        'updated_at': datetime.utcnow()
    })
    
    # 8. Insert Materials catalog & stock
    logger.info("Inserting material master categories & stock items...")
    cat1_res = db.material_categories.insert_one({'name': 'Construction Core Material'})
    cat2_res = db.material_categories.insert_one({'name': 'Structural Steel & Metal'})
    
    mat1_doc = {
        'material_code': 'MAT-CMT-OPC53',
        'name': 'Portland Cement OPC Grade 53',
        'category_id': cat1_res.inserted_id,
        'unit': 'Bags',
        'min_stock_level': 100.0,
        'purchase_rate': 6.5,
        'created_at': datetime.utcnow()
    }
    mat1_res = db.materials.insert_one(mat1_doc)
    
    mat2_doc = {
        'material_code': 'MAT-STL-REBAR16',
        'name': 'High Tensile Steel Rebars 16mm',
        'category_id': cat2_res.inserted_id,
        'unit': 'Tons',
        'min_stock_level': 5.0,
        'purchase_rate': 720.0,
        'created_at': datetime.utcnow()
    }
    mat2_res = db.materials.insert_one(mat2_doc)
    
    # Stock level inputs
    db.inventory.insert_one({
        'material_id': mat1_res.inserted_id,
        'project_id': proj_id,
        'site_id': site_id,
        'warehouse_name': 'Main Site Yard',
        'quantity': 350.0,
        'created_at': datetime.utcnow()
    })
    db.inventory.insert_one({
        'material_id': mat2_res.inserted_id,
        'project_id': proj_id,
        'site_id': site_id,
        'warehouse_name': 'Main Site Yard',
        'quantity': 12.0,
        'created_at': datetime.utcnow()
    })
    
    # 9. Budgets & BOQs
    logger.info("Inserting BOQ estimates & budget controls...")
    db.budgets.insert_one({
        'project_id': proj_id,
        'category': 'Material',
        'amount': 200000.0,
        'created_at': datetime.utcnow()
    })
    db.budgets.insert_one({
        'project_id': proj_id,
        'category': 'Labour',
        'amount': 150000.0,
        'created_at': datetime.utcnow()
    })
    db.budgets.insert_one({
        'project_id': proj_id,
        'category': 'Equipment',
        'amount': 80000.0,
        'created_at': datetime.utcnow()
    })
    
    db.boq.insert_one({
        'boq_number': 'BOQ-2026-0001',
        'project_id': proj_id,
        'category': 'Civil Foundations',
        'items': [
            {'item_id': '1', 'description': 'Excavation in sand soils', 'unit': 'Cum', 'quantity': 1500.0, 'rate': 4.5, 'amount': 6750.0},
            {'item_id': '2', 'description': 'Cement concrete structural mesh pour', 'unit': 'Cum', 'quantity': 450.0, 'rate': 120.0, 'amount': 54000.0}
        ],
        'total_amount': 60750.0,
        'created_at': datetime.utcnow()
    })
    
    # 10. Expenses & Payments
    db.expenses.insert_one({
        'expense_date': '2026-08-15',
        'amount': 1500.0,
        'project_id': proj_id,
        'site_id': site_id,
        'category': 'Transport',
        'description': 'Aggregate materials sand truck haulage charges.',
        'status': ExpenseStatus.APPROVED,
        'created_by': user_ids[Roles.SITE_ENGINEER],
        'created_at': datetime.utcnow()
    })
    
    # 11. Equipment
    db.equipment.insert_one({
        'equipment_id': 'EQP-CAT-320',
        'name': 'Caterpillar Excavator 320D',
        'category': 'Heavy Excavator',
        'type': 'Rental',
        'daily_cost': 450.0,
        'status': EquipmentStatus.AVAILABLE,
        'project_id': proj_id,
        'site_id': site_id,
        'created_at': datetime.utcnow()
    })
    
    # 12. Snags & Issues
    db.issues.insert_one({
        'issue_number': 'ISS-2026-0001',
        'project_id': proj_id,
        'site_id': site_id,
        'title': 'Columns Reinforcement spacing variance',
        'description': 'Columns spacing at block A foundation slab deviates from detail designs blueprints. Re-adjustment required.',
        'reported_by': user_ids[Roles.SITE_ENGINEER],
        'assigned_to': user_ids[Roles.EMPLOYEE],
        'priority': TaskPriority.HIGH,
        'status': IssueStatus.OPEN,
        'due_date': '2026-08-20',
        'photos': [],
        'created_at': datetime.utcnow()
    })
    
    # 13. System Notifications
    db.notifications.insert_one({
        'user_id': user_ids[Roles.PROJECT_MANAGER],
        'title': 'New Material Request',
        'message': 'Site Block A submitted an indent request for Portland Cement.',
        'type': 'material_request',
        'link': '/procurement/',
        'is_read': False,
        'created_at': datetime.utcnow()
    })
    
    logger.info("Successfully seeded database with complete mock records!")
    
if __name__ == '__main__':
    seed_db()
