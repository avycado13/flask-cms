from app.extensions import db
import sqlalchemy.orm as so
from flask_security.models import fsqla_v3 as fsqla
from flask_security import UserMixin, RoleMixin
import secrets
from hashlib import md5
from typing import Optional
from flask import current_app
import redis
import rq
from app.search import add_to_index, remove_from_index, query_index
import sqlalchemy as sa
import json
from time import time


class SearchableMixin(object):
    @classmethod
    def search(cls, expression, page, per_page):
        ids, total = query_index(cls.__tablename__, expression, page, per_page)
        if total == 0:
            return [], 0
        when = []
        for i in range(len(ids)):
            when.append((ids[i], i))
        query = (
            sa.select(cls).where(cls.id.in_(ids)).order_by(db.case(*when, value=cls.id))
        )
        return db.session.scalars(query), total

    @classmethod
    def before_commit(cls, session):
        session._changes = {
            "add": list(session.new),
            "update": list(session.dirty),
            "delete": list(session.deleted),
        }

    @classmethod
    def after_commit(cls, session):
        for obj in session._changes["add"]:
            if isinstance(obj, SearchableMixin):
                add_to_index(obj.__tablename__, obj)
        for obj in session._changes["update"]:
            if isinstance(obj, SearchableMixin):
                add_to_index(obj.__tablename__, obj)
        for obj in session._changes["delete"]:
            if isinstance(obj, SearchableMixin):
                remove_from_index(obj.__tablename__, obj)
        session._changes = None

    @classmethod
    def reindex(cls):
        for obj in db.session.scalars(sa.select(cls)):
            add_to_index(cls.__tablename__, obj)


db.event.listen(db.session, "before_commit", SearchableMixin.before_commit)
db.event.listen(db.session, "after_commit", SearchableMixin.after_commit)

fsqla.FsModels.set_db_info(db)

roles_users = db.Table(
    "roles_users",
    db.Model.metadata,
    db.Column("user_id", db.Integer(), db.ForeignKey("user.id")),
    db.Column("role_id", db.Integer(), db.ForeignKey("role.id")),
    extend_existing=True,
)

blog_followers = db.Table(
    "blog_followers",
    db.Model.metadata,
    sa.Column("user_id", sa.Integer, sa.ForeignKey("user.id"), primary_key=True),
    sa.Column("blog_id", sa.Integer, sa.ForeignKey("blog.id"), primary_key=True),
)


class Blog(SearchableMixin, db.Model):
    __searchable__ = ["title", "description"]

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))

    author: so.Mapped["User"] = so.relationship("User", back_populates="blogs")
    posts = db.relationship("Post", back_populates="blog", cascade="all, delete-orphan")
    newsletter = so.mapped_column(sa.Boolean, default=False)


class Post(SearchableMixin, db.Model):
    __searchable__ = ["title", "content"]

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    content = db.Column(db.Text, nullable=False)
    blog_id = db.Column(db.Integer, db.ForeignKey("blog.id"))
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))

    created_at = db.Column(db.DateTime, default=db.func.now())
    updated_at = db.Column(db.DateTime, default=db.func.now(), onupdate=db.func.now())

    published = db.Column(db.Boolean, default=False)
    publish_in_newsletter = db.Column(db.Boolean, default=False)

    blog = db.relationship("Blog", back_populates="posts")
    author = db.relationship("User", back_populates="posts")
    comments = db.relationship("Comment", back_populates="post", cascade="all, delete")


class WebAuthn(db.Model, fsqla.FsWebAuthnMixin):
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"))
    user = db.relationship("User", back_populates="webauthn")


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)

    created_at = db.Column(db.DateTime, default=db.func.now())
    updated_at = db.Column(db.DateTime, default=db.func.now(), onupdate=db.func.now())

    post_id = db.Column(db.Integer, db.ForeignKey("post.id"))
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))

    post = db.relationship("Post", back_populates="comments")
    # user = db.relationship("User", back_populates="comments")


class User(db.Model, UserMixin):
    __searchable__ = ["blogs", "posts", "username"]

    @db.declared_attr
    def webauthn(cls):
        return db.relationship("WebAuthn", back_populates="user", cascade="all, delete")

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password = db.Column(db.String(255))
    active = db.Column(db.Boolean(), nullable=False)
    fs_uniquifier = db.Column(
        db.String(64),
        unique=True,
        nullable=False,
        default=lambda: secrets.token_urlsafe(32),
    )
    fs_webauthn_user_handle = db.Column(db.String(64), unique=True, nullable=True)
    last_login_at = db.Column(db.DateTime())
    current_login_at = db.Column(db.DateTime())
    last_login_ip = db.Column(db.String(100))
    current_login_ip = db.Column(db.String(100))
    roles = db.relationship(
        "Role", secondary=roles_users, backref=db.backref("users", lazy="dynamic")
    )
    comments = db.relationship("Comment", backref="user")
    blogs = db.relationship("Blog", backref="user")
    posts = db.relationship("Post", back_populates="author")
    login_count = db.Column(db.Integer)
    tf_totp_secret = db.Column(db.String(255), nullable=True)
    tf_primary_method = db.Column(db.String(255))
    username = db.Column(db.String(255), unique=True)
    notifications: so.WriteOnlyMapped["Notification"] = so.relationship(
        back_populates="user"
    )
    tasks: so.WriteOnlyMapped["Task"] = so.relationship(back_populates="user")

    def avatar(self, size):
        digest = md5(self.email.lower().encode("utf-8")).hexdigest()
        return f"https://www.gravatar.com/avatar/{digest}?d=identicon&s={size}"

    def add_notification(self, name, data):
        db.session.execute(self.notifications.delete().where(Notification.name == name))
        n = Notification(name=name, payload_json=json.dumps(data), user=self)
        db.session.add(n)
        return n

    def launch_task(self, name, description, *args, **kwargs):
        rq_job = current_app.task_queue.enqueue(f"app.{name}", self.id, *args, **kwargs)
        task = Task(id=rq_job.get_id(), name=name, description=description, user=self)
        db.session.add(task)
        return task

    def get_tasks_in_progress(self):
        query = self.tasks.select().where(Task.complete is False)
        return db.session.scalars(query)

    def get_task_in_progress(self, name):
        query = self.tasks.select().where(Task.name == name, Task.complete is False)
        return db.session.scalar(query)


class Role(db.Model, RoleMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    description = db.Column(db.String(255))
    # permissions = db.Column(AsaList(db.UnicodeText), nullable=True)


class Task(db.Model):
    id: so.Mapped[str] = so.mapped_column(sa.String(36), primary_key=True)
    name: so.Mapped[str] = so.mapped_column(sa.String(128), index=True)
    description: so.Mapped[Optional[str]] = so.mapped_column(sa.String(128))
    user_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey("user.id"))
    complete: so.Mapped[bool] = so.mapped_column(default=False)

    user: so.Mapped[User] = so.relationship(back_populates="tasks")

    def get_rq_job(self):
        try:
            rq_job = rq.job.Job.fetch(self.id, connection=current_app.redis)
        except (redis.exceptions.RedisError, rq.exceptions.NoSuchJobError):
            return None
        return rq_job

    def get_progress(self):
        job = self.get_rq_job()
        return job.meta.get("progress", 0) if job is not None else 100


class Notification(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    name: so.Mapped[str] = so.mapped_column(sa.String(128), index=True)
    user_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey(User.id), index=True)
    timestamp: so.Mapped[float] = so.mapped_column(index=True, default=time)
    payload_json: so.Mapped[str] = so.mapped_column(sa.Text)

    user: so.Mapped[User] = so.relationship(back_populates="notifications")

    def get_data(self):
        return json.loads(str(self.payload_json))
