from flask import render_template, redirect, url_for, request, flash, abort
from app.extensions import db
from app.models import Post, Blog
from app.main import bp
from app.main.forms import PostForm, PostActionForm, BlogForm, BlogActionForm
from flask_security import auth_required, current_user
import bleach
import os


@bp.route("/")
def index():
    blogs = Blog.query.all()
    return render_template("index.html", blogs=blogs, current_user=current_user)

@bp.route("/blog/<int:blog_id>")
def view_blog(blog_id: int):
    blog = Blog.query.get_or_404(blog_id)
    # Use the relationship defined in the Blog model
    posts = blog.posts
    return render_template(
        "view_blog.html", blog=blog, posts=posts, current_user=current_user
    )


@bp.route("/post/<int:post_id>")
def view_post(post_id: int):
    post = Post.query.get_or_404(post_id)
    blog = post.blog
    return render_template("view_post.html", post=post, blog=blog,current_user=current_user)


@bp.route("/blog_admin/<int:blog_id>", methods=["GET", "POST"])
@auth_required()
def blog_admin(blog_id: int):
    create_form = PostForm()
    actions_form = PostActionForm()

    if create_form.validate_on_submit():
        content = bleach.clean(create_form.content.data, tags=["p", "strong", "em", "u", "h1", "h2", "h3", "h4", "h5", "h6", "a", "img", "ul", "ol", "li"])
        title = bleach.clean(create_form.title.data)
        new_page = Post(title=title, content=content, blog_id=blog_id)
        db.session.add(new_page)
        db.session.commit()
        flash("Page created successfully!", "success")
        return redirect(url_for("main.index"))
    if actions_form.validate_on_submit():
        if actions_form.delete.data:
            page = Post.query.get_or_404(actions_form.post_id.data)
            db.session.delete(page)
            db.session.commit()
            flash("Page deleted successfully!", "success")
            return redirect(url_for("main.index"))
        if actions_form.edit.data:
            page = Post.query.get_or_404(actions_form.page_id.data)
            return redirect(url_for("main.edit_post", page_id=page.id))
        if actions_form.view.data:
            page = Post.query.get_or_404(actions_form.page_id.data)
            return redirect(url_for("main.view_post", page_id=page.id))
    blog = Blog.query.get_or_404(blog_id)
    posts = blog.posts
    if current_user == Blog.query.get_or_404(blog_id).user:
        return render_template(
            "blog_admin.html",
            create_form=create_form,
            actions_form=actions_form,
            blog=blog,
            posts=posts,
            current_user=current_user,
        )
    else:
        flash("You don't have access to edit this blog", "danger")
        return redirect(url_for("main.index"))


@bp.route("/edit_post/<int:post_id>", methods=["GET", "POST"])
@auth_required()
def edit_post(post_id: int):
    page = Post.query.get_or_404(post_id)
    form = PostForm(obj=page)
    if form.validate_on_submit():
        page.title = form.title.data
        page.content = form.content.data
        db.session.commit()
        flash("Post updated successfully!", "success")
        return redirect(url_for("main.index"))
    return render_template("edit_post.html", form=form, page=page)


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
        )
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
            return redirect(url_for("main.view_blog", blog_id=blog.id))
    blogs = Blog.query.filter_by(user=current_user).all()
    return render_template(
        "admin.html",
        create_form=create_form,
        actions_form=actions_form,
        blogs=blogs,
        current_user=current_user,
    )
