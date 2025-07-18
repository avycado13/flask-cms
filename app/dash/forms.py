from wtforms.validators import ValidationError
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField, HiddenField, BooleanField
from wtforms.validators import DataRequired
from wtforms.widgets import TextArea
from flask_babel import _, lazy_gettext as _l
from flask import request


class TinyMCEWidget(TextArea):
    """A custom WTForms widget that integrates with TinyMCE and Bootstrap."""

    def __call__(self, field, **kwargs):
        """Render the textarea with Bootstrap and TinyMCE support."""
        classes = kwargs.get("class", "")
        kwargs["class"] = (
            f"{classes} form-control tinymce".strip()
        )  # Ensure Bootstrap styling is applied
        return super().__call__(field, **kwargs)


# Create a TinyMCE-enhanced WTForms field
class TinyMCEField(TextAreaField):
    widget = TinyMCEWidget()


class BannedSlugValidator:
    def __init__(self, banned_slugs=None):
        if banned_slugs is None:
            banned_slugs = ["login", "www", "register", "about"]
        self.banned_slugs = banned_slugs

    def __call__(self, form, field):
        if field.data in self.banned_slugs:
            raise ValidationError(_("This slug is not allowed."))


class PostForm(FlaskForm):
    title = StringField(_l("Title"), validators=[DataRequired()])
    content = TinyMCEField(_l("Content"), validators=[DataRequired()])
    publish_in_newsletter = BooleanField(_l("Publish to Newsletter"))
    published = BooleanField(_l("Published"))
    submit = SubmitField(_l("Save Post"))
    save_as_draft = SubmitField(_l("Save as Draft"))


class PageForm(FlaskForm):
    title = StringField(_l("Title"), validators=[DataRequired()])
    content = TinyMCEField(_l("Content"), validators=[DataRequired()])
    published = BooleanField(_l("Published"))
    submit = SubmitField(_l("Save Page"))


class PageActionForm(FlaskForm):
    page_id = HiddenField(_l("Page ID"), validators=[DataRequired()])
    view = SubmitField(_l("View"))
    edit = SubmitField(_l("Edit"))
    delete = SubmitField(_l("Delete"))


class PostActionForm(FlaskForm):
    post_id = HiddenField(_l("Post ID"), validators=[DataRequired()])
    view = SubmitField(_l("View"))
    edit = SubmitField(_l("Edit"))
    delete = SubmitField(_l("Delete"))


class BlogForm(FlaskForm):
    title = StringField(_l("Title"), validators=[DataRequired()])
    slug = StringField(
        _l("URL Slug"), validators=[DataRequired(), BannedSlugValidator()]
    )

    description = TextAreaField(_l("Description"))
    newsletter = BooleanField(_l("Newsletter"))
    submit = SubmitField(_l("Create Blog"))


class BlogActionForm(FlaskForm):
    blog_id = HiddenField(_l("Blog ID"), validators=[DataRequired()])
    view = SubmitField(_l("View"))
    edit = SubmitField(_l("Edit"))
    delete = SubmitField(_l("Delete"))


class SearchForm(FlaskForm):
    q = StringField(_l("Search"), validators=[DataRequired()])

    def __init__(self, *args, **kwargs):
        if "formdata" not in kwargs:
            kwargs["formdata"] = request.args
        if "meta" not in kwargs:
            kwargs["meta"] = {"csrf": False}
        super(SearchForm, self).__init__(*args, **kwargs)


class CommentForm(FlaskForm):
    content = TextAreaField(_l("Comment"), validators=[DataRequired()])
    submit = SubmitField(_l("Submit Comment"))


class EmptyForm(FlaskForm):
    submit = SubmitField("Submit")
