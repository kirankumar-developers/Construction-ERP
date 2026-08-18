import re
from email_validator import validate_email as val_email, EmailNotValidError
from config import Config

def validate_email(email):
    """
    Validates email format using the email-validator library.
    Returns (is_valid, normalized_email_or_error_msg)
    """
    if not email:
        return False, "Email address is required."
    try:
        # Validate and normalize
        valid = val_email(email)
        return True, valid.email
    except EmailNotValidError as e:
        return False, str(e)

def validate_password(password):
    """
    Validates that password meets security requirements:
    - Minimum 6 characters
    """
    if not password:
        return False, "Password is required."
    if len(password) < 6:
        return False, "Password must be at least 6 characters long."
    return True, None

def validate_phone(phone):
    """
    Validates phone number formatting using a regex match.
    Allow international formats, spaces, dashes, parentheses.
    """
    if not phone:
        return False, "Phone number is required."
    
    # Matches digits, +, -, spaces, and parentheses. Minimum 7 digits.
    clean_phone = re.sub(r'[\s\-\(\)\+]', '', phone)
    if not clean_phone.isdigit() or len(clean_phone) < 7:
        return False, "Invalid phone number. Must contain at least 7 digits."
    return True, None

def allowed_file(filename):
    """
    Checks if the file extension is allowed.
    """
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS
