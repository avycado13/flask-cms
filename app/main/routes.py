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
    PostForm,
    PostActionForm,
    BlogForm,
    BlogActionForm,
    SearchForm,
    CommentForm,
    EmptyForm,
    PageForm,
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


@bp.route("/<blog_id>/uploads", methods=["GET", "POST"])
@bp.route("/upload", subdomain="<slug>")
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
                        flash(_("No front matter"), "error")
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


@bp.route("/blog/<int:blog_id>/rss.xml")
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


@bp.route("/post/<int:post_id>", methods=["GET", "POST"])
@bp.route("/post/<int:post_id>", methods=["GET", "POST"], subdomain="<slug>")
def view_post(post_id: int, slug=None):
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


@bp.route("/blog_admin/<int:blog_id>", methods=["GET", "POST"])
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
    page_action_form = PageForm()

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
            user=current_user,
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
            "blog_admin.html",
            post_create_form=post_create_form,
            edit_form=edit_form,
            post_actions_form=post_actions_form,
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
