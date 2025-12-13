import re

from flask_wtf import FlaskForm, RecaptchaField
from wtforms import StringField, SubmitField, PasswordField
from wtforms.fields import EmailField
from wtforms.validators import DataRequired, Length, Regexp, EqualTo, Email, ValidationError


# Form for user registration
class RegisterForm(FlaskForm):
    # Date of Birth field with validation for DD/MM/YYYY format
    # dob_regexp = Regexp(r'^(0[1-9]|[12][0-9]|3[01])/(0[1-9]|1[012])/(19|20)\d\d$',
    #                     message="Invalid date format, must be DD/MM/YYYY")
    # dob = StringField('Date of Birth', validators=[DataRequired(), dob_regexp])

    # Email field with validation for proper email format
    email = EmailField('Email', validators=[DataRequired(), Email(
        message="Invalid email address")])

    username = StringField('username', validators=[DataRequired(), Length(min=3, max=80)])

    # Firstname and Lastname: Exclude specified characters
    # name_regexp = Regexp(r'^[^*?!\'^+%&/()=}]{3,}$',
    #                      message="Invalid characters in name")
    # first_name = StringField('Firstname',
    #                          validators=[DataRequired(), name_regexp])
    # last_name = StringField('Lastname', validators=[DataRequired(), name_regexp])

    # Password: Specific length and character requirements
    # password_regexp = Regexp(r'^(?=.*\d)(?=.*[a-z])(?=.*[A-Z])(?=.*\W).{6,12}$',
    #                          message="Password must be 6-12 characters long, include digits, lowercase, uppercase, and special characters")
    password = PasswordField('Password',
                             validators=[DataRequired(), Length(min=6,max=20)])

    # Confirm Password: Must match Password
    confirm_password = PasswordField('Confirm Password',
                                     validators=[DataRequired(),
                                                 EqualTo('password',
                                                         message="Passwords must match")])

    submit = SubmitField('Register')

def optional_email(form, field):
    data = field.data
    if data and '@' in data:  # 如果包含 @，就当邮箱验证
        if not re.match(r"[^@]+@[^@]+\.[^@]+", data):
            raise ValidationError('邮箱格式不正确')

# Form for user login
class LoginForm(FlaskForm):

    login = StringField('Email or username', validators=[DataRequired(), Length(min=3, max=80), optional_email])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')


from flask_wtf import FlaskForm
from wtforms import PasswordField, SubmitField, BooleanField
from wtforms.validators import DataRequired, EqualTo


# Form for changing the user's password
class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm New Password', validators=[DataRequired(), EqualTo('new_password')])
    show_password = BooleanField('Show Password')
    submit = SubmitField('Change Password')

# users/forms.py —— 新增修改邮箱表单
class UpdateEmailForm(FlaskForm):
    email = StringField('New email address', validators=[
        DataRequired(message="Please enter a new email address"),
        Email(message="Please enter a correct email address"),
    ])
    confirm_email = StringField('Confirm address', validators=[
        DataRequired(message="Please enter email address again"),
        EqualTo('email', message="Please enter the same email address")
    ])
    submit = SubmitField('update email')

class ProfileForm(FlaskForm):
    bio = StringField('个人简介', validators=[Length(max=500)])
    github = StringField('GitHub')
    twitter = StringField('Twitter')
    submit = SubmitField('更新资料')