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
from app.models import Post, Blog, User, Comment, Page
from app.main import bp
from app.main.forms import (
    EmptyForm,
    PostForm,
    PostActionForm,
    BlogForm,
    BlogActionForm,
    SearchForm,
    CommentForm,
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
@bp.route("/blog/<slug>")
@bp.route("/", subdomain="<slug>")
def view_blog(blog_id=None, slug=None):
    if slug:
        blog = Blog.query.filter_by(slug=slug).first_or_404()
    else:
        blog = Blog.query.get_or_404(blog_id)
    form = EmptyForm()
    # Use the relationship defined in the Blog model
    page = request.args.get("page", 1, type=int)
    query = (
        sa.select(Post).where(Post.blog_id == blog_id).order_by(Post.created_at.desc())
    )
    posts = db.paginate(
        query, page=page, per_page=current_app.config["POSTS_PER_PAGE"], error_out=False
    )
    next_url = (
        url_for("view_blog", blog_id=blog_id, page=posts.next_num, slug=slug)
        if posts.has_next
        else None
    )
    prev_url = (
        url_for("view_blog", blog_id=blog_id, page=posts.prev_num, slug=slug)
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
@bp.route("/blog/<slug>/rss.xml")
@bp.route("/rss.xml", subdomain="<slug>")
def blog_rss(blog_id=None, slug=None):
    if slug:
        blog = Blog.query.filter_by(slug=slug).first_or_404()
    else:
        blog = Blog.query.get_or_404(blog_id)

    posts = Post.query.filter_by(blog_id=blog.id).order_by(Post.created_at.desc()).all()

    return render_template(
        "rss.xml", blog=blog, posts=posts, build_date=datetime.now(timezone.utc)
    )


@bp.route("/post/<slug>/<int:post_id>", methods=["GET", "POST"])
@bp.route("/post/<int:post_id>", methods=["GET", "POST"], subdomain="<slug>")
def view_post(post_id: int, slug=None):
    if slug:
        post = Post.query.filter_by(slug=slug, id=post_id).first_or_404()
        blog = Blog.query.filter_by(slug=slug).first_or_404()
        if blog.id != post.blog_id:
            abort(404, description=_("Post not found in this blog."))
    else:
        post = Post.query.get_or_404(post_id)
    comment_form = CommentForm()
    blog = post.blog
    comments = post.comments
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


@bp.route("/page/<int:page_id>", methods=["GET", "POST"])
@bp.route("/page/<int:page_id>", methods=["GET", "POST"], subdomain="<slug>")
def view_page(page_id: int, slug=None):
    page = Page.query.get_or_404(page_id)
    blog = page.blog
    return render_template(
        "view_page.html",
        post=page,
        blog=blog,
        current_user=current_user,
    )



@bp.route("/user/<username>")
def view_user(username):
    def get_all_posts_and_comments(user_id, sort_by="created_at", descending=False):
        posts_query = db.session.query(Post).filter_by(user_id=user_id)
        comments_query = db.session.query(Comment).filter_by(user_id=user_id)

        posts = posts_query.all()
        comments = comments_query.all()

        combined = posts + comments
        if not all(hasattr(item, sort_by) for item in combined):
            raise AttributeError("Invalid sort attribute provided.")

        combined.sort(key=lambda item: getattr(item, sort_by), reverse=descending)
        return combined

    form = EmptyForm()
    user = User.query.filter_by(username=username).first_or_404()
    return render_template(
        "view_user.html",
        user=user,
        posts=user.posts,
        blogs=user.blogs,
        comments=user.comments,
        all_activity=get_all_posts_and_comments(user.id),
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
