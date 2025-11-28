import smtplib
from email.mime.text import MIMEText


def send_failure_email(to, pipeline_name, errors):
    msg = MIMEText(f"""
    Ombudsman pipeline FAILED.

    Pipeline: {pipeline_name}
    Errors: {errors}
    """)
    msg["Subject"] = f"❌ Ombudsman Pipeline Failure: {pipeline_name}"
    msg["To"] = to
    msg["From"] = "ombudsman@system.local"

    with smtplib.SMTP("smtp.yourcompany.com") as s:
        s.send_message(msg)