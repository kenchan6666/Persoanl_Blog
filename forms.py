from flask_wtf import FlaskForm
from wtforms import TextAreaField, SubmitField
from wtforms.validators import DataRequired, Length


class CommentForm(FlaskForm):
    content = TextAreaField('评论内容', validators=[DataRequired(), Length(max=500)])
    submit = SubmitField('发表评论')