class Roles:
    SUPER_ADMIN = 'super_admin'
    ADMIN = 'admin'
    PROJECT_MANAGER = 'project_manager'
    SITE_ENGINEER = 'site_engineer'
    SUPERVISOR = 'supervisor'
    EMPLOYEE = 'employee'  # Staff
    LABOUR = 'labour'
    VENDOR = 'vendor'      # Supplier
    SUBCONTRACTOR = 'subcontractor'
    CLIENT = 'client'
    
    ALL_ROLES = [
        SUPER_ADMIN, ADMIN, PROJECT_MANAGER, SITE_ENGINEER, SUPERVISOR,
        EMPLOYEE, LABOUR, VENDOR, SUBCONTRACTOR, CLIENT
    ]

class ProjectStatus:
    PLANNING = 'planning'
    ACTIVE = 'active'
    ON_HOLD = 'on_hold'
    COMPLETED = 'completed'
    CANCELLED = 'cancelled'
    ALL = [PLANNING, ACTIVE, ON_HOLD, COMPLETED, CANCELLED]

class ProjectPriority:
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'
    CRITICAL = 'critical'
    ALL = [LOW, MEDIUM, HIGH, CRITICAL]

class SiteStatus:
    ACTIVE = 'active'
    ON_HOLD = 'on_hold'
    COMPLETED = 'completed'
    ALL = [ACTIVE, ON_HOLD, COMPLETED]

class TaskStatus:
    NOT_STARTED = 'not_started'
    IN_PROGRESS = 'in_progress'
    ON_HOLD = 'on_hold'
    COMPLETED = 'completed'
    DELAYED = 'delayed'
    ALL = [NOT_STARTED, IN_PROGRESS, ON_HOLD, COMPLETED, DELAYED]

class TaskPriority:
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'
    CRITICAL = 'critical'
    ALL = [LOW, MEDIUM, HIGH, CRITICAL]

class IndentStatus:
    PENDING = 'pending'
    APPROVED = 'approved'
    REJECTED = 'rejected'
    RFQ_CREATED = 'rfq_created'
    PO_CREATED = 'po_created'
    GRN_CREATED = 'grn_created'
    ALL = [PENDING, APPROVED, REJECTED, RFQ_CREATED, PO_CREATED, GRN_CREATED]

class RFQStatus:
    OPEN = 'open'
    CLOSED = 'closed'
    ALL = [OPEN, CLOSED]

class QuoteStatus:
    RECEIVED = 'received'
    SELECTED = 'selected'
    REJECTED = 'rejected'
    ALL = [RECEIVED, SELECTED, REJECTED]

class POStatus:
    PENDING = 'pending'
    APPROVED = 'approved'
    SHIPPED = 'shipped'
    DELIVERED = 'delivered'
    CANCELLED = 'cancelled'
    ALL = [PENDING, APPROVED, SHIPPED, DELIVERED, CANCELLED]

class EquipmentStatus:
    AVAILABLE = 'available'
    IN_USE = 'in_use'
    MAINTENANCE = 'maintenance'
    INACTIVE = 'inactive'
    ALL = [AVAILABLE, IN_USE, MAINTENANCE, INACTIVE]

class ExpenseStatus:
    PENDING = 'pending'
    APPROVED = 'approved'
    REJECTED = 'rejected'
    ALL = [PENDING, APPROVED, REJECTED]

class InvoiceStatus:
    DRAFT = 'draft'
    SENT = 'sent'
    PARTIAL = 'partial'
    PAID = 'paid'
    OVERDUE = 'overdue'
    ALL = [DRAFT, SENT, PARTIAL, PAID, OVERDUE]

class PaymentStatus:
    PENDING = 'pending'
    PARTIAL = 'partial'
    PAID = 'paid'
    OVERDUE = 'overdue'
    ALL = [PENDING, PARTIAL, PAID, OVERDUE]

class InspectionResult:
    PENDING = 'pending'
    APPROVED = 'approved'
    REJECTED = 'rejected'
    NEEDS_CORRECTION = 'needs_correction'
    ALL = [PENDING, APPROVED, REJECTED, NEEDS_CORRECTION]

class IssueStatus:
    OPEN = 'open'
    ASSIGNED = 'assigned'
    IN_PROGRESS = 'in_progress'
    RESOLVED = 'resolved'
    CLOSED = 'closed'
    ALL = [OPEN, ASSIGNED, IN_PROGRESS, RESOLVED, CLOSED]

class DocumentCategory:
    DRAWINGS = 'drawings'
    BOQ = 'boq'
    CONTRACTS = 'contracts'
    REPORTS = 'reports'
    INVOICES = 'invoices'
    SITE_PHOTOS = 'site_photos'
    QUALITY_DOCUMENTS = 'quality_documents'
    OTHER = 'other'
    ALL = [DRAWINGS, BOQ, CONTRACTS, REPORTS, INVOICES, SITE_PHOTOS, QUALITY_DOCUMENTS, OTHER]
