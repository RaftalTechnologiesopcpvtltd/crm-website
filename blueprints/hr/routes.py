from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from models import Employee, Leave, Payroll, User
from blueprints.hr.forms import EmployeeForm, LeaveForm, PayrollForm
from utils import generate_csv, generate_pdf, format_currency

hr_bp = Blueprint('hr', __name__, url_prefix='/hr')

@hr_bp.before_request
@login_required
def check_admin():
    if not current_user.is_admin and not getattr(current_user, 'employee', None):
        flash('Access denied. You need HR privileges to access this section.', 'danger')
        return redirect(url_for('project_management.dashboard'))

@hr_bp.route('/employees')
def employees():
    employees = Employee.query.all()
    return render_template('hr/employees.html', employees=employees)

@hr_bp.route('/employees/new', methods=['GET', 'POST'])
def new_employee():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('hr.employees'))
    
    form = EmployeeForm()
    # Populate user choices
    form.user_id.choices = [(u.id, u.username) for u in User.query.filter(
        ~User.id.in_(db.session.query(Employee.user_id)))
    ]
    
    if form.validate_on_submit():
        employee = Employee(
            user_id=form.user_id.data,
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            department=form.department.data,
            position=form.position.data,
            hire_date=form.hire_date.data,
            salary=form.salary.data,
            phone=form.phone.data,
            address=form.address.data,
        )
        db.session.add(employee)
        db.session.commit()
        
        flash('Employee created successfully!', 'success')
        return redirect(url_for('hr.employees'))
    
    return render_template('hr/employee_form.html', form=form, title='New Employee')

@hr_bp.route('/employees/<int:id>')
def employee_detail(id):
    employee = Employee.query.get_or_404(id)
    return render_template('hr/employee_detail.html', employee=employee)

@hr_bp.route('/employees/<int:id>/edit', methods=['GET', 'POST'])
def edit_employee(id):
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('hr.employees'))
    
    employee = Employee.query.get_or_404(id)
    form = EmployeeForm(obj=employee)
    
    # Populate user choices and include the current user
    users = User.query.filter(
        db.or_(User.id == employee.user_id, 
               ~User.id.in_(db.session.query(Employee.user_id)))
    ).all()
    form.user_id.choices = [(u.id, u.username) for u in users]
    
    if form.validate_on_submit():
        form.populate_obj(employee)
        db.session.commit()
        
        flash('Employee updated successfully!', 'success')
        return redirect(url_for('hr.employee_detail', id=employee.id))
    
    return render_template('hr/employee_form.html', form=form, employee=employee, title='Edit Employee')

@hr_bp.route('/employees/<int:id>/delete', methods=['POST'])
def delete_employee(id):
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('hr.employees'))
    
    employee = Employee.query.get_or_404(id)
    db.session.delete(employee)
    db.session.commit()
    
    flash('Employee deleted successfully!', 'success')
    return redirect(url_for('hr.employees'))

@hr_bp.route('/employees/export')
def export_employees():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('hr.employees'))
    
    employees = Employee.query.all()
    headers = ['ID', 'Name', 'Department', 'Position', 'Hire Date', 'Salary']
    
    data = []
    for emp in employees:
        data.append({
            'ID': emp.id,
            'Name': emp.full_name,
            'Department': emp.department,
            'Position': emp.position,
            'Hire Date': emp.hire_date.strftime('%Y-%m-%d'),
            'Salary': format_currency(emp.salary)
        })
    
    return generate_csv(data, 'employees')

@hr_bp.route('/employees/report')
def employee_report():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('hr.employees'))
    
    employees = Employee.query.all()
    report_date = datetime.now().strftime('%Y-%m-%d')
    
    return generate_pdf(
        'hr/employee_report.html', 
        'employee_report',
        employees=employees,
        report_date=report_date
    )

@hr_bp.route('/leaves')
def leaves():
    if current_user.is_admin:
        leaves = Leave.query.order_by(Leave.start_date.desc()).all()
    else:
        employee = Employee.query.filter_by(user_id=current_user.id).first()
        if not employee:
            flash('You are not registered as an employee.', 'warning')
            return redirect(url_for('project_management.dashboard'))
        leaves = Leave.query.filter_by(employee_id=employee.id).order_by(Leave.start_date.desc()).all()
    
    return render_template('hr/leaves.html', leaves=leaves)

@hr_bp.route('/leaves/new', methods=['GET', 'POST'])
def new_leave():
    employee = None
    if not current_user.is_admin:
        employee = Employee.query.filter_by(user_id=current_user.id).first()
        if not employee:
            flash('You are not registered as an employee.', 'warning')
            return redirect(url_for('project_management.dashboard'))
    
    form = LeaveForm()
    
    if current_user.is_admin:
        form.employee_id.choices = [(e.id, e.full_name) for e in Employee.query.all()]
    else:
        form.employee_id.data = employee.id
        form.employee_id.render_kw = {'readonly': True}
    
    if form.validate_on_submit():
        leave = Leave(
            employee_id=form.employee_id.data if current_user.is_admin else employee.id,
            leave_type=form.leave_type.data,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            reason=form.reason.data,
            status='approved' if current_user.is_admin else 'pending'
        )
        db.session.add(leave)
        db.session.commit()
        
        flash('Leave request submitted successfully!', 'success')
        return redirect(url_for('hr.leaves'))
    
    return render_template('hr/leave_form.html', form=form, title='New Leave Request')

@hr_bp.route('/leaves/<int:id>/edit', methods=['GET', 'POST'])
def edit_leave(id):
    leave = Leave.query.get_or_404(id)
    
    if not current_user.is_admin and (not current_user.employee or current_user.employee.id != leave.employee_id):
        flash('Access denied. You can only edit your own leave requests.', 'danger')
        return redirect(url_for('hr.leaves'))
    
    if not current_user.is_admin and leave.status != 'pending':
        flash('You cannot edit a leave request that has already been processed.', 'warning')
        return redirect(url_for('hr.leaves'))
    
    form = LeaveForm(obj=leave)
    
    if current_user.is_admin:
        form.employee_id.choices = [(e.id, e.full_name) for e in Employee.query.all()]
        form.status.choices = [('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')]
    else:
        form.employee_id.render_kw = {'readonly': True}
        del form.status
    
    if form.validate_on_submit():
        form.populate_obj(leave)
        db.session.commit()
        
        flash('Leave request updated successfully!', 'success')
        return redirect(url_for('hr.leaves'))
    
    return render_template('hr/leave_form.html', form=form, leave=leave, title='Edit Leave Request')

@hr_bp.route('/leaves/<int:id>/delete', methods=['POST'])
def delete_leave(id):
    leave = Leave.query.get_or_404(id)
    
    if not current_user.is_admin and (not current_user.employee or current_user.employee.id != leave.employee_id):
        flash('Access denied. You can only delete your own leave requests.', 'danger')
        return redirect(url_for('hr.leaves'))
    
    if not current_user.is_admin and leave.status != 'pending':
        flash('You cannot delete a leave request that has already been processed.', 'warning')
        return redirect(url_for('hr.leaves'))
    
    db.session.delete(leave)
    db.session.commit()
    
    flash('Leave request deleted successfully!', 'success')
    return redirect(url_for('hr.leaves'))

@hr_bp.route('/payroll')
def payroll():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('hr.employees'))
    
    payrolls = Payroll.query.order_by(Payroll.payment_date.desc()).all()
    return render_template('hr/payroll.html', payrolls=payrolls)

@hr_bp.route('/payroll/new', methods=['GET', 'POST'])
def new_payroll():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('hr.employees'))
    
    form = PayrollForm()
    form.employee_id.choices = [(e.id, e.full_name) for e in Employee.query.all()]
    
    if form.validate_on_submit():
        employee = Employee.query.get(form.employee_id.data)
        net_pay = float(employee.salary) + float(form.bonus.data) - float(form.deductions.data)
        
        payroll = Payroll(
            employee_id=form.employee_id.data,
            pay_period_start=form.pay_period_start.data,
            pay_period_end=form.pay_period_end.data,
            base_salary=employee.salary,
            bonus=form.bonus.data,
            deductions=form.deductions.data,
            net_pay=net_pay,
            payment_date=form.payment_date.data,
            status=form.status.data
        )
        db.session.add(payroll)
        db.session.commit()
        
        flash('Payroll record created successfully!', 'success')
        return redirect(url_for('hr.payroll'))
    
    return render_template('hr/payroll_form.html', form=form, title='New Payroll Record')

@hr_bp.route('/payroll/<int:id>')
def payroll_detail(id):
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('hr.employees'))
    
    payroll = Payroll.query.get_or_404(id)
    return render_template('hr/payroll_detail.html', payroll=payroll)

@hr_bp.route('/payroll/<int:id>/slip')
def payroll_slip(id):
    if not current_user.is_admin:
        employee = Employee.query.filter_by(user_id=current_user.id).first()
        if not employee:
            flash('Access denied.', 'danger')
            return redirect(url_for('project_management.dashboard'))
    
    payroll = Payroll.query.get_or_404(id)
    
    if not current_user.is_admin and payroll.employee_id != employee.id:
        flash('Access denied. You can only view your own payslips.', 'danger')
        return redirect(url_for('project_management.dashboard'))
    
    return generate_pdf(
        'hr/payslip.html', 
        f'payslip_{payroll.payment_date}',
        payroll=payroll
    )
