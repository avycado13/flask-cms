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
from app.models import Post, Blog, User, Comment
from app.main import bp
from app.main.forms import (
    PostForm,
    PostActionForm,
    BlogForm,
    BlogActionForm,
    SearchForm,
    CommentForm,
    EmptyForm,
)
from flask_security import auth_required, current_user
from flask_babel import _, get_locale
import bleach
import os
from datetime import datetime, timezone
import sqlalchemy as sa


@bp.before_app_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.now(timezone.utc)
        db.session.commit()
        g.search_form = SearchForm()
    g.locale = str(get_locale())


@bp.route("/")
def index():
    if current_user.is_authenticated:
        blogs = Blog.query.all()
        page = request.args.get("page", 1, type=int)
        query = (
            sa.select(Post)
            .join(Post.blog)
            .filter(Blog.id.in_([blog.id for blog in blogs]))
            .order_by(Post.created_at.desc())
        )
        posts = db.paginate(
            query,
            page=page,
            per_page=current_app.config["POSTS_PER_PAGE"],
            error_out=False,
        )
        next_url = url_for("index", page=posts.next_num) if posts.has_next else None
        prev_url = url_for("index", page=posts.prev_num) if posts.has_prev else None
        return render_template(
            "index.html",
            blogs=blogs,
            current_user=current_user,
            posts=posts,
            next_url=next_url,
            prev_url=prev_url,
        )
    else:
        flash(_("To get a personalized feed, create an account or login!"), "info")
        return redirect(url_for("main.explore"))


@bp.route("/explore")
def explore():
    blogs = Blog.query.all()
    return render_template("explore.html", blogs=blogs, current_user=current_user)


@bp.route("/blog/<int:blog_id>")
def view_blog(blog_id: int):
    form = EmptyForm()
    blog = Blog.query.get_or_404(blog_id)
    # Use the relationship defined in the Blog model
    page = request.args.get("page", 1, type=int)
    query = (
        sa.select(Post).where(Post.blog_id == blog_id).order_by(Post.created_at.desc())
    )
    posts = db.paginate(
        query, page=page, per_page=current_app.config["POSTS_PER_PAGE"], error_out=False
    )
    next_url = (
        url_for("view_blog", blog_id=blog_id, page=posts.next_num)
        if posts.has_next
        else None
    )
    prev_url = (
        url_for("view_blog", blog_id=blog_id, page=posts.prev_num)
        if posts.has_prev
        else None
    )
    return render_template(
        "view_blog.html",
        blog=blog,
        posts=posts,
        current_user=current_user,
        next_url=next_url,
        prev_url=prev_url,
        form=form,
    )


@bp.route("/blog/<int:blog_id>/rss.xml")
def blog_rss(blog_id: int):
    blog = Blog.query.get_or_404(blog_id)
    posts = Post.query.filter_by(blog_id=blog_id).order_by(Post.created_at.desc()).all()
    return render_template(
        "rss.xml", blog=blog, posts=posts, build_date=datetime.now(timezone.utc)
    )


@bp.route("/post/<int:post_id>", methods=["GET", "POST"])
def view_post(post_id: int):
    post = Post.query.get_or_404(post_id)
    comment_form = CommentForm()
    comments = post.comments
    blog = post.blog
    if comment_form.validate_on_submit():
        new_comment = Comment(
            user_id=current_user.id,
            post_id=post_id,
            content=comment_form.content.data,
        )
        db.session.add(new_comment)
        db.session.commit()
        flash(_("Comment created successfully!"), "success")
        return redirect(url_for("main.view_post", post_id=post_id))
    return render_template(
        "view_post.html",
        post=post,
        blog=blog,
        comment_form=comment_form,
        comments=comments,
        current_user=current_user,
    )


@bp.route("/blog_admin/<int:blog_id>", methods=["GET", "POST"])
@auth_required()
def blog_admin(blog_id: int):
    blog = Blog.query.get_or_404(blog_id)
    create_form = PostForm()
    edit_form = BlogForm(obj=blog)
    actions_form = PostActionForm()

    if create_form.validate_on_submit():
        content = bleach.clean(
            create_form.content.data,
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
        title = bleach.clean(create_form.title.data)
        new_page = Post(
            title=title,
            content=content,
            blog_id=blog_id,
            user=current_user,
            published=create_form.published.data,
            publish_in_newsletter=create_form.publish_in_newsletter.data,
        )
        db.session.add(new_page)
        db.session.commit()
        flash(_("Page created successfully!"), "success")
        return redirect(url_for("main.index"))
    if actions_form.validate_on_submit():
        if actions_form.delete.data:
            post = Post.query.get_or_404(actions_form.post_id.data)
            db.session.delete(post)
            db.session.commit()
            flash("Page deleted successfully!", "success")
            return redirect(url_for("main.index"))
        if actions_form.edit.data:
            post = Post.query.get_or_404(actions_form.post_id.data)
            return redirect(url_for("main.edit_post", post_id=post.id))
        if actions_form.view.data:
            post = Post.query.get_or_404(actions_form.post_id.data)
            return redirect(url_for("main.view_post", post_id=post.id))
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
    if current_user == Blog.query.get_or_404(blog_id).user:
        return render_template(
            "blog_admin.html",
            create_form=create_form,
            edit_form=edit_form,
            actions_form=actions_form,
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


@bp.route("/admin", methods=["GET", "POST"])
@auth_required()
def admin():
    create_form = BlogForm()
    actions_form = BlogActionForm()
    if create_form.validate_on_submit():
        new_blog = Blog(
            title=create_form.title.data,
            description=create_form.description.data,
            user=current_user,
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
    blogs = Blog.query.filter_by(user=current_user).all()
    return render_template(
        "admin.html",
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


@bp.route("/user/<username>")
def view_user(username):
    form = EmptyForm()
    user = User.query.filter_by(username=username).first_or_404()
    return render_template(
        "view_user.html",
        user=user,
        posts=user.posts,
        blogs=user.blogs,
        comments=user.comments,
        current_user=current_user,
        form=form,
    )


@bp.route("/search")
def search():
    if not g.search_form.validate():
        return redirect(url_for("main.index"))
    page = request.args.get("page", 1, type=int)
    posts, total = Post.search(
        g.search_form.q.data, page, current_app.config["POSTS_PER_PAGE"]
    )
    next_url = (
        url_for("main.search", q=g.search_form.q.data, page=page + 1)
        if total > page * current_app.config["POSTS_PER_PAGE"]
        else None
    )
    prev_url = (
        url_for("main.search", q=g.search_form.q.data, page=page - 1)
        if page > 1
        else None
    )
    return render_template(
        "search.html",
        title=_("Search"),
        posts=posts,
        next_url=next_url,
        prev_url=prev_url,
    )
