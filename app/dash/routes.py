from flask import (
    render_template,
    redirect,
    url_for,
    request,
    flash,
    abort,
    g,
    current_app,
)
from app.extensions import db
from app.models import Post, Blog, Page
from app.dash import bp
from app.dash.forms import (
    PostForm,
    PostActionForm,
    BlogForm,
    BlogActionForm,
    PageForm,
    PageActionForm,
)
from flask_security import auth_required, current_user
from flask_babel import _, get_locale
import bleach
import os
from datetime import datetime, timezone
import sqlalchemy as sa
import markdown
import frontmatter


@bp.route("/blog/<int:blog_id>", methods=["GET", "POST"])
@bp.route("/admin", subdomain="<slug>")
@auth_required()
def blog_admin(blog_id=None, slug=None):
    if slug:
        blog = Blog.query.filter_by(slug=slug).first_or_404()
    else:
        blog = Blog.query.get_or_404(blog_id)
    post_create_form = PostForm()
    page_create_form = PageForm()

    edit_form = BlogForm(obj=blog)
    post_actions_form = PostActionForm()
    page_action_form = PageActionForm()
    blog_action_form = BlogActionForm()

    if post_create_form.validate_on_submit():
        content = bleach.clean(
            post_create_form.content.data,
            tags=[
                "p",
                "strong",
                "em",
                "u",
                "h2",
                "h3",
                "h4",
                "h5",
                "h6",
                "a",
                "img",
                "ul",
                "ol",
                "li",
            ],
        )
        title = bleach.clean(post_create_form.title.data)
        new_page = Post(
            title=title,
            content=content,
            blog_id=blog_id,
            user_id=current_user.id,
            published=post_create_form.published.data,
            publish_in_newsletter=post_create_form.publish_in_newsletter.data,
        )
        db.session.add(new_page)
        db.session.commit()
        flash(_("Post created successfully!"), "success")
        return redirect(url_for("main.index"))
    if post_actions_form.validate_on_submit():
        if post_actions_form.delete.data:
            page = Post.query.get_or_404(post_actions_form.post_id.data)
            db.session.delete(page)
            db.session.commit()
            flash(_("Page deleted successfully!"), "success")
            return redirect(url_for("main.index"))
        if post_actions_form.edit.data:
            page = Post.query.get_or_404(post_actions_form.post_id.data)
            return redirect(url_for("main.edit_post", post_id=page.id))
        if post_actions_form.view.data:
            page = Post.query.get_or_404(post_actions_form.post_id.data)
            return redirect(url_for("main.view_post", post_id=page.id))
    if page_create_form.validate_on_submit():
        content = bleach.clean(
            page_create_form.content.data,
            tags=[
                "p",
                "strong",
                "em",
                "u",
                "h2",
                "h3",
                "h4",
                "h5",
                "h6",
                "a",
                "img",
                "ul",
                "ol",
                "li",
            ],
        )
        title = bleach.clean(post_create_form.title.data)
        new_page = Page(
            title=title,
            content=content,
            blog_id=blog_id,
            user=current_user,
            published=post_create_form.published.data,
            publish_in_newsletter=post_create_form.publish_in_newsletter.data,
        )
        db.session.add(new_page)
        db.session.commit()
        flash(_("Page created successfully!"), "success")
        return redirect(url_for("main.index"))
    if page_action_form.validate_on_submit():
        if page_action_form.delete.data:
            page = Page.query.get_or_404(post_actions_form.post_id.data)
            db.session.delete(page)
            db.session.commit()
            flash(_("Page deleted successfully!"), "success")
            return redirect(url_for("main.index"))
        if page_action_form.edit.data:
            page = Page.query.get_or_404(post_actions_form.post_id.data)
            return redirect(url_for("main.edit_page", post_id=page.id))
        if page_action_form.view.data:
            page = Page.query.get_or_404(post_actions_form.post_id.data)
            return redirect(url_for("main.view_page", post_id=page.id))

    page = request.args.get("page", 1, type=int)
    query = (
        sa.select(Post).where(Post.blog_id == blog_id).order_by(Post.created_at.desc())
    )
    posts = db.paginate(
        query, page=page, per_page=current_app.config["POSTS_PER_PAGE"], error_out=False
    )
    next_url = (
        url_for("blog_admin", blog_id=blog_id, page=posts.next_num)
        if posts.has_next
        else None
    )
    prev_url = (
        url_for("blog_admin", blog_id=blog_id, page=posts.prev_num)
        if posts.has_prev
        else None
    )
    if current_user == Blog.query.get_or_404(blog_id).author:
        return render_template(
            "dash/blog/index.html",
            edit_form=edit_form,
            post_create_form=post_create_form,
            post_actions_form=post_actions_form,
            page_create_form=page_create_form,
            page_action_form=page_action_form,
            blog_action_form=blog_action_form,
            blog=blog,
            posts=posts,
            current_user=current_user,
            next_url=next_url,
            prev_url=prev_url,
        )
    else:
        flash(_("You don't have access to edit this blog"), "danger")
        return redirect(url_for("main.index"))


@bp.route("/edit_post/<int:post_id>", methods=["GET", "POST"])
@auth_required()
def edit_post(post_id: int):
    page = Post.query.get_or_404(post_id)
    edit_form = PostForm(obj=page)
    if edit_form.validate_on_submit():
        page.title = edit_form.title.data
        page.content = edit_form.content.data
        db.session.commit()
        flash(_("Post updated successfully!"), "success")
        return redirect(url_for("main.index"))
    return render_template("edit_post.html", edit_form=edit_form, page=page)


@bp.route("/", methods=["GET", "POST"])
@auth_required()
def dash_index():
    create_form = BlogForm()
    actions_form = BlogActionForm()
    if create_form.validate_on_submit():
        new_blog = Blog(
            title=create_form.title.data,
            description=create_form.description.data,
            author=current_user,
            newsletter=create_form.newsletter.data,
        )
        db.session.add(new_blog)
        db.session.commit()
        flash(_("Blog created successfully!"), "success")
        return redirect(url_for("main.index"))
    if actions_form.validate_on_submit():
        if actions_form.delete.data:
            blog = Blog.query.get_or_404(actions_form.blog_id.data)
            db.session.delete(blog)
            db.session.commit()
            flash(_("Blog deleted successfully!"), "success")
            return redirect(url_for("main.index"))
        if actions_form.edit.data:
            blog = Blog.query.get_or_404(actions_form.blog_id.data)
            return redirect(url_for("main.edit_blog", blog_id=blog.id))
        if actions_form.view.data:
            blog = Blog.query.get_or_404(actions_form.blog_id.data)
            return redirect(url_for("main.view_blog", blog_id=blog.id))
    blogs = Blog.query.filter_by(author=current_user).all()
    return render_template(
        "dash/index.html",
        create_form=create_form,
        actions_form=actions_form,
        blogs=blogs,
        current_user=current_user,
    )


@bp.route("/edit_blog/<int:blog_id>", methods=["GET", "POST"])
def edit_blog(blog_id: int):
    blog = Blog.query.get_or_404(blog_id)
    edit_form = BlogForm(obj=blog)
    if edit_form.validate_on_submit():
        blog.title = edit_form.title.data
        blog.description = edit_form.description.data
        db.session.commit()
        flash(_("Blog updated successfully!"), "success")
        return redirect(url_for("main.index"))
    return render_template("edit_blog.html", edit_form=edit_form, blog=blog)


@bp.route("/account")
@auth_required()
def account():
    return render_template("dash/account.html")


@bp.route("/<blog_id>/uploads", methods=["GET", "POST"])
@auth_required()
def upload(blog_id=None, slug=None):
    if slug:
        blog = Blog.query.filter_by(slug=slug).first_or_404()
    else:
        blog = Blog.query.get_or_404(blog_id)
    if blog.author == current_user:
        if request.method == "POST":
            files = request.files
            for file in files:
                file_content = file.stream.read()
                if frontmatter.checks(file_content):
                    matter = frontmatter.loads(file_content)
                    try:
                        html = markdown.markdown(matter.content)
                    except Exception as e:
                        current_app.logger.info(f"Error converting markdown file: {e}")
                        flash(_("Failed to parse markdown"), "error")
                        return redirect(url_for("blog_admin"))
                    new_post = Post(
                        title=matter.metadata.get("title"),
                        content=html,
                        blog_id=blog.id,
                        user=current_user,
                        published=not matter.metadata.get("draft"),
                    )
                    db.session.add(new_post)
                    db.session.commit()
                else:
                    flash(_("No front matter"), "error")
                    return redirect(url_for("main.blog_admin"))
        else:
            return redirect(url_for("main.index"))

    else:
        abort(403)
    return redirect(url_for("main.blog_admin"))
