from routes.auth import auth_bp
from routes.dashboard import dashboard_bp
from routes.users import users_bp
from routes.projects import projects_bp
from routes.sites import sites_bp
from routes.tasks import tasks_bp
from routes.boq import boq_bp
from routes.budget import budget_bp
from routes.dpr import dpr_bp
from routes.materials import materials_bp
from routes.procurement import procurement_bp
from routes.vendors import vendors_bp
from routes.labour import labour_bp
from routes.attendance import attendance_bp
from routes.subcontractors import subcontractors_bp
from routes.equipment import equipment_bp
from routes.expenses import expenses_bp
from routes.invoices import invoices_bp
from routes.payments import payments_bp
from routes.quality import quality_bp
from routes.issues import issues_bp
from routes.documents import documents_bp
from routes.notifications import notifications_bp
from routes.reports import reports_bp
from routes.clients import clients_bp
from routes.project_managers import project_managers_bp

def register_blueprints(app):
    """
    Registers all blueprints with the Flask application instance.
    """
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(projects_bp)
    app.register_blueprint(sites_bp)
    app.register_blueprint(tasks_bp)
    app.register_blueprint(boq_bp)
    app.register_blueprint(budget_bp)
    app.register_blueprint(dpr_bp)
    app.register_blueprint(materials_bp)
    app.register_blueprint(procurement_bp)
    app.register_blueprint(vendors_bp)
    app.register_blueprint(labour_bp)
    app.register_blueprint(attendance_bp)
    app.register_blueprint(subcontractors_bp)
    app.register_blueprint(equipment_bp)
    app.register_blueprint(expenses_bp)
    app.register_blueprint(invoices_bp)
    app.register_blueprint(payments_bp)
    app.register_blueprint(quality_bp)
    app.register_blueprint(issues_bp)
    app.register_blueprint(documents_bp)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(clients_bp)
    app.register_blueprint(project_managers_bp)
