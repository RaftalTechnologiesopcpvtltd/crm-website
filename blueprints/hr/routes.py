from datetime import datetime, timedelta, date
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from models import Employee, Leave, Payroll, User, Attendance
from blueprints.hr.forms import EmployeeForm, LeaveForm, PayrollForm
from blueprints.hr.attendance_forms import AttendanceForm, AttendanceBulkForm, AttendanceReportForm, PayrollCalculationForm
from utils import generate_csv, generate_pdf, format_currency

hr_bp = Blueprint('hr', __name__, url_prefix='/hr')

@hr_bp.before_request
@login_required
def check_access():
    # Allow access to HR department users and admins
    if current_user.is_admin or current_user.department == 'hr':
        return None
    
    # For other users, only allow access to view their own employee profile and leave requests
    # Block access to sensitive HR functions (employee list, payroll, attendance management)
    if request.endpoint in ['hr.attendance', 'hr.new_attendance', 'hr.bulk_attendance', 
                          'hr.payroll', 'hr.new_payroll', 'hr.calculate_payroll', 
                          'hr.employees', 'hr.new_employee']:
        flash('Access denied. You need HR privileges to access this section.', 'danger')
        return redirect(url_for('project_management.dashboard'))

@hr_bp.route('/employees')
def employees():
    employees = Employee.query.all()
    return render_template('hr/employees.html', employees=employees)

@hr_bp.route('/employees/new', methods=['GET', 'POST'])
def new_employee():
    if not current_user.is_admin and not current_user.department == 'hr':
        flash('Access denied. Admin or HR privileges required.', 'danger')
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
    if not current_user.is_admin and not current_user.department == 'hr':
        flash('Access denied. Admin or HR privileges required.', 'danger')
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
    if not current_user.is_admin and not current_user.department == 'hr':
        flash('Access denied. Admin or HR privileges required.', 'danger')
        return redirect(url_for('hr.employees'))
    
    employee = Employee.query.get_or_404(id)
    db.session.delete(employee)
    db.session.commit()
    
    flash('Employee deleted successfully!', 'success')
    return redirect(url_for('hr.employees'))

@hr_bp.route('/employees/export')
def export_employees():
    if not current_user.is_admin and not current_user.department == 'hr':
        flash('Access denied. Admin or HR privileges required.', 'danger')
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
    if not current_user.is_admin and not current_user.department == 'hr':
        flash('Access denied. Admin or HR privileges required.', 'danger')
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
    # If user is admin or in HR department, show all leaves
    if current_user.is_admin or current_user.department == 'hr':
        leaves = Leave.query.order_by(Leave.start_date.desc()).all()
        return render_template('hr/leaves.html', leaves=leaves, show_all=True)
    else:
        # Regular employees can only see their own leave requests
        employee = Employee.query.filter_by(user_id=current_user.id).first()
        if not employee:
            flash('You are not registered as an employee.', 'warning')
            return redirect(url_for('project_management.dashboard'))
        leaves = Leave.query.filter_by(employee_id=employee.id).order_by(Leave.start_date.desc()).all()
        return render_template('hr/leaves.html', leaves=leaves, show_all=False)

@hr_bp.route('/leaves/new', methods=['GET', 'POST'])
def new_leave():
    employee = None
    is_hr_or_admin = current_user.is_admin or current_user.department == 'hr'
    
    if not is_hr_or_admin:
        employee = Employee.query.filter_by(user_id=current_user.id).first()
        if not employee:
            flash('You are not registered as an employee.', 'warning')
            return redirect(url_for('project_management.dashboard'))
    
    form = LeaveForm()
    
    if is_hr_or_admin:
        form.employee_id.choices = [(e.id, e.full_name) for e in Employee.query.all()]
    else:
        # For regular users, only allow them to select their own employee record
        form.employee_id.choices = [(employee.id, employee.full_name)]
        form.employee_id.data = employee.id
    
    if form.validate_on_submit():
        leave = Leave(
            employee_id=form.employee_id.data if is_hr_or_admin else employee.id,
            leave_type=form.leave_type.data,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            reason=form.reason.data,
            status='approved' if is_hr_or_admin else 'pending'
        )
        db.session.add(leave)
        db.session.commit()
        
        flash('Leave request submitted successfully!', 'success')
        return redirect(url_for('hr.leaves'))
    
    return render_template('hr/leave_form.html', form=form, title='New Leave Request')

@hr_bp.route('/leaves/<int:id>/edit', methods=['GET', 'POST'])
def edit_leave(id):
    leave = Leave.query.get_or_404(id)
    
    # Check if user has permission to edit this leave
    is_hr_or_admin = current_user.is_admin or current_user.department == 'hr'
    is_owner = current_user.employee and current_user.employee.id == leave.employee_id
    
    if not is_hr_or_admin and not is_owner:
        flash('Access denied. You can only edit your own leave requests.', 'danger')
        return redirect(url_for('hr.leaves'))
    
    # Regular employees can only edit pending leaves
    if not is_hr_or_admin and leave.status != 'pending':
        flash('You cannot edit a leave request that has already been processed.', 'warning')
        return redirect(url_for('hr.leaves'))
    
    form = LeaveForm(obj=leave)
    
    # HR or Admin can edit all fields including status
    if is_hr_or_admin:
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
    
    # Check if user has permission to delete this leave
    is_hr_or_admin = current_user.is_admin or current_user.department == 'hr'
    is_owner = current_user.employee and current_user.employee.id == leave.employee_id
    
    if not is_hr_or_admin and not is_owner:
        flash('Access denied. You can only delete your own leave requests.', 'danger')
        return redirect(url_for('hr.leaves'))
    
    # Regular employees can only delete pending leaves
    if not is_hr_or_admin and leave.status != 'pending':
        flash('You cannot delete a leave request that has already been processed.', 'warning')
        return redirect(url_for('hr.leaves'))
    
    db.session.delete(leave)
    db.session.commit()
    
    flash('Leave request deleted successfully!', 'success')
    return redirect(url_for('hr.leaves'))

@hr_bp.route('/payroll')
def payroll():
    if not current_user.is_admin and not current_user.department == 'hr':
        flash('Access denied. Admin or HR privileges required.', 'danger')
        return redirect(url_for('hr.employees'))
    
    payrolls = Payroll.query.order_by(Payroll.payment_date.desc()).all()
    return render_template('hr/payroll.html', payrolls=payrolls)

@hr_bp.route('/payroll/new', methods=['GET', 'POST'])
def new_payroll():
    if not current_user.is_admin and not current_user.department == 'hr':
        flash('Access denied. Admin or HR privileges required.', 'danger')
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
    if not current_user.is_admin and not current_user.department == 'hr':
        flash('Access denied. Admin or HR privileges required.', 'danger')
        return redirect(url_for('hr.employees'))
    
    payroll = Payroll.query.get_or_404(id)
    return render_template('hr/payroll_detail.html', payroll=payroll)

@hr_bp.route('/payroll/<int:id>/slip')
def payroll_slip(id):
    # Admin and HR can access any payslip
    is_hr_or_admin = current_user.is_admin or current_user.department == 'hr'
    
    if not is_hr_or_admin:
        # Regular employees can only view their own payslips
        employee = Employee.query.filter_by(user_id=current_user.id).first()
        if not employee:
            flash('Access denied.', 'danger')
            return redirect(url_for('project_management.dashboard'))
    
    payroll = Payroll.query.get_or_404(id)
    
    # Check if regular employee is trying to view someone else's payslip
    if not is_hr_or_admin:
        if payroll.employee_id != employee.id:
            flash('Access denied. You can only view your own payslips.', 'danger')
            return redirect(url_for('project_management.dashboard'))
    
    return generate_pdf(
        'hr/payslip.html', 
        f'payslip_{payroll.payment_date}',
        payroll=payroll
    )

# Attendance Routes
@hr_bp.route('/attendance')
def attendance():
    """View attendance records"""
    if current_user.is_admin or current_user.department == 'hr':
        # Admins and HR can see all attendance records
        query = Attendance.query
        
        # Filter by employee if specified
        employee_id = request.args.get('employee_id', type=int)
        if employee_id:
            query = query.filter_by(employee_id=employee_id)
        
        # Filter by date range if specified
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        if start_date and end_date:
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
                query = query.filter(Attendance.date >= start_date, Attendance.date <= end_date)
            except ValueError:
                flash('Invalid date format. Use YYYY-MM-DD.', 'danger')
        
        attendance_records = query.order_by(Attendance.date.desc()).all()
        employees = Employee.query.all()
    else:
        # Regular users can only see their own attendance
        employee = Employee.query.filter_by(user_id=current_user.id).first()
        if not employee:
            flash('You are not registered as an employee.', 'warning')
            return redirect(url_for('project_management.dashboard'))
        
        attendance_records = Attendance.query.filter_by(employee_id=employee.id).order_by(Attendance.date.desc()).all()
        employees = [employee]
    
    return render_template('hr/attendance.html', attendance_records=attendance_records, employees=employees)

@hr_bp.route('/attendance/new', methods=['GET', 'POST'])
def new_attendance():
    """Create a new attendance record"""
    if not current_user.is_admin and not current_user.department == 'hr':
        flash('Access denied. Admin or HR privileges required.', 'danger')
        return redirect(url_for('hr.attendance'))
    
    form = AttendanceForm()
    form.employee_id.choices = [(e.id, e.full_name) for e in Employee.query.all()]
    
    if form.validate_on_submit():
        # Check if record already exists for this employee and date
        existing = Attendance.query.filter_by(
            employee_id=form.employee_id.data,
            date=form.date.data
        ).first()
        
        if existing:
            flash(f'Attendance record already exists for this employee on {form.date.data}. Please edit the existing record.', 'warning')
            return redirect(url_for('hr.attendance'))
        
        attendance = Attendance(
            employee_id=form.employee_id.data,
            date=form.date.data,
            check_in_time=form.check_in_time.data,
            check_out_time=form.check_out_time.data,
            status=form.status.data,
            remarks=form.remarks.data
        )
        
        db.session.add(attendance)
        db.session.commit()
        
        flash('Attendance record created successfully!', 'success')
        return redirect(url_for('hr.attendance'))
    
    return render_template('hr/attendance_form.html', form=form, title='New Attendance Record')

@hr_bp.route('/attendance/<int:id>/edit', methods=['GET', 'POST'])
def edit_attendance(id):
    """Edit an attendance record"""
    if not current_user.is_admin and not current_user.department == 'hr':
        flash('Access denied. Admin or HR privileges required.', 'danger')
        return redirect(url_for('hr.attendance'))
    
    attendance = Attendance.query.get_or_404(id)
    form = AttendanceForm(obj=attendance)
    form.employee_id.choices = [(e.id, e.full_name) for e in Employee.query.all()]
    
    if form.validate_on_submit():
        form.populate_obj(attendance)
        db.session.commit()
        
        flash('Attendance record updated successfully!', 'success')
        return redirect(url_for('hr.attendance'))
    
    return render_template('hr/attendance_form.html', form=form, attendance=attendance, title='Edit Attendance Record')

@hr_bp.route('/attendance/<int:id>/delete', methods=['POST'])
def delete_attendance(id):
    """Delete an attendance record"""
    if not current_user.is_admin and not current_user.department == 'hr':
        flash('Access denied. Admin or HR privileges required.', 'danger')
        return redirect(url_for('hr.attendance'))
    
    attendance = Attendance.query.get_or_404(id)
    db.session.delete(attendance)
    db.session.commit()
    
    flash('Attendance record deleted successfully!', 'success')
    return redirect(url_for('hr.attendance'))

@hr_bp.route('/attendance/bulk', methods=['GET', 'POST'])
def bulk_attendance():
    """Bulk attendance creation/update"""
    if not current_user.is_admin and not current_user.department == 'hr':
        flash('Access denied. Admin or HR privileges required.', 'danger')
        return redirect(url_for('hr.attendance'))
    
    form = AttendanceBulkForm()
    
    if form.validate_on_submit():
        date = form.date.data
        employees = Employee.query.all()
        
        for employee in employees:
            # Check if attendance record already exists
            existing = Attendance.query.filter_by(employee_id=employee.id, date=date).first()
            
            if existing:
                # Update existing record if mark all present is checked
                if form.mark_all_present.data:
                    existing.status = 'present'
                    db.session.add(existing)
            else:
                # Create new record
                attendance = Attendance(
                    employee_id=employee.id,
                    date=date,
                    status='present' if form.mark_all_present.data else 'absent'
                )
                db.session.add(attendance)
        
        db.session.commit()
        flash('Bulk attendance records updated successfully!', 'success')
        return redirect(url_for('hr.attendance'))
    
    return render_template('hr/attendance_bulk_form.html', form=form, title='Bulk Attendance Update')

@hr_bp.route('/attendance/report', methods=['GET', 'POST'])
def attendance_report():
    """Generate attendance report"""
    if not current_user.is_admin and not current_user.department == 'hr':
        flash('Access denied. Admin or HR privileges required.', 'danger')
        return redirect(url_for('hr.attendance'))
    
    form = AttendanceReportForm()
    form.employee_id.choices = [(0, 'All Employees')] + [(e.id, e.full_name) for e in Employee.query.all()]
    
    if form.validate_on_submit():
        start_date = form.start_date.data
        end_date = form.end_date.data
        
        if start_date > end_date:
            flash('Start date cannot be after end date.', 'danger')
            return render_template('hr/attendance_report_form.html', form=form, title='Attendance Report')
        
        # Generate report
        if form.employee_id.data == 0:
            # Report for all employees
            employees = Employee.query.all()
            attendance_data = []
            
            for employee in employees:
                attendance_summary = employee.get_attendance_summary(start_date, end_date)
                attendance_data.append({
                    'employee': employee,
                    'summary': attendance_summary
                })
            
            return render_template(
                'hr/attendance_report.html',
                attendance_data=attendance_data,
                start_date=start_date,
                end_date=end_date,
                title='Attendance Report - All Employees'
            )
        else:
            # Report for specific employee
            employee = Employee.query.get_or_404(form.employee_id.data)
            attendance_records = employee.get_attendance_for_period(start_date, end_date)
            attendance_summary = employee.get_attendance_summary(start_date, end_date)
            
            return render_template(
                'hr/attendance_report_employee.html',
                employee=employee,
                attendance_records=attendance_records,
                attendance_summary=attendance_summary,
                start_date=start_date,
                end_date=end_date,
                title=f'Attendance Report - {employee.full_name}'
            )
    
    return render_template('hr/attendance_report_form.html', form=form, title='Attendance Report')

@hr_bp.route('/payroll/calculate', methods=['GET', 'POST'])
def calculate_payroll():
    """Calculate payroll based on attendance"""
    if not current_user.is_admin and not current_user.department == 'hr':
        flash('Access denied. Admin or HR privileges required.', 'danger')
        return redirect(url_for('hr.payroll'))
    
    form = PayrollCalculationForm()
    form.employee_id.choices = [(e.id, e.full_name) for e in Employee.query.all()]
    
    if form.validate_on_submit():
        employee = Employee.query.get(form.employee_id.data)
        
        # Create new payroll record
        payroll = Payroll(
            employee_id=form.employee_id.data,
            pay_period_start=form.pay_period_start.data,
            pay_period_end=form.pay_period_end.data,
            base_salary=employee.salary,
            attendance_based=form.attendance_based.data,
            bonus=form.bonus.data or 0,
            deductions=form.deductions.data or 0,
            payment_date=form.payment_date.data,
            status='pending'
        )
        
        # Calculate net pay based on attendance if selected
        if form.attendance_based.data:
            payroll.calculate_from_attendance()
        else:
            payroll.net_pay = float(employee.salary) + float(form.bonus.data or 0) - float(form.deductions.data or 0)
        
        db.session.add(payroll)
        db.session.commit()
        
        flash('Payroll record calculated and created successfully!', 'success')
        return redirect(url_for('hr.payroll_detail', id=payroll.id))
    
    return render_template('hr/payroll_calculation_form.html', form=form, title='Calculate Payroll')
