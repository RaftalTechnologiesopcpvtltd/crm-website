from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, DecimalField, DateField, HiddenField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Length, Optional, NumberRange, Email
from wtforms.fields import EmailField
from decimal import Decimal

class ClientUserForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(max=100)])
    email = EmailField('Email', validators=[Optional(), Email(), Length(max=120)])
    platform = SelectField('Platform', 
                         choices=[('fiverr', 'Fiverr'), 
                                 ('upwork', 'Upwork'), 
                                 ('other', 'Other')],
                         default='other')
    platform_username = StringField('Platform Username', validators=[Optional(), Length(max=100)])
    is_existing_user = BooleanField('Is Existing User?')
    existing_user_id = SelectField('Select Existing User', validators=[Optional()], coerce=int)
    submit = SubmitField('Save Client')

class ProjectForm(FlaskForm):
    name = StringField('Project Name', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('Description', validators=[Optional()])
    client = StringField('Client Name', validators=[Optional(), Length(max=100)])
    client_user_id = SelectField('Client User', validators=[Optional()], coerce=int)
    platform = SelectField('Platform', 
                         choices=[('fiverr', 'Fiverr'), 
                                 ('upwork', 'Upwork'), 
                                 ('other', 'Other')],
                         default='other')
    platform_project_id = StringField('Platform Project ID', validators=[Optional(), Length(max=100)])
    start_date = DateField('Start Date', validators=[DataRequired()])
    end_date = DateField('End Date', validators=[Optional()])
    status = SelectField('Status', 
                       choices=[('planning', 'Planning'), 
                               ('in-progress', 'In Progress'), 
                               ('completed', 'Completed'),
                               ('on-hold', 'On Hold')],
                       default='planning')
    budget = DecimalField('Budget', validators=[Optional(), NumberRange(min=0)], places=2)
    payment_status = SelectField('Payment Status', 
                              choices=[('pending', 'Pending'), 
                                      ('in-review', 'In Review'), 
                                      ('in-platform', 'In Platform'),
                                      ('transferred', 'Transferred')],
                              default='pending')
    submit = SubmitField('Save Project')

class TaskForm(FlaskForm):
    user_id = SelectField('Assign To', validators=[Optional()], coerce=int)
    title = StringField('Task Title', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('Description', validators=[Optional()])
    due_date = DateField('Due Date', validators=[Optional()])
    priority = SelectField('Priority', 
                         choices=[('low', 'Low'), 
                                 ('medium', 'Medium'), 
                                 ('high', 'High'),
                                 ('urgent', 'Urgent')],
                         default='medium')
    status = SelectField('Status', 
                       choices=[('to-do', 'To Do'), 
                               ('in-progress', 'In Progress'), 
                               ('in-review', 'In Review'),
                               ('completed', 'Completed')],
                       default='to-do')
    submit = SubmitField('Save Task')

class ProjectMilestoneForm(FlaskForm):
    name = StringField('Milestone Name', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('Description', validators=[Optional()])
    due_date = DateField('Due Date', validators=[DataRequired()])
    amount = DecimalField('Amount', validators=[DataRequired(), NumberRange(min=0)], places=2)
    status = SelectField('Status', 
                      choices=[('pending', 'Pending'), 
                              ('completed', 'Completed'), 
                              ('paid', 'Paid')],
                      default='pending')
    submit = SubmitField('Save Milestone')

class AccountForm(FlaskForm):
    name = StringField('Account Name', validators=[DataRequired(), Length(max=100)])
    account_type = SelectField('Account Type', 
                             choices=[('bank', 'Bank Account'), 
                                    ('paypal', 'PayPal'), 
                                    ('stripe', 'Stripe'),
                                    ('other', 'Other')],
                             default='bank')
    currency = SelectField('Currency', 
                         choices=[('USD', 'USD'), 
                                 ('EUR', 'EUR'), 
                                 ('GBP', 'GBP'),
                                 ('INR', 'INR'),
                                 ('AUD', 'AUD'),
                                 ('CAD', 'CAD')],
                         default='USD')
    description = TextAreaField('Description', validators=[Optional()])
    submit = SubmitField('Save Account')

class ProjectPaymentForm(FlaskForm):
    project_id = SelectField('Project', validators=[DataRequired()], coerce=int)
    milestone_id = SelectField('Milestone', validators=[Optional()], coerce=int)
    account_id = SelectField('Account', validators=[Optional()], coerce=int)
    amount_original = DecimalField('Original Amount', validators=[DataRequired(), NumberRange(min=0)], places=2)
    currency_original = SelectField('Original Currency', 
                                 choices=[('USD', 'USD'), 
                                         ('EUR', 'EUR'), 
                                         ('GBP', 'GBP'),
                                         ('INR', 'INR'),
                                         ('AUD', 'AUD'),
                                         ('CAD', 'CAD')],
                                 default='USD')
    platform_fee = DecimalField('Platform Fee', validators=[Optional(), NumberRange(min=0)], places=2, default=Decimal('0.00'))
    conversion_fee = DecimalField('Conversion Fee', validators=[Optional(), NumberRange(min=0)], places=2, default=Decimal('0.00'))
    conversion_rate = DecimalField('Conversion Rate', validators=[Optional(), NumberRange(min=0)], places=6, default=Decimal('1.000000'))
    amount_received = DecimalField('Amount Received', validators=[Optional(), NumberRange(min=0)], places=2)
    currency_received = SelectField('Received Currency', 
                                  choices=[('USD', 'USD'), 
                                          ('EUR', 'EUR'), 
                                          ('GBP', 'GBP'),
                                          ('INR', 'INR'),
                                          ('AUD', 'AUD'),
                                          ('CAD', 'CAD')],
                                  default='USD')
    payment_date = DateField('Payment Date', validators=[Optional()])
    status = SelectField('Status', 
                       choices=[('pending', 'Pending'), 
                               ('in-review', 'In Review'), 
                               ('in-platform', 'In Platform'),
                               ('transferred', 'Transferred'),
                               ('reconciled', 'Reconciled')],
                       default='pending')
    notes = TextAreaField('Notes', validators=[Optional()])
    submit = SubmitField('Save Payment')
