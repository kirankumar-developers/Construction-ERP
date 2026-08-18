import logging
from database.mongodb import get_db

logger = logging.getLogger(__name__)

def create_indexes():
    """
    Creates indexes on MongoDB collections to ensure constraints and search performance.
    """
    db = get_db()
    
    try:
        # Users
        db.users.create_index('email', unique=True)
        
        # Projects
        db.projects.create_index('project_code', unique=True)
        db.projects.create_index('manager_id')
        db.projects.create_index('client_id')
        db.projects.create_index('status')
        
        # Sites
        db.sites.create_index('site_code', unique=True)
        db.sites.create_index('project_id')
        db.sites.create_index('engineer_id')
        db.sites.create_index('supervisor_id')
        
        # Tasks
        db.tasks.create_index('project_id')
        db.tasks.create_index('site_id')
        db.tasks.create_index('parent_task_id')
        db.tasks.create_index('status')
        
        # BOQ
        db.boq.create_index('boq_number', unique=True)
        db.boq.create_index('project_id')
        
        # Budgets
        db.budgets.create_index([('project_id', 1), ('category', 1)], unique=True)
        
        # DPR
        db.dpr.create_index('project_id')
        db.dpr.create_index('site_id')
        db.dpr.create_index('date')
        db.dpr.create_index('status')
        
        # Materials
        db.materials.create_index('material_code', unique=True)
        db.materials.create_index('category_id')
        
        # Material Categories
        db.material_categories.create_index('name', unique=True)
        
        # Inventory
        db.inventory.create_index([('material_id', 1), ('project_id', 1), ('site_id', 1), ('warehouse_name', 1)], unique=True)
        
        # Inventory Transactions
        db.inventory_transactions.create_index('material_id')
        db.inventory_transactions.create_index('project_id')
        db.inventory_transactions.create_index('site_id')
        db.inventory_transactions.create_index('created_at')
        
        # Material Requests
        db.material_requests.create_index('request_number', unique=True)
        db.material_requests.create_index('project_id')
        db.material_requests.create_index('site_id')
        db.material_requests.create_index('status')
        
        # RFQs
        db.rfqs.create_index('rfq_number', unique=True)
        db.rfqs.create_index('request_id')
        
        # Vendor Quotations
        db.vendor_quotations.create_index([('rfq_id', 1), ('vendor_id', 1)], unique=True)
        
        # Purchase Orders
        db.purchase_orders.create_index('po_number', unique=True)
        db.purchase_orders.create_index('vendor_id')
        db.purchase_orders.create_index('project_id')
        db.purchase_orders.create_index('status')
        
        # GRN
        db.grn.create_index('grn_number', unique=True)
        db.grn.create_index('po_id')
        
        # Vendors
        db.vendors.create_index('company_name')
        db.vendors.create_index('email', unique=True)
        
        # Employees
        db.employees.create_index('user_id')
        db.employees.create_index('employee_id', unique=True)
        
        # Labours
        db.labours.create_index('labour_id', unique=True)
        db.labours.create_index('project_id')
        db.labours.create_index('site_id')
        
        # Attendance
        db.attendance.create_index([('employee_type', 1), ('ref_id', 1), ('date', 1)], unique=True)
        
        # Subcontractors
        db.subcontractors.create_index('company_name')
        db.subcontractors.create_index('email', unique=True)
        
        # Work Orders
        db.work_orders.create_index('work_order_number', unique=True)
        db.work_orders.create_index('subcontractor_id')
        db.work_orders.create_index('project_id')
        
        # Equipment
        db.equipment.create_index('equipment_id', unique=True)
        db.equipment.create_index('project_id')
        db.equipment.create_index('site_id')
        db.equipment.create_index('status')
        
        # Equipment Usage
        db.equipment_usage.create_index('equipment_id')
        db.equipment_usage.create_index('project_id')
        
        # Equipment Maintenance
        db.equipment_maintenance.create_index('equipment_id')
        
        # Expenses
        db.expenses.create_index('project_id')
        db.expenses.create_index('site_id')
        db.expenses.create_index('category')
        db.expenses.create_index('status')
        
        # Invoices
        db.invoices.create_index('invoice_number', unique=True)
        db.invoices.create_index('project_id')
        db.invoices.create_index('client_id')
        
        # Payments
        db.payments.create_index([('reference_type', 1), ('reference_id', 1)])
        
        # Inspections
        db.inspections.create_index('project_id')
        db.inspections.create_index('site_id')
        db.inspections.create_index('result')
        
        # Issues
        db.issues.create_index('issue_number', unique=True)
        db.issues.create_index('project_id')
        db.issues.create_index('site_id')
        db.issues.create_index('status')
        
        # Documents
        db.documents.create_index('project_id')
        db.documents.create_index('site_id')
        db.documents.create_index('category')
        
        # Notifications
        db.notifications.create_index([('user_id', 1), ('is_read', 1)])
        db.notifications.create_index('created_at')
        
        # Activity Logs
        db.activity_logs.create_index('user_id')
        db.activity_logs.create_index('timestamp')
        
        logger.info("Successfully created all database indexes.")
    except Exception as e:
        logger.error(f"Error creating database indexes: {e}")
        raise e
