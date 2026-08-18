import logging
from database.mongodb import get_db
from utils.helpers import to_object_id

logger = logging.getLogger(__name__)

def get_project_stats(project_id):
    db = get_db()
    pid = to_object_id(project_id)
    
    # Calculate task stats
    tasks = list(db.tasks.find({'project_id': pid}))
    total_tasks = len(tasks)
    completed_tasks = sum(1 for t in tasks if t.get('status') == 'completed')
    
    progress = 0
    if total_tasks > 0:
        progress = int((completed_tasks / total_tasks) * 100)
        
    return {
        'total_tasks': total_tasks,
        'completed_tasks': completed_tasks,
        'progress_percentage': progress
    }
