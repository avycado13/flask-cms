from flask import render_template, redirect, url_for, request, flash
from app.extensions import db
from app.models import Post, Blog
from app.main import bp
from app.main.forms import PostForm, PostActionForm, BlogForm, BlogActionForm
from flask_security import auth_required
import bleach

@bp.route("/")
def index():
    # blogs = Blog.query.all()
    return "Hello, World!"


@bp.route("/blog/<int:blog_id>")
def blog_view(blog_id:int):
    blog = Blog.query.get_or_404(blog_id)
    # Use the relationship defined in the Blog model
    posts = blog.posts
    return render_template("view_blog.html", blog=blog, posts=posts)


@bp.route("/post/<int:post_id>")
def view_post(post_id:int):
    page = Post.query.get_or_404(post_id)
    return render_template("page.html", page=page)

@bp.route("/blog_admin/<int:blog_id>", methods=["GET", "POST"])
@auth_required()
def blog_admin(blog_id:int):
    create_form = PostForm()
    actions_form = PostActionForm()

    if create_form.validate_on_submit():
        content = bleach.clean(create_form.content.data)
        title = bleach.clean(create_form.title.data)
        new_page = Post(title=title, content=content,blog_id=blog_id)
        db.session.add(new_page)
        db.session.commit()
        flash("Page created successfully!", "success")
        return redirect(url_for("main.index"))
    if actions_form.validate_on_submit():
        if actions_form.delete.data:
            page = Post.query.get_or_404(actions_form.page_id.data)
            db.session.delete(page)
            db.session.commit()
            flash("Page deleted successfully!", "success")
            return redirect(url_for("main.index"))
        if actions_form.edit.data:
            page = Post.query.get_or_404(actions_form.page_id.data)
            return redirect(url_for("main.edit_page", page_id=page.id))
        if actions_form.view.data:
            page = Post.query.get_or_404(actions_form.page_id.data)
            return redirect(url_for("main.view_post", page_id=page.id))
    pages = Post.query.filter_by(blog_id=blog_id).all()
    return render_template(
        "blog_admin.html", create_form=create_form, actions_form=actions_form, pages=pages
    )

@bp.route("/edit_page/<int:post_id>", methods=["GET", "POST"])
@auth_required()
def edit_page(post_id:int):
    page = Post.query.get_or_404(post_id)
    form = PostForm(obj=page)
    if form.validate_on_submit():
        page.title = form.title.data
        page.content = form.content.data
        db.session.commit()
        flash("Page updated successfully!", "success")
        return redirect(url_for("main.index"))
    return render_template("edit_page.html", form=form, page=page)


@bp.route("/admin", methods=["GET", "POST"])
def admin():
    create_form = BlogForm()
    actions_form = BlogActionForm()
    if create_form.validate_on_submit():
        new_blog = Blog(title=create_form.title.data, description=create_form.description.data)
        db.session.add(new_blog)
        db.session.commit()
        flash("Blog created successfully!", "success")
        return redirect(url_for("main.index"))
    if actions_form.validate_on_submit():
        if actions_form.delete.data:
            blog = Blog.query.get_or_404(actions_form.blog_id.data)
            db.session.delete(blog)
            db.session.commit()
            flash("Blog deleted successfully!", "success")
            return redirect(url_for("main.index"))
        if actions_form.edit.data:
            blog = Blog.query.get_or_404(actions_form.blog_id.data)
            return redirect(url_for("main.edit_blog", blog_id=blog.id))
        if actions_form.view.data:
            blog = Blog.query.get_or_404(actions_form.blog_id.data)
            return redirect(url_for("main.blog_view", blog_id=blog.id))
    blogs = Blog.query.all()
    return render_template(
        "admin.html", create_form=create_form, actions_form=actions_form, blogs=blogs
    )