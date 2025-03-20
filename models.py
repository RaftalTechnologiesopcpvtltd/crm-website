from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, login_manager

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    employee = db.relationship('Employee', backref='user', uselist=False, lazy=True)
    tasks = db.relationship('Task', backref='assigned_to', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'

class Employee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    first_name = db.Column(db.String(64), nullable=False)
    last_name = db.Column(db.String(64), nullable=False)
    department = db.Column(db.String(64), nullable=False)
    position = db.Column(db.String(64), nullable=False)
    hire_date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    salary = db.Column(db.Numeric(10, 2), nullable=False)
    phone = db.Column(db.String(20))
    address = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    leaves = db.relationship('Leave', backref='employee', lazy=True)
    payrolls = db.relationship('Payroll', backref='employee', lazy=True)
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def __repr__(self):
        return f'<Employee {self.full_name}>'

class Leave(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)
    leave_type = db.Column(db.String(20), nullable=False)  # sick, vacation, personal, etc.
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    reason = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Leave {self.leave_type} - {self.status}>'

class Payroll(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)
    pay_period_start = db.Column(db.Date, nullable=False)
    pay_period_end = db.Column(db.Date, nullable=False)
    base_salary = db.Column(db.Numeric(10, 2), nullable=False)
    bonus = db.Column(db.Numeric(10, 2), default=0)
    deductions = db.Column(db.Numeric(10, 2), default=0)
    net_pay = db.Column(db.Numeric(10, 2), nullable=False)
    payment_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, processed, paid
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Payroll {self.payment_date} - {self.status}>'

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    client = db.Column(db.String(100))
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date)
    status = db.Column(db.String(20), default='planning')  # planning, in-progress, completed, on-hold
    budget = db.Column(db.Numeric(10, 2))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tasks = db.relationship('Task', backref='project', lazy=True, cascade='all, delete-orphan')
    
    @property
    def progress(self):
        if not self.tasks:
            return 0
        completed_tasks = sum(1 for task in self.tasks if task.status == 'completed')
        return int((completed_tasks / len(self.tasks)) * 100)
    
    def __repr__(self):
        return f'<Project {self.name}>'

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    due_date = db.Column(db.Date)
    priority = db.Column(db.String(20), default='medium')  # low, medium, high, urgent
    status = db.Column(db.String(20), default='to-do')  # to-do, in-progress, in-review, completed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Task {self.title}>'
