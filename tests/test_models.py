import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.models import User, Role, Blog, Post, WebAuthn
import pytest


def test_new_user():
    """
    GIVEN a User model
    WHEN a new User is created
    THEN check the email, password, and active fields are defined correctly
    """
    user = User(email="testytest@gmail.com", password="FlaskIsAwesome", active=True)
    assert user.email == "testytest@gmail.com"
    assert user.password == "FlaskIsAwesome"
    assert user.active is True


def test_new_role():
    """
    GIVEN a Role model
    WHEN a new Role is created
    THEN check the name and description fields are defined correctly
    """
    role = Role(name="Admin", description="Administrator role")
    assert role.name == "Admin"
    assert role.description == "Administrator role"


def test_new_blog():
    """
    GIVEN a Blog model
    WHEN a new Blog is created
    THEN check the title, description, and user_id fields are defined correctly
    """
    blog = Blog(title="My Blog", description="This is my blog", user_id=1)
    assert blog.title == "My Blog"
    assert blog.description == "This is my blog"
    assert blog.user_id == 1


def test_new_post():
    """
    GIVEN a Post model
    WHEN a new Post is created
    THEN check the title, content, and blog_id fields are defined correctly
    """
    post = Post(title="My Post", content="This is my post content", blog_id=1)
    assert post.title == "My Post"
    assert post.content == "This is my post content"
    assert post.blog_id == 1


def test_new_webauthn():
    """
    GIVEN a WebAuthn model
    WHEN a new WebAuthn is created
    THEN check the user_id field is defined correctly
    """
    webauthn = WebAuthn(user_id=1)
    assert webauthn.user_id == 1


def test_user_roles_relationship():
    """
    GIVEN a User and Role model
    WHEN a User is assigned a Role
    THEN check the relationship is defined correctly
    """
    user = User(email="testytest@gmail.com", password="FlaskIsAwesome", active=True)
    role = Role(name="Admin", description="Administrator role")
    user.roles.append(role)
    assert role in user.roles
