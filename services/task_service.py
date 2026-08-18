import logging
from datetime import datetime
from database.mongodb import get_db
from utils.helpers import to_object_id
from utils.constants import TaskStatus

logger = logging.getLogger(__name__)

def create_task(project_id, site_id, title, description, assigned_employee_ids, start_date, due_date, priority, parent_task_id=None):
    db = get_db()
    task_doc = {
        'project_id': to_object_id(project_id),
        'site_id': to_object_id(site_id),
        'title': title,
        'description': description,
        'assigned_employee_ids': [to_object_id(uid) for uid in assigned_employee_ids if uid],
        'start_date': start_date,
        'due_date': due_date,
        'priority': priority,
        'status': TaskStatus.NOT_STARTED,
        'progress': 0,
        'parent_task_id': to_object_id(parent_task_id) if parent_task_id else None,
        'created_at': datetime.utcnow(),
        'updated_at': datetime.utcnow()
    }
    
    res = db.tasks.insert_one(task_doc)
    task_doc['_id'] = res.inserted_id
    
    # send notification
    for uid in task_doc['assigned_employee_ids']:
        db.notifications.insert_one({
            'user_id': uid,
            'title': "New Task Assigned",
            'message': f"You have been assigned to task: {title}",
            'type': "task_assigned",
            'link': f"/tasks/view/{task_doc['_id']}",
            'is_read': False,
            'created_at': datetime.utcnow()
        })
        
    return task_doc

def add_task_comment(task_id, user_id, comment, file_path=None, original_name=None):
    db = get_db()
    comment_doc = {
        'task_id': to_object_id(task_id),
        'user_id': to_object_id(user_id),
        'comment': comment,
        'file_path': file_path,
        'original_name': original_name,
        'created_at': datetime.utcnow()
    }
    db.task_comments.insert_one(comment_doc)
    return comment_doc
