from app.models import Blog
from flask import render_template, current_app
from app.email import send_email
from datetime import date
import sys

today = date.today()


def send_newsletter(blog_id):
    try:
        blog = Blog.query.get(blog_id)
        if blog is None:
            raise ValueError(f"Blog with id {blog_id} does not exist")
        posts = [post for post in blog.posts if post.publish_in_newsletter]
        html = render_template("email/newsletter.html", blog=blog, posts=posts)
        send_email(
            f"Newsletter: {blog.title} {today}",
            (blog.title, current_app.config["MAIL_DEFAULT_SENDER"]),
            [recipient.email for recipient in blog.recipients],
            "For best viewing experience, please look at html",
            html,
        )
    except Exception:
        current_app.logger.exception("Unhandled exception", exc_info=sys.exc_info())
