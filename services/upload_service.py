import os
import uuid
import logging
from werkzeug.utils import secure_filename
from config import Config

logger = logging.getLogger(__name__)

# Try importing cloudinary if it is configured
cloudinary_configured = False
if Config.CLOUDINARY_URL:
    try:
        import cloudinary
        import cloudinary.uploader
        # Cloudinary parses CLOUDINARY_URL automatically from environment if imported
        cloudinary_configured = True
        logger.info("Cloudinary configuration detected and loaded.")
    except ImportError:
        logger.warning("Cloudinary library is not installed. Falling back to local storage.")

def upload_file(file):
    """
    Saves an uploaded file.
    If Cloudinary is configured, uploads to Cloudinary.
    Otherwise, saves to local static/uploads/ folder.
    
    Returns (file_url, filename) or (None, error_msg)
    """
    if not file or file.filename == '':
        return None, "No file selected."
        
    filename = secure_filename(file.filename)
    # Append a unique ID to avoid overwriting files with the same name
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    base = filename.rsplit('.', 1)[0] if '.' in filename else filename
    unique_filename = f"{base}_{uuid.uuid4().hex[:8]}.{ext}" if ext else f"{base}_{uuid.uuid4().hex[:8]}"
    
    # 1. Cloudinary upload fallback
    if cloudinary_configured:
        try:
            upload_result = cloudinary.uploader.upload(file, public_id=f"onsite_proofs/{unique_filename}")
            url = upload_result.get('secure_url')
            return url, unique_filename
        except Exception as e:
            logger.error(f"Cloudinary upload failed: {e}. Falling back to local storage.")
            
    # 2. Local storage upload
    try:
        upload_path = Config.UPLOAD_FOLDER
        if not os.path.exists(upload_path):
            os.makedirs(upload_path, exist_ok=True)
            
        full_path = os.path.join(upload_path, unique_filename)
        # Seek back to 0 just in case the file pointer was moved
        file.seek(0)
        file.save(full_path)
        
        # Public URL path for local files
        url = f"/static/uploads/{unique_filename}"
        return url, unique_filename
    except Exception as e:
        logger.error(f"Local file upload failed: {e}")
        return None, f"Failed to upload file: {str(e)}"
