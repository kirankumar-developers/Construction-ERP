import logging
from pymongo import MongoClient
from config import Config

logger = logging.getLogger(__name__)

client = None
db = None

def init_db(app=None):
    """
    Initialize the PyMongo Client using the configured MONGO_URI.
    Supports deferred initialization with a Flask app instance.
    """
    global client, db
    
    # Override DNS resolver to use Google DNS, bypassing local timeouts
    try:
        import dns.resolver
        dns.resolver.default_resolver = dns.resolver.Resolver(configure=False)
        dns.resolver.default_resolver.nameservers = ['8.8.8.8', '8.8.4.4']
        logger.info("Configured dnspython to query Google DNS (8.8.8.8) directly.")
    except Exception as dns_e:
        logger.warning(f"Failed to override DNS resolver: {dns_e}")
        
    mongo_uri = Config.MONGO_URI
    if app:
        mongo_uri = app.config.get('MONGO_URI', mongo_uri)
        
    try:
        client = MongoClient(mongo_uri)
        # Verify connection by pinging
        client.admin.command('ping')
        
        # Parse database name from URI, default to 'onsite_service_db' if not provided
        # Example URI: mongodb://localhost:27017/onsite_service_db
        db_name = 'onsite_service_db'
        if '/' in mongo_uri.replace('mongodb://', '').replace('mongodb+srv://', ''):
            parts = mongo_uri.split('/')
            if parts[-1]:
                # Split any query params (e.g. ?retryWrites=true)
                db_name = parts[-1].split('?')[0]
                
        db = client[db_name]
        logger.info(f"Successfully connected to MongoDB: {db_name}")
        return db
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        raise e

def get_db():
    """
    Returns the database reference. Initializes if not already done.
    """
    global db
    if db is None:
        db = init_db()
    return db
