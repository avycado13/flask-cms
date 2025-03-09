from flask import Flask
import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.email import send_email
from app.extensions import mail


def test_send_email(app: Flask):
    with app.app_context():
        with mail.record_messages() as outbox:
            send_email(
                subject="testing",
                sender="joe@gmail.com",  # sender email
                recipients=["bob@gmail.com"],  # recipient email
                text_body="testing",
                html_body="<p>testing</p>",  # html body
                sync=True,
            )
            assert len(outbox) == 1
            assert outbox[0].subject == "testing"


def test_send_async_email(app: Flask):
    with app.app_context():
        with mail.record_messages() as outbox:
            send_email(
                subject="testing",
                sender="joe@gmail.com",  # sender email
                recipients=["bob@gmail.com"],  # recipient email
                text_body="testing",
                html_body="<p>testing</p>",  # html body
                sync=False,
            )
            assert len(outbox) == 1
            assert outbox[0].subject == "testing"
