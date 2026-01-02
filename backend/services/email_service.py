import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from core.config import SMTP_SERVER, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, SMTP_FROM_EMAIL

def send_email(to_email: str, subject: str, body: str):
    if not SMTP_USERNAME or not SMTP_PASSWORD:
        print("SMTP credentials not set. Skipping email.")
        return False

    try:
        msg = MIMEMultipart()
        msg['From'] = SMTP_FROM_EMAIL
        msg['To'] = to_email
        msg['Subject'] = subject

        msg.attach(MIMEText(body, 'html'))

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        print(f"Email sent to {to_email}")
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False

def send_budget_alert(user_email: str, category: str, spent: float, limit: float, roast_message: str = None):
    subject = f"Budget Alert: {category} Limit Exceeded 🚨"
    
    roast_html = ""
    if roast_message:
        roast_html = f"""
        <div style="background-color: #ffebee; border-left: 4px solid #ef5350; padding: 15px; margin: 15px 0; font-style: italic; color: #b71c1c;">
            "{roast_message}"
        </div>
        """

    body = f"""
    <html>
      <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <h2 style="color: #d32f2f;">Budget Alert ⚠️</h2>
        <p>You have exceeded your budget for <strong>{category}</strong>.</p>
        
        {roast_html}
        
        <div style="background-color: #f5f5f5; padding: 15px; border-radius: 5px;">
            <p style="margin: 5px 0;"><strong>Current Spending:</strong> ₹{spent:.2f}</p>
            <p style="margin: 5px 0;"><strong>Budget Limit:</strong> ₹{limit:.2f}</p>
            <p style="margin: 5px 0; color: #d32f2f;"><strong>Overspent by:</strong> ₹{spent - limit:.2f}</p>
        </div>
        
        <p>Please review your expenses and try to get back on track!</p>
      </body>
    </html>
    """
    return send_email(user_email, subject, body)
