from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, DecimalField, DateField, HiddenField, SubmitField
from wtforms.validators import DataRequired, Length, Optional, NumberRange

class EmployeeForm(FlaskForm):
    user_id = SelectField('User Account', validators=[DataRequired()], coerce=int)
    first_name = StringField('First Name', validators=[DataRequired(), Length(max=64)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(max=64)])
    department = SelectField('Department', validators=[DataRequired()], 
                           choices=[
                               ('accounting', 'Accounting'), 
                               ('hr', 'Human Resources'), 
                               ('developer', 'Developer'),
                               ('general', 'General')
                           ])
    position = StringField('Position', validators=[DataRequired(), Length(max=64)])
    hire_date = DateField('Hire Date', validators=[DataRequired()])
    salary = DecimalField('Salary', validators=[DataRequired(), NumberRange(min=0)], places=2)
    phone = StringField('Phone', validators=[Length(max=20)])
    address = TextAreaField('Address', validators=[Length(max=255)])
    submit = SubmitField('Save Employee')

class LeaveForm(FlaskForm):
    employee_id = SelectField('Employee', validators=[DataRequired()], coerce=int)
    leave_type = SelectField('Leave Type', validators=[DataRequired()],
                           choices=[('sick', 'Sick Leave'), 
                                   ('vacation', 'Vacation'), 
                                   ('personal', 'Personal Leave'),
                                   ('other', 'Other')])
    start_date = DateField('Start Date', validators=[DataRequired()])
    end_date = DateField('End Date', validators=[DataRequired()])
    reason = TextAreaField('Reason', validators=[Optional(), Length(max=255)])
    status = SelectField('Status', 
                        choices=[('pending', 'Pending'), 
                                ('approved', 'Approved'), 
                                ('rejected', 'Rejected')],
                        default='pending')
    submit = SubmitField('Submit Leave Request')

class PayrollForm(FlaskForm):
    employee_id = SelectField('Employee', validators=[DataRequired()], coerce=int)
    pay_period_start = DateField('Pay Period Start', validators=[DataRequired()])
    pay_period_end = DateField('Pay Period End', validators=[DataRequired()])
    bonus = DecimalField('Bonus', validators=[Optional(), NumberRange(min=0)], default=0, places=2)
    deductions = DecimalField('Deductions', validators=[Optional(), NumberRange(min=0)], default=0, places=2)
    payment_date = DateField('Payment Date', validators=[DataRequired()])
    status = SelectField('Status', 
                        choices=[('pending', 'Pending'), 
                                ('processed', 'Processed'), 
                                ('paid', 'Paid')],
                        default='pending')
    submit = SubmitField('Create Payroll Record')
