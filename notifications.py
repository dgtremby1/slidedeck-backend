import os
import smtplib
import ssl
from email.message import EmailMessage


class Notifier:
    def __init__(self):
        self.smtp = smtplib.SMTP_SSL("smtp.gmail.com", port=465, context=ssl.create_default_context())
        self.smtp.login(os.getenv("EMAIL_ADDRESS"), os.getenv("EMAIL_PASSWORD"))
        pass

    def email(self, contents, subject, sender, recipient):
        msg = EmailMessage()
        msg.set_content(contents)
        msg["Subject"] = subject
        msg["From"] = sender
        msg["To"] = recipient
        self.smtp.send_message(msg)
