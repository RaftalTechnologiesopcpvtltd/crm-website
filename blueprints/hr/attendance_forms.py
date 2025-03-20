from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, DateField, TimeField, TextAreaField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Optional, Length

class AttendanceForm(FlaskForm):
    """Form for Attendance record"""
    employee_id = SelectField('Employee', validators=[DataRequired()], coerce=int)
    date = DateField('Date', validators=[DataRequired()])
    check_in_time = TimeField('Check-in Time', validators=[Optional()])
    check_out_time = TimeField('Check-out Time', validators=[Optional()])
    status = SelectField('Status', 
                       choices=[
                           ('present', 'Present'), 
                           ('absent', 'Absent'), 
                           ('late', 'Late'),
                           ('half-day', 'Half Day')
                       ],
                       default='present')
    remarks = TextAreaField('Remarks', validators=[Optional(), Length(max=255)])
    submit = SubmitField('Save Attendance')

class AttendanceBulkForm(FlaskForm):
    """Form for bulk attendance update"""
    date = DateField('Date', validators=[DataRequired()])
    mark_all_present = BooleanField('Mark All Present', default=False)
    submit = SubmitField('Update Attendance')

class AttendanceReportForm(FlaskForm):
    """Form for attendance report generation"""
    employee_id = SelectField('Employee', validators=[Optional()], coerce=int)
    start_date = DateField('Start Date', validators=[DataRequired()])
    end_date = DateField('End Date', validators=[DataRequired()])
    submit = SubmitField('Generate Report')

class PayrollCalculationForm(FlaskForm):
    """Form for payroll calculation based on attendance"""
    employee_id = SelectField('Employee', validators=[DataRequired()], coerce=int)
    pay_period_start = DateField('Pay Period Start', validators=[DataRequired()])
    pay_period_end = DateField('Pay Period End', validators=[DataRequired()])
    attendance_based = BooleanField('Calculate Based on Attendance', default=True)
    bonus = StringField('Bonus', validators=[Optional()])
    deductions = StringField('Deductions', validators=[Optional()])
    payment_date = DateField('Payment Date', validators=[DataRequired()])
    submit = SubmitField('Calculate Payroll')