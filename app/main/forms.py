from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField, HiddenField
from wtforms.validators import DataRequired


class PostForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired()])
    content = TextAreaField("Content", validators=[DataRequired()])
    submit = SubmitField("Save Page")


class PostActionForm(FlaskForm):
    post_id = HiddenField("Post ID", validators=[DataRequired()])
    view = SubmitField("View")
    edit = SubmitField("Edit")
    delete = SubmitField("Delete")


class BlogForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired()])
    description = TextAreaField("Description")
    submit = SubmitField("Create Blog")


class BlogActionForm(FlaskForm):
    blog_id = HiddenField("Blog ID", validators=[DataRequired()])
    view = SubmitField("View")
    edit = SubmitField("Edit")
    delete = SubmitField("Delete")
