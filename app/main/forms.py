from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField, HiddenField
from wtforms.validators import DataRequired
from wtforms.widgets import TextArea

class TinyMCEWidget(TextArea):
    """A custom WTForms widget that integrates with TinyMCE and Bootstrap."""
    
    def __call__(self, field, **kwargs):
        """Render the textarea with Bootstrap and TinyMCE support."""
        classes = kwargs.get("class", "")
        kwargs["class"] = f"{classes} form-control tinymce".strip()  # Ensure Bootstrap styling is applied
        return super().__call__(field, **kwargs)

# Create a TinyMCE-enhanced WTForms field
class TinyMCEField(TextAreaField):
    widget = TinyMCEWidget()


class PostForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired()])
    content = TinyMCEField("Content", validators=[DataRequired()])
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
