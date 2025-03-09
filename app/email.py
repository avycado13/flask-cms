from threading import Thread
from flask import current_app
from flask_mail import Message
from extensions import mail
from typing import Any


def send_async_email(app, msg):
    with app.app_context():
        mail.send(msg)


def send_email(
    subject: str,
    sender: str | tuple[str, str] | None,
    recipients: list[str | tuple[str, str]] | None,
    text_body: Any | str | None,
    html_body: Any | str | None,
    attachments=None,
    sync=False,
):
    msg = Message(subject, sender=sender, recipients=recipients)
    msg.body = text_body
    msg.html = html_body
    if attachments:
        for attachment in attachments:
            msg.attach(*attachment)
    if sync:
        mail.send(msg)
    else:
        Thread(
            target=send_async_email, args=(current_app._get_current_object(), msg)
        ).start()
