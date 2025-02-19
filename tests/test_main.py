import pytest
from flask import url_for
from app import db
from app.models import User, Blog, Post
from test_utils import set_current_user

def test_index(client):
    response = client.get(url_for('main.index'))
    assert response.status_code == 200
    assert b'No blogs created yet.' in response.data

def test_blog_view(client):
    user = User(username='testuser', email='test@example.com')
    db.session.add(user)
    db.session.commit()

    blog = Blog(title='Test Blog', description='Test Description', user_id=user.id)
    db.session.add(blog)
    db.session.commit()

    response = client.get(url_for('main.blog_view', blog_id=blog.id))
    assert response.status_code == 200
    assert b'Test Blog' in response.data
    assert b'Test Description' in response.data

def test_view_post(client):
    user = User(username='testuser', email='test@example.com')
    db.session.add(user)
    db.session.commit()

    blog = Blog(title='Test Blog', description='Test Description', user_id=user.id)
    db.session.add(blog)
    db.session.commit()

    post = Post(title='Test Post', content='Test Content', blog_id=blog.id)
    db.session.add(post)
    db.session.commit()

    response = client.get(url_for('main.view_post', post_id=post.id))
    assert response.status_code == 200
    assert b'Test Post' in response.data
    assert b'Test Content' in response.data

def test_blog_admin_access_denied(client):
    user = User(username='testuser', email='test@example.com')
    db.session.add(user)
    db.session.commit()

    blog = Blog(title='Test Blog', description='Test Description', user_id=user.id)
    db.session.add(blog)
    db.session.commit()

    response = client.get(url_for('main.blog_admin', blog_id=blog.id))
    assert response.status_code == 302  # Redirect to login

def test_create_blog(client):
    user = User(username='testuser', email='test@example.com')
    db.session.add(user)
    db.session.commit()

    with client.session_transaction() as sess:
        sess['user_id'] = user.id  # Ensure session matches how login is implemented

    response = client.post(url_for('main.admin'), data={
        'title': 'New Blog',
        'description': 'New Description'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b'Blog created successfully!' in response.data
    assert b'New Blog' in response.data
    assert b'New Description' in response.data
