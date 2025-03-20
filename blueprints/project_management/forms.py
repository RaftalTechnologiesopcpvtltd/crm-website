from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, DecimalField, DateField, HiddenField, SubmitField
from wtforms.validators import DataRequired, Length, Optional, NumberRange

class ProjectForm(FlaskForm):
    name = StringField('Project Name', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('Description', validators=[Optional()])
    client = StringField('Client', validators=[Optional(), Length(max=100)])
    start_date = DateField('Start Date', validators=[DataRequired()])
    end_date = DateField('End Date', validators=[Optional()])
    status = SelectField('Status', 
                       choices=[('planning', 'Planning'), 
                               ('in-progress', 'In Progress'), 
                               ('completed', 'Completed'),
                               ('on-hold', 'On Hold')],
                       default='planning')
    budget = DecimalField('Budget', validators=[Optional(), NumberRange(min=0)], places=2)
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
