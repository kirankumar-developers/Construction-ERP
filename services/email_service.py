import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import Config

logger = logging.getLogger(__name__)

def send_email(to_email, subject, body_html):
    """
    Sends an HTML email using SMTP configuration.
    If credentials are not configured, it logs the email content to console and returns True.
    """
    smtp_host = Config.SMTP_HOST
    smtp_port = Config.SMTP_PORT
    smtp_user = Config.SMTP_USER
    smtp_password = Config.SMTP_PASSWORD
    from_email = Config.SMTP_FROM_EMAIL
    
    # Console-logging fallback if SMTP credentials are not filled
    if not smtp_user or not smtp_password:
        logger.warning("SMTP credentials are not configured. Logging email instead:")
        logger.warning(f"TO: {to_email}")
        logger.warning(f"SUBJECT: {subject}")
        logger.warning(f"BODY:\n{body_html}\n--- End of Email ---")
        return True
        
    try:
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = from_email
        msg['To'] = to_email
        
        # Attach HTML body
        msg.attach(MIMEText(body_html, 'html'))
        
        # Establish connection
        server = smtplib.SMTP(smtp_host, smtp_port)
        server.ehlo()
        server.starttls() # Enable TLS
        server.ehlo()
        server.login(smtp_user, smtp_password)
        server.sendmail(from_email, to_email, msg.as_string())
        server.close()
        
        logger.info(f"Successfully sent email to {to_email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        return False

def send_assignment_email(employee_email, employee_name, job_number, job_title):
    subject = f"New Job Assignment: {job_number}"
    body = f"""
    <html>
      <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <h2 style="color: #0d6efd;">Hello {employee_name},</h2>
        <p>You have been assigned to a new service job on the Onsite Service Management System.</p>
        <p><strong>Job Details:</strong></p>
        <ul>
          <li><strong>Job Number:</strong> {job_number}</li>
          <li><strong>Job Title:</strong> {job_title}</li>
        </ul>
        <p>Please log in to your employee dashboard to accept the job, view details, and navigate to the job site.</p>
        <p style="margin-top: 30px;">Best regards,<br/>Onsite Service Team</p>
      </body>
    </html>
    """
    return send_email(employee_email, subject, body)

def send_status_update_email(customer_email, customer_name, job_number, new_status):
    subject = f"Job Status Update: {job_number}"
    body = f"""
    <html>
      <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <h2 style="color: #0d6efd;">Dear {customer_name},</h2>
        <p>The status of your service job <strong>{job_number}</strong> has been updated.</p>
        <p><strong>New Status:</strong> <span style="background-color: #f1f3f5; padding: 4px 8px; border-radius: 4px; font-weight: bold;">{new_status.upper()}</span></p>
        <p>Log in to your customer portal to track the real-time progress and view service notes.</p>
        <p style="margin-top: 30px;">Best regards,<br/>Onsite Service Team</p>
      </body>
    </html>
    """
    return send_email(customer_email, subject, body)

def send_invoice_email(customer_email, customer_name, invoice_number, total_amount):
    subject = f"New Invoice Generated: {invoice_number}"
    body = f"""
    <html>
      <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <h2 style="color: #0d6efd;">Dear {customer_name},</h2>
        <p>An invoice has been generated for your recent service request.</p>
        <p><strong>Invoice details:</strong></p>
        <ul>
          <li><strong>Invoice Number:</strong> {invoice_number}</li>
          <li><strong>Total Amount Due:</strong> ${total_amount:.2f}</li>
        </ul>
        <p>Please log in to your portal to view the line items and proceed with your payment.</p>
        <p style="margin-top: 30px;">Best regards,<br/>Onsite Service Team</p>
      </body>
    </html>
    """
    return send_email(customer_email, subject, body)
