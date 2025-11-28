'''
Notification Hooks (Slack + Email)
'''

# src/ombudsman/notifications/email.py

import smtplib
from email.mime.text import MIMEText

def send_email(smtp_host, from_addr, to_addr, subject, body):
    msg = MIMEText(body)
    msg["From"] = from_addr
    msg["To"] = to_addr
    msg["Subject"] = subject

    with smtplib.SMTP(smtp_host) as s:
        s.sendmail(from_addr, [to_addr], msg.as_string())