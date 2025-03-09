import pytest
from flask import url_for, current_app
from flask.testing import FlaskClient
from test_utils import set_current_user
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import db, security
from app.models import User, Blog, Post


def test_index(client: FlaskClient):
    response = client.get(url_for("main.index"))
    assert response.status_code == 200
    assert b"No blogs created yet." in response.data


def test_blog_view(client: FlaskClient):
    security.datastore.create_user(
        username="testuser", email="test@example.com", active=True
    )
    user = User(username="testuser", email="test@example.com", active=True)

    blog = Blog(title="Test Blog", description="Test Description", user_id=user.id)
    db.session.add(blog)
    db.session.commit()

    response = client.get(url_for("main.view_blog", blog_id=blog.id))
    assert response.status_code == 200
    assert b"Test Blog" in response.data
    assert b"Test Description" in response.data


def test_view_post(client: FlaskClient):
    security.datastore.create_user(
        username="testuser", email="test@example.com", active=True
    )
    user = User(username="testuser", email="test@example.com", active=True)

    blog = Blog(title="Test Blog", description="Test Description", user_id=user.id)
    db.session.add(blog)
    db.session.commit()

    post = Post(title="Test Post", content="Test Content", blog_id=blog.id)
    db.session.add(post)
    db.session.commit()

    response = client.get(url_for("main.view_post", post_id=post.id))
    assert response.status_code == 200
    assert b"Test Post" in response.data
    assert b"Test Content" in response.data


def test_blog_admin_access_denied(client: FlaskClient):
    security.datastore.create_user(
        username="testuser", email="test@example.com", active=True
    )
    user = User(username="testuser", email="test@example.com", active=True)

    blog = Blog(title="Test Blog", description="Test Description", user_id=user.id)
    db.session.add(blog)
    db.session.commit()

    response = client.get(url_for("main.blog_admin", blog_id=blog.id))
    assert response.status_code == 302  # Redirect to login


def test_create_blog(client: FlaskClient):
    security.datastore.create_user(
        username="testuser", email="test@example.com", active=True
    )
    set_current_user(client.application, security.datastore, "test@example.com")
    user = User(username="testuser", email="test@example.com", active=True)

    response = client.post(
        url_for("main.admin"),
        data={"title": "New Blog", "description": "New Description"},
        follow_redirects=True,
        headers={current_app.config["SECURITY_TOKEN_AUTHENTICATION_HEADER"]: "token"},
    )

    assert response.status_code == 200
    assert response.request.path == "/"
    # assert b'Blog created successfully!' in response.data
    # assert b'New Blog' in response.data
    # assert b'New Description' in response.data
