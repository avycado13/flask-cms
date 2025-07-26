from datetime import datetime
from app.extensions import db
import sqlalchemy.orm as so
from flask_security.models import fsqla_v3 as fsqla
from authlib.integrations.sqla_oauth2 import OAuth2ClientMixin, OAuth2TokenMixin
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
    sa.Column("user_id", sa.Integer, sa.ForeignKey("user.id")),
    sa.Column("role_id", sa.Integer, sa.ForeignKey("role.id")),
    extend_existing=True,
)

blog_followers = db.Table(
    "blog_followers",
    db.Model.metadata,
    sa.Column("user_id", sa.Integer, sa.ForeignKey("user.id"), primary_key=True),
    sa.Column("blog_id", sa.Integer, sa.ForeignKey("blog.id"), primary_key=True),
)


class Client(db.Model, OAuth2ClientMixin):
    id: so.Mapped[int] = so.mapped_column(sa.Integer, primary_key=True)
    user_id: so.Mapped[int] = so.mapped_column(sa.Integer, sa.ForeignKey("user.id", ondelete="CASCADE"))
    user: so.Mapped["User"] = so.relationship("User")


class Token(db.Model, OAuth2TokenMixin):
    id: so.Mapped[int] = so.mapped_column(sa.Integer, primary_key=True)
    user_id: so.Mapped[int] = so.mapped_column(sa.Integer, db.ForeignKey("user.id", ondelete="CASCADE"))
    user: so.Mapped["User"] = so.relationship("User")


class Blog(SearchableMixin, db.Model):
    __searchable__ = ["title", "description", "slug", "posts", "pages"]

    id: so.Mapped[int] = so.mapped_column(sa.Integer, primary_key=True)
    title: so.Mapped[str] = so.mapped_column(sa.String(150), nullable=False)
    slug: so.Mapped[str] = so.mapped_column(sa.String(150), nullable=True)
    description: so.Mapped[str] = so.mapped_column(sa.Text, nullable=True)
    user_id: so.Mapped[int] = so.mapped_column(sa.Integer, sa.ForeignKey("user.id"))

    author: so.Mapped["User"] = so.relationship("User", back_populates="blogs")
    posts: so.Mapped[list["Post"]] = so.relationship("Post", back_populates="blog", cascade="all, delete-orphan")
    pages: so.Mapped[list["Page"]] = so.relationship("Page", back_populates="blog", cascade="all, delete-orphan")
    newsletter: so.Mapped[bool] = so.mapped_column(sa.Boolean, default=False)
    css: so.Mapped[str] = so.mapped_column(sa.Text, nullable=True)
    theme_id: so.Mapped[int] = so.mapped_column(sa.Integer, sa.ForeignKey("theme.id"), nullable=True)
    theme: so.Mapped["Theme"] = so.relationship("Theme", back_populates="blogs")
    webmentions: so.Mapped[list["Webmention"]] = so.relationship(
        "Webmention", back_populates="blog"
    )


class Post(SearchableMixin, db.Model):
    __searchable__ = ["title", "content"]

    id: so.Mapped[int] = so.mapped_column(sa.Integer, primary_key=True)
    title: so.Mapped[str] = so.mapped_column(sa.String(150), nullable=False)
    content: so.Mapped[str] = so.mapped_column(sa.Text, nullable=False)
    blog_id: so.Mapped[int] = so.mapped_column(sa.Integer, sa.ForeignKey("blog.id"))
    user_id: so.Mapped[int] = so.mapped_column(sa.Integer, sa.ForeignKey("user.id"))

    created_at: so.Mapped[datetime] = so.mapped_column(sa.DateTime, default=sa.func.now())
    updated_at: so.Mapped[datetime] = so.mapped_column(
        sa.DateTime, default=sa.func.now(), onupdate=sa.func.now()
    )
    language: so.Mapped[Optional[str]] = so.mapped_column(sa.String(5))
    published: so.Mapped[bool] = so.mapped_column(sa.Boolean, default=False)
    publish_in_newsletter: so.Mapped[bool] = so.mapped_column(sa.Boolean, default=False)

    blog: so.Mapped["Blog"] = so.relationship("Blog", back_populates="posts")
    author: so.Mapped["User"] = so.relationship("User", back_populates="posts")
    comments: so.Mapped[list["Comment"]] = so.relationship("Comment", back_populates="post", cascade="all, delete")


class Page(SearchableMixin, db.Model):
    __searchable__ = ["title", "content"]

    id = so.mapped_column(sa.Integer, primary_key=True)
    title = so.mapped_column(sa.String(150), nullable=False)
    content = so.mapped_column(sa.Text, nullable=False)
    blog_id = so.mapped_column(sa.Integer, sa.ForeignKey("blog.id"))
    user_id = so.mapped_column(sa.Integer, sa.ForeignKey("user.id"))

    created_at = so.mapped_column(sa.DateTime, default=sa.func.now())
    updated_at = so.mapped_column(
        sa.DateTime, default=sa.func.now(), onupdate=sa.func.now()
    )

    published = so.mapped_column(sa.Boolean, default=False)

    blog = so.relationship("Blog", back_populates="pages")
    author = so.relationship("User", back_populates="pages")


class WebAuthn(db.Model, fsqla.FsWebAuthnMixin):
    user_id = so.mapped_column(sa.Integer, sa.ForeignKey("user.id", ondelete="CASCADE"))
    user = so.relationship("User", back_populates="webauthn")


class Comment(db.Model):
    id = so.mapped_column(sa.Integer, primary_key=True)
    content = so.mapped_column(sa.Text, nullable=False)

    created_at = so.mapped_column(sa.DateTime, default=sa.func.now())
    updated_at = so.mapped_column(
        sa.DateTime, default=sa.func.now(), onupdate=sa.func.now()
    )

    post_id = so.mapped_column(sa.Integer, sa.ForeignKey("post.id"))
    user_id = so.mapped_column(sa.Integer, sa.ForeignKey("user.id"))

    post = so.relationship("Post", back_populates="comments")
    # user = db.relationship("User", back_populates="comments")


class User(db.Model, UserMixin):
    __searchable__ = ["blogs", "posts", "username"]

    @db.declared_attr
    def webauthn(cls):
        return so.relationship("WebAuthn", back_populates="user", cascade="all, delete")

    id: so.Mapped[int] = so.mapped_column(sa.Integer, primary_key=True)
    email: so.Mapped[str] = so.mapped_column(
        sa.String(255), unique=True, nullable=False
    )
    password: so.Mapped[str] = so.mapped_column(sa.String(255))
    active: so.Mapped[bool] = so.mapped_column(sa.Boolean(), nullable=False)
    fs_uniquifier: so.Mapped[str] = so.mapped_column(
        sa.String(64),
        unique=True,
        nullable=False,
        default=lambda: secrets.token_urlsafe(32),
    )
    fs_webauthn_user_handle: so.Mapped[str] = so.mapped_column(
        sa.String(64), unique=True, nullable=True
    )
    last_login_at: so.Mapped[Optional[datetime]] = so.mapped_column(sa.DateTime())
    current_login_at: so.Mapped[Optional[datetime]] = so.mapped_column(sa.DateTime())
    last_login_ip: so.Mapped[Optional[str]] = so.mapped_column(sa.String(100))
    current_login_ip: so.Mapped[Optional[str]] = so.mapped_column(sa.String(100))
    roles: so.Mapped[list["Role"]] = so.relationship(
        "Role", secondary=roles_users, backref=db.backref("users", lazy="dynamic")
    )
    comments: so.Mapped[list["Comment"]] = so.relationship("Comment", backref="user")
    blogs: so.Mapped[list["Blog"]] = so.relationship("Blog", back_populates="author")
    posts: so.Mapped[list["Post"]] = so.relationship("Post", back_populates="author")
    pages: so.Mapped[list["Page"]] = so.relationship("Page", back_populates="author")
    webmentions: so.Mapped[list["Webmention"]] = so.relationship(
        "Webmention", back_populates="user"
    )
    chirps: so.Mapped[list["Chirp"]] = so.relationship(
        "Chirp", back_populates="user"
    )
    login_count: so.Mapped[int] = so.mapped_column(sa.Integer, nullable=True)
    tf_totp_secret: so.Mapped[Optional[str]] = so.mapped_column(
        sa.String(255), nullable=True
    )
    tf_primary_method: so.Mapped[Optional[str]] = so.mapped_column(sa.String(255))
    username: so.Mapped[str] = so.mapped_column(sa.String(255), unique=True)
    notifications: so.WriteOnlyMapped["Notification"] = so.relationship(
        back_populates="user"
    )
    tasks: so.WriteOnlyMapped["Task"] = so.relationship(back_populates="user")
    themes: so.Mapped[list["Theme"]] = so.relationship("Theme", back_populates="user")
    about_me: so.Mapped[Optional[str]] = so.mapped_column(sa.Text, nullable=True)

    def get_user_id(self):
        return self.id

    def avatar(self, size):
        digest = md5(self.email.lower().encode("utf-8")).hexdigest()
        return f"https://www.gravatar.com/avatar/{digest}?d=identicon&s={size}?r=pg"

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
    id = so.mapped_column(sa.Integer, primary_key=True)
    name = so.mapped_column(sa.String(80), unique=True, nullable=False)
    description = so.mapped_column(sa.String(255))
    # permissions = db.Column(AsaList(db.UnicodeText), nullable=True)


class Task(db.Model):
    id: so.Mapped[str] = so.mapped_column(sa.String(36), primary_key=True)
    name: so.Mapped[str] = so.mapped_column(sa.String(128), index=True)
    description: so.Mapped[Optional[str]] = so.mapped_column(sa.String(128))
    user_id: so.Mapped[Optional[int]] = so.mapped_column(
        sa.ForeignKey("user.id"),
        nullable=True,  # This makes the foreign key column nullable in the database
    )
    complete: so.Mapped[bool] = so.mapped_column(default=False)

    user: so.Mapped[Optional[User]] = so.relationship(back_populates="tasks")

    def get_rq_job(self):
        try:
            rq_job = rq.job.Job.fetch(self.id, connection=current_app.redis)
        except (redis.exceptions.RedisError, rq.exceptions.NoSuchJobError):
            return None
        return rq_job

    def get_progress(self):
        job = self.get_rq_job()
        return job.meta.get("progress", 0) if job is not None else 100

    @classmethod
    def launch_userless_task(cls, name, description=None, *args, **kwargs):
        """
        Mocks the creation and 'launching' of a task without an associated user.
        In a real application, this would involve queuing a job.
        """
        # In a real application, you might enqueue a job here,
        # and the job ID would be used as the task ID.
        # For this mock, we'll just create a new Task instance directly.
        rq_job = current_app.task_queue.enqueue(f"app.{name}", *args, **kwargs)

        # Create a new Task instance with no user_id
        new_task = cls(
            id=rq_job.get_id(),
            name=name,
            description=description,
            user_id=None,  # Explicitly set user_id to None
            complete=False,
        )
        # In a real app, you would add this task to the session and commit:
        db.session.add(new_task)
        return new_task


class Notification(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    name: so.Mapped[str] = so.mapped_column(sa.String(128), index=True)
    user_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey(User.id), index=True)
    timestamp: so.Mapped[float] = so.mapped_column(index=True, default=time)
    payload_json: so.Mapped[str] = so.mapped_column(sa.Text)

    user: so.Mapped[User] = so.relationship(back_populates="notifications")

    def get_data(self):
        return json.loads(str(self.payload_json))


class Theme(db.Model):
    id = so.mapped_column(sa.Integer, primary_key=True)
    name = so.mapped_column(sa.String(255), nullable=False)
    css = so.mapped_column(sa.Text, nullable=False)
    user_id = so.mapped_column(sa.Integer, sa.ForeignKey("user.id"))
    user = so.relationship("User", back_populates="themes")
    blogs = so.relationship("Blog", back_populates="theme")

    def __repr__(self):
        return f"<Theme {self.name}>"


@sa.event.listens_for(Theme.blogs, "append")
def receive_append(theme, blog, initiator):
    # When a blog is added to a theme, set its CSS to match the theme's CSS.
    blog.css = theme.css


class Webmention(db.Model):
    id: so.Mapped[int] = so.mapped_column(sa.Integer, primary_key=True)
    source: so.Mapped[str] = so.mapped_column(
        sa.String, nullable=False
    )  # the linking URL
    target: so.Mapped[str] = so.mapped_column(
        sa.String, nullable=False
    )  # your post URL

    user_id: so.Mapped[Optional[int]] = so.mapped_column(
        sa.ForeignKey("user.id"), nullable=True
    )  # optional: if the webmention is associated with a user
    user: so.Mapped[Optional[User]] = so.relationship(
        "User", back_populates="webmentions"
    )
    # optional: if you want to store the original content of the webmention
    content: so.Mapped[Optional[str]] = so.mapped_column(sa.Text, nullable=True)

    blog_id: so.Mapped[Optional[int]] = so.mapped_column(
        sa.ForeignKey("blog.id"), nullable=True
    )  # optional: if the webmention is associated with a blog
    blog: so.Mapped[Optional[Blog]] = so.relationship(
        "Blog", back_populates="webmentions"
    )
    # optional: if you want to store the verification status
    verified: so.Mapped[bool] = so.mapped_column(sa.Boolean, default=False)
    created_at: so.Mapped[datetime] = so.mapped_column(
        sa.DateTime, server_default=sa.func.now()
    )
    type: so.Mapped[str] = so.mapped_column(
        sa.String
    )  # optional: "mention", "reply", "like", "repost", etc.


class Chirp(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    user_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey("user.id"))
    content: so.Mapped[str] = so.mapped_column(sa.Text, nullable=False)
    created_at: so.Mapped[datetime] = so.mapped_column(
        sa.DateTime, server_default=sa.func.now()
    )
    user: so.Mapped[User] = so.relationship("User", back_populates="chirps")
