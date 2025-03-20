from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, EmailField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError
from models import User

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=64)])
    email = EmailField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')
    
    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Username already exists. Please choose a different one.')
    
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Email already registered. Please use a different one.')

class ProfileForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=64)])
    email = EmailField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    current_password = PasswordField('Current Password')
    new_password = PasswordField('New Password', validators=[Length(min=0, max=64)])
    confirm_password = PasswordField('Confirm New Password', validators=[EqualTo('new_password')])
    submit = SubmitField('Update Profile')
    
    def validate_username(self, username):
        from flask_login import current_user
        user = User.query.filter_by(username=username.data).first()
        if user and user.id != current_user.id:
            raise ValidationError('Username already exists. Please choose a different one.')
    
    def validate_email(self, email):
        from flask_login import current_user
        user = User.query.filter_by(email=email.data).first()
        if user and user.id != current_user.id:
            raise ValidationError('Email already registered. Please use a different one.')
    
    def validate_current_password(self, current_password):
        from flask_login import current_user
        if self.new_password.data and not current_user.check_password(current_password.data):
            raise ValidationError('Current password is incorrect.')
