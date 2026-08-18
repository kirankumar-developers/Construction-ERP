import logging
from datetime import datetime
from bson import ObjectId
from database.mongodb import get_db
from utils.helpers import to_object_id
from config import Config

logger = logging.getLogger(__name__)

# Try to initialize Firebase Admin SDK if credentials JSON is configured
firebase_configured = False
if Config.FIREBASE_CREDENTIALS_JSON:
    try:
        import firebase_admin
        from firebase_admin import credentials, messaging
        
        # Initialize Firebase App
        cred = credentials.Certificate(Config.FIREBASE_CREDENTIALS_JSON)
        firebase_admin.initialize_app(cred)
        firebase_configured = True
        logger.info("Firebase Cloud Messaging configured successfully.")
    except Exception as e:
        logger.warning(f"Failed to initialize Firebase Admin SDK: {e}. FCM notifications will be skipped.")

def create_notification(user_id_str, title, message, notif_type='general'):
    """
    Creates an in-app notification in MongoDB.
    Attempts to send an FCM push notification if configured and user has a token.
    """
    db = get_db()
    user_id = to_object_id(user_id_str)
    if not user_id:
        return None
        
    notification_doc = {
        'user_id': user_id,
        'title': title,
        'message': message,
        'type': notif_type,
        'is_read': False,
        'created_at': datetime.utcnow()
    }
    
    db.notifications.insert_one(notification_doc)
    
    # Optional FCM integration
    if firebase_configured:
        # Fetch FCM tokens from user profile if stored (e.g. users.fcm_tokens)
        user = db.users.find_one({'_id': user_id})
        if user and 'fcm_tokens' in user:
            tokens = user['fcm_tokens']
            for token in tokens:
                try:
                    fcm_message = messaging.Message(
                        notification=messaging.Notification(
                            title=title,
                            body=message
                        ),
                        token=token
                    )
                    messaging.send(fcm_message)
                except Exception as ex:
                    logger.error(f"FCM message send failed: {ex}")
                    
    return notification_doc

def get_user_notifications(user_id_str, limit=50, unread_only=False):
    """
    Fetches notifications for a user, ordered by creation date descending.
    """
    db = get_db()
    user_id = to_object_id(user_id_str)
    if not user_id:
        return []
        
    query = {'user_id': user_id}
    if unread_only:
        query['is_read'] = False
        
    return list(db.notifications.find(query).sort('created_at', -1).limit(limit))

def get_unread_count(user_id_str):
    db = get_db()
    user_id = to_object_id(user_id_str)
    if not user_id:
        return 0
    return db.notifications.count_documents({'user_id': user_id, 'is_read': False})

def mark_notification_as_read(notif_id_str):
    db = get_db()
    notif_id = to_object_id(notif_id_str)
    if not notif_id:
        return False
    db.notifications.update_one({'_id': notif_id}, {'$set': {'is_read': True}})
    return True

def mark_all_notifications_as_read(user_id_str):
    db = get_db()
    user_id = to_object_id(user_id_str)
    if not user_id:
        return False
    db.notifications.update_many({'user_id': user_id, 'is_read': False}, {'$set': {'is_read': True}})
    return True
