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
    department = db.Column(db.String(64), default='general')  # accounting, hr, developer, general
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    employee = db.relationship('Employee', backref='user', uselist=False, lazy=True)
    tasks = db.relationship('Task', backref='assigned_to', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def has_access(self, department_list):
        """Check if user has access to the specified departments"""
        if self.is_admin:
            return True
        if isinstance(department_list, str):
            return self.department == department_list
        return self.department in department_list
    
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
    attendances = db.relationship('Attendance', backref='employee', lazy=True)
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def get_attendance_for_period(self, start_date, end_date):
        """Get attendance records for a specific period"""
        from app import db
        return Attendance.query.filter(
            Attendance.employee_id == self.id,
            Attendance.date >= start_date,
            Attendance.date <= end_date
        ).order_by(Attendance.date.asc()).all()
    
    def get_attendance_summary(self, start_date, end_date):
        """Get attendance summary for a specific period"""
        attendance_records = self.get_attendance_for_period(start_date, end_date)
        
        # Initialize counters
        total_days = (end_date - start_date).days + 1
        present_days = 0
        absent_days = 0
        late_days = 0
        
        # Count attendance statuses
        for record in attendance_records:
            if record.status == 'present':
                present_days += 1
            elif record.status == 'absent':
                absent_days += 1
            elif record.status == 'late':
                late_days += 1
        
        return {
            'total_days': total_days,
            'present_days': present_days,
            'absent_days': absent_days,
            'late_days': late_days,
            'attendance_percentage': (present_days / total_days * 100) if total_days > 0 else 0
        }
    
    def calculate_salary_based_on_attendance(self, start_date, end_date):
        """Calculate salary based on attendance for a specific period"""
        # Get attendance summary
        attendance_summary = self.get_attendance_summary(start_date, end_date)
        
        # Calculate working days in the period
        from datetime import timedelta
        working_days = 0
        current_date = start_date
        while current_date <= end_date:
            # Skip weekends (0 = Monday, 6 = Sunday)
            if current_date.weekday() < 5:  # Weekdays only
                working_days += 1
            current_date += timedelta(days=1)
        
        # Calculate daily salary
        daily_salary = self.salary / working_days if working_days > 0 else 0
        
        # Calculate salary based on attendance
        # Full salary for present days, no salary for absent days, reduced for late
        present_salary = daily_salary * attendance_summary['present_days']
        late_salary = daily_salary * 0.5 * attendance_summary['late_days']  # Half pay for late days
        
        # Total salary
        total_salary = present_salary + late_salary
        
        return {
            'daily_salary': daily_salary,
            'present_salary': present_salary,
            'late_salary': late_salary,
            'total_salary': total_salary,
            'attendance_summary': attendance_summary
        }
    
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
    attendance_based = db.Column(db.Boolean, default=False)  # Whether salary is calculated based on attendance
    attendance_salary = db.Column(db.Numeric(10, 2), default=0)  # Salary calculated based on attendance
    present_days = db.Column(db.Integer, default=0)  # Number of days present
    absent_days = db.Column(db.Integer, default=0)  # Number of days absent
    late_days = db.Column(db.Integer, default=0)  # Number of days late
    bonus = db.Column(db.Numeric(10, 2), default=0)
    deductions = db.Column(db.Numeric(10, 2), default=0)
    net_pay = db.Column(db.Numeric(10, 2), nullable=False)
    payment_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, processed, paid
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def calculate_from_attendance(self):
        """Calculate salary based on attendance"""
        if not self.attendance_based:
            return
            
        attendance_data = self.employee.calculate_salary_based_on_attendance(
            self.pay_period_start, self.pay_period_end
        )
        
        # Update attendance-related fields
        self.attendance_salary = attendance_data['total_salary']
        self.present_days = attendance_data['attendance_summary']['present_days']
        self.absent_days = attendance_data['attendance_summary']['absent_days']
        self.late_days = attendance_data['attendance_summary']['late_days']
        
        # Calculate net pay
        self.net_pay = self.attendance_salary + self.bonus - self.deductions
        
        return self.net_pay
        
    def calculate_net_pay(self):
        """Calculate net pay"""
        if self.attendance_based:
            self.calculate_from_attendance()
        else:
            self.net_pay = self.base_salary + self.bonus - self.deductions
        return self.net_pay
    
    def __repr__(self):
        return f'<Payroll {self.payment_date} - {self.status}>'

class Account(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    account_type = db.Column(db.String(50), nullable=False)  # bank, paypal, etc.
    currency = db.Column(db.String(3), default='USD')
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    project_payments = db.relationship('ProjectPayment', backref='account', lazy=True)
    
    def __repr__(self):
        return f'<Account {self.name}>'

class ClientUser(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120))
    platform = db.Column(db.String(50))  # Fiverr, Upwork, etc.
    platform_username = db.Column(db.String(100))
    is_existing_user = db.Column(db.Boolean, default=False)
    existing_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    projects = db.relationship('Project', backref='client_user', lazy=True)
    existing_user = db.relationship('User', backref='client_profiles', lazy=True)
    
    def __repr__(self):
        return f'<ClientUser {self.name}>'

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    client = db.Column(db.String(100))
    client_user_id = db.Column(db.Integer, db.ForeignKey('client_user.id'), nullable=True)
    platform = db.Column(db.String(50), default='other')  # fiverr, upwork, other
    platform_project_id = db.Column(db.String(100))  # ID from the platform
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date)
    status = db.Column(db.String(20), default='planning')  # planning, in-progress, completed, on-hold
    budget = db.Column(db.Numeric(10, 2))
    payment_status = db.Column(db.String(50), default='pending')  # pending, in-review, in-platform, transferred
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tasks = db.relationship('Task', backref='project', lazy=True, cascade='all, delete-orphan')
    milestones = db.relationship('ProjectMilestone', backref='project', lazy=True, cascade='all, delete-orphan')
    payments = db.relationship('ProjectPayment', backref='project', lazy=True, cascade='all, delete-orphan')
    sale = db.relationship('Sales', backref='project_sale', uselist=False, cascade='all, delete-orphan')
    
    @property
    def progress(self):
        if not self.tasks:
            return 0
        completed_tasks = sum(1 for task in self.tasks if task.status == 'completed')
        return int((completed_tasks / len(self.tasks)) * 100)
    
    def __repr__(self):
        return f'<Project {self.name}>'

class ProjectMilestone(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    due_date = db.Column(db.Date, nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, completed, paid
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    @property
    def progress(self):
        """Calculate milestone progress based on completed tasks in the project"""
        from sqlalchemy import func
        from app import db
        from models import Task  # Local import to avoid circular imports
        
        # Get total number of tasks for this project
        total_tasks = Task.query.filter_by(project_id=self.project_id).count()
        
        if total_tasks == 0:
            return 0
            
        # Get number of completed tasks
        completed_tasks = Task.query.filter_by(
            project_id=self.project_id, 
            status='completed'
        ).count()
        
        # Calculate percentage
        return int((completed_tasks / total_tasks) * 100)
    
    def __repr__(self):
        return f'<ProjectMilestone {self.name}>'

class ProjectPayment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    milestone_id = db.Column(db.Integer, db.ForeignKey('project_milestone.id'), nullable=True)
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=True)
    amount_original = db.Column(db.Numeric(10, 2), nullable=False)
    currency_original = db.Column(db.String(3), default='USD')
    platform_fee = db.Column(db.Numeric(10, 2), default=0)
    conversion_fee = db.Column(db.Numeric(10, 2), default=0)
    conversion_rate = db.Column(db.Numeric(10, 6), default=1)
    amount_received = db.Column(db.Numeric(10, 2))
    currency_received = db.Column(db.String(3), default='USD')
    payment_date = db.Column(db.Date)
    status = db.Column(db.String(20), default='pending')  # pending, in-review, in-platform, transferred, reconciled
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_recorded_in_sales = db.Column(db.Boolean, default=False)  # Track if payment is reflected in sales
    
    # Relationships
    milestone = db.relationship('ProjectMilestone', backref='payment', uselist=False)
    
    def update_project_sales(self):
        """Update the project's sales record with this payment"""
        from app import db
        if not self.is_recorded_in_sales and self.amount_received and self.status == 'transferred':
            project_sale = Sales.query.filter_by(project_id=self.project_id).first()
            if project_sale:
                project_sale.received_amount += self.amount_received
                project_sale.calculate_difference()
                self.is_recorded_in_sales = True
                db.session.commit()
    
    def __repr__(self):
        return f'<ProjectPayment {self.amount_original} {self.currency_original}>'

class Sales(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    total_amount = db.Column(db.Numeric(10, 2), nullable=False)
    received_amount = db.Column(db.Numeric(10, 2), default=0)
    currency = db.Column(db.String(3), default='USD')
    status = db.Column(db.String(20), default='open')  # open, closed
    difference = db.Column(db.Numeric(10, 2), default=0)  # difference between total and received
    closed_date = db.Column(db.Date)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def calculate_difference(self):
        """Calculate the difference between total amount and received amount"""
        if self.total_amount and self.received_amount:
            self.difference = self.total_amount - self.received_amount
        return self.difference
        
    def __repr__(self):
        return f'<Sales for Project #{self.project_id} - {self.status}>'

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    milestone_id = db.Column(db.Integer, db.ForeignKey('project_milestone.id'), nullable=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    due_date = db.Column(db.Date)
    priority = db.Column(db.String(20), default='medium')  # low, medium, high, urgent
    status = db.Column(db.String(20), default='to-do')  # to-do, in-progress, in-review, completed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    milestone = db.relationship('ProjectMilestone', backref='tasks', lazy=True)
    
    def __repr__(self):
        return f'<Task {self.title}>'

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    check_in_time = db.Column(db.Time, nullable=True)
    check_out_time = db.Column(db.Time, nullable=True)
    status = db.Column(db.String(20), default='present')  # present, absent, late, half-day
    remarks = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Define unique constraint for employee and date
    __table_args__ = (db.UniqueConstraint('employee_id', 'date', name='unique_employee_attendance_date'),)
    
    @property
    def total_hours(self):
        """Calculate total hours worked"""
        if self.check_in_time and self.check_out_time:
            checkin = datetime.combine(self.date, self.check_in_time)
            checkout = datetime.combine(self.date, self.check_out_time)
            duration = checkout - checkin
            return round(duration.total_seconds() / 3600, 2)  # Convert to hours
        return 0
    
    def __repr__(self):
        return f'<Attendance {self.employee_id} - {self.date} - {self.status}>'
