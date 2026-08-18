# Utils package initialization
from utils.helpers import format_datetime

# Export useful functions for templates
def init_utils(app):
    app.jinja_env.filters['datetime'] = format_datetime
