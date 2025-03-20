from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from models import Project, Task, User, Employee, ClientUser, ProjectMilestone, ProjectPayment, Account, Sales, Leave, Payroll
from blueprints.project_management.forms import (
    ProjectForm, TaskForm, ClientUserForm, ProjectMilestoneForm, 
    ProjectPaymentForm, AccountForm, SalesForm
)
from utils import generate_csv, generate_pdf
from decimal import Decimal
from sqlalchemy import func
from datetime import datetime, date

project_bp = Blueprint('project_management', __name__, url_prefix='')

@project_bp.before_request
@login_required
def check_access():
    """
    Check if user has access to project management routes based on their department.
    - Admins have full access
    - Developer department has access to tasks and assigned projects
    - Accounting department has access to sales and payment reports
    - Other departments have limited access
    """
    # Allow admins full access
    if current_user.is_admin:
        return None
    
    # Route-specific permissions
    endpoint = request.endpoint
    
    # Sales and payments section - only for accounting and admin
    if ('sales' in endpoint or 'payment' in endpoint) and current_user.department != 'accounting':
        flash('Access denied. You need accounting privileges to access this section.', 'danger')
        return redirect(url_for('project_management.dashboard'))
        
    # Project management endpoints - check developer access to their own projects
    if 'project_detail' in endpoint or 'edit_project' in endpoint:
        project_id = request.view_args.get('id')
        if project_id and current_user.department == 'developer':
            # Check if developer is assigned to any tasks in this project
            assigned_tasks = Task.query.filter_by(
                project_id=project_id, 
                user_id=current_user.id
            ).count()
            
            if assigned_tasks == 0:
                flash('Access denied. You are not assigned to this project.', 'danger')
                return redirect(url_for('project_management.dashboard'))

# Helper function to check and update milestone status when tasks are completed
def check_and_update_milestone_status(project_id):
    """
    Check if all tasks for a project are completed and update the milestone status accordingly
    """
    # Get all milestones for the project
    milestones = ProjectMilestone.query.filter_by(project_id=project_id).all()
    
    # For each milestone, check if tasks are completed
    for milestone in milestones:
        # Skip milestones that are already marked as paid
        if milestone.status == 'paid':
            continue
            
        # Get tasks related to this project
        project_tasks = Task.query.filter_by(project_id=project_id).all()
        
        # If there are no tasks, continue to the next milestone
        if not project_tasks:
            continue
            
        # Check if all tasks are completed
        all_tasks_completed = all(task.status == 'completed' for task in project_tasks)
        
        # If all tasks are completed and milestone is not yet completed, update its status
        if all_tasks_completed and milestone.status == 'pending':
            milestone.status = 'completed'
            db.session.add(milestone)
            
    # Commit changes if any
    db.session.commit()

@project_bp.route('/')
@project_bp.route('/dashboard')
@login_required
def dashboard():
    # Filter projects based on user department
    if current_user.is_admin or current_user.department == 'accounting':
        projects = Project.query.order_by(Project.start_date.desc()).limit(5).all()
    else:
        # Get projects where the user has assigned tasks
        assigned_project_ids = db.session.query(Task.project_id).filter_by(user_id=current_user.id).distinct().all()
        assigned_project_ids = [p[0] for p in assigned_project_ids]  # Convert to simple list
        projects = Project.query.filter(Project.id.in_(assigned_project_ids)).order_by(Project.start_date.desc()).limit(5).all()
    
    # Get tasks assigned to current user
    user_tasks = Task.query.filter_by(user_id=current_user.id).order_by(Task.due_date.asc()).limit(5).all()
    
    # Department-specific data
    department_data = {}
    user_department = current_user.department
    
    # Get project statistics - filtered for non-admin and non-accounting users
    if current_user.is_admin or current_user.department == 'accounting':
        total_projects = Project.query.count()
        completed_projects = Project.query.filter_by(status='completed').count()
        in_progress_projects = Project.query.filter_by(status='in-progress').count()
        planning_projects = Project.query.filter_by(status='planning').count()
        
        # Get task statistics
        total_tasks = Task.query.count()
        completed_tasks = Task.query.filter_by(status='completed').count()
        in_progress_tasks = Task.query.filter_by(status='in-progress').count()
        todo_tasks = Task.query.filter_by(status='to-do').count()
    else:
        # For regular users, only count projects they're assigned to
        assigned_project_ids = db.session.query(Task.project_id).filter_by(user_id=current_user.id).distinct().all()
        assigned_project_ids = [p[0] for p in assigned_project_ids]
        
        if assigned_project_ids:
            total_projects = Project.query.filter(Project.id.in_(assigned_project_ids)).count()
            completed_projects = Project.query.filter(Project.id.in_(assigned_project_ids), Project.status=='completed').count()
            in_progress_projects = Project.query.filter(Project.id.in_(assigned_project_ids), Project.status=='in-progress').count()
            planning_projects = Project.query.filter(Project.id.in_(assigned_project_ids), Project.status=='planning').count()
        else:
            total_projects = completed_projects = in_progress_projects = planning_projects = 0
        
        # Only count tasks assigned to the user
        total_tasks = Task.query.filter_by(user_id=current_user.id).count()
        completed_tasks = Task.query.filter_by(user_id=current_user.id, status='completed').count()
        in_progress_tasks = Task.query.filter_by(user_id=current_user.id, status='in-progress').count()
        todo_tasks = Task.query.filter_by(user_id=current_user.id, status='to-do').count()
    
    # HR Department specific data
    if user_department == 'hr' or current_user.is_admin:
        department_data['hr'] = {
            'total_employees': Employee.query.count(),
            'total_leaves': Leave.query.count(),
            'pending_leaves': Leave.query.filter_by(status='pending').count(),
            'recent_attendances': Attendance.query.order_by(Attendance.date.desc()).limit(5).all(),
            'attendance_today': Attendance.query.filter_by(date=datetime.now().date()).count(),
            'payrolls_pending': Payroll.query.filter_by(status='pending').count()
        }
    
    # Accounting Department specific data
    if user_department == 'accounting' or current_user.is_admin:
        department_data['accounting'] = {
            'total_sales': Sales.query.count(),
            'pending_payments': ProjectPayment.query.filter(
                ProjectPayment.status.in_(['pending', 'in-review'])
            ).count(),
            'total_revenue': db.session.query(func.sum(Sales.received_amount)).scalar() or 0,
            'outstanding_amount': db.session.query(func.sum(Sales.difference)).scalar() or 0
        }
    
    # Developer Department specific data
    if user_department == 'developer' or current_user.is_admin:
        department_data['developer'] = {
            'assigned_tasks': Task.query.filter_by(user_id=current_user.id).count(),
            'in_review_tasks': Task.query.filter_by(user_id=current_user.id, status='in-review').count(),
            'urgent_tasks': Task.query.filter_by(user_id=current_user.id, priority='urgent').count(),
            'productivity': completed_tasks / total_tasks * 100 if total_tasks > 0 else 0
        }
    
    # Personalized employee insights
    employee_insights = {}
    if current_user.employee:
        # Task completion rate for the current employee
        user_total_tasks = Task.query.filter_by(user_id=current_user.id).count()
        user_completed_tasks = Task.query.filter_by(user_id=current_user.id, status='completed').count()
        completion_rate = (user_completed_tasks / user_total_tasks * 100) if user_total_tasks > 0 else 0
        
        # Upcoming leave requests
        upcoming_leaves = Leave.query.filter_by(
            employee_id=current_user.employee.id, 
            status='approved'
        ).filter(Leave.start_date >= datetime.now().date()).order_by(Leave.start_date).limit(3).all()
        
        # Recent payrolls
        recent_payrolls = Payroll.query.filter_by(
            employee_id=current_user.employee.id
        ).order_by(Payroll.payment_date.desc()).limit(1).all()
        
        # Overdue tasks
        overdue_tasks = Task.query.filter_by(
            user_id=current_user.id
        ).filter(
            Task.due_date < datetime.now().date(),
            Task.status != 'completed'
        ).order_by(Task.due_date).all()
        
        # Days since hiring
        if current_user.employee.hire_date:
            days_employed = (datetime.now().date() - current_user.employee.hire_date).days
        else:
            days_employed = 0
        
        # Recent attendance records
        recent_attendance = Attendance.query.filter_by(
            employee_id=current_user.employee.id
        ).order_by(Attendance.date.desc()).limit(5).all()
        
        # Today's attendance
        today_attendance = Attendance.query.filter_by(
            employee_id=current_user.employee.id,
            date=datetime.now().date()
        ).first()
            
        employee_insights = {
            'completion_rate': round(completion_rate, 1),
            'upcoming_leaves': upcoming_leaves,
            'recent_payrolls': recent_payrolls,
            'overdue_tasks': overdue_tasks,
            'days_employed': days_employed,
            'user_total_tasks': user_total_tasks,
            'user_completed_tasks': user_completed_tasks,
            'recent_attendance': recent_attendance,
            'today_attendance': today_attendance
        }
    
    return render_template('project_management/dashboard.html',
                          projects=projects,
                          user_tasks=user_tasks,
                          total_projects=total_projects,
                          completed_projects=completed_projects,
                          in_progress_projects=in_progress_projects,
                          planning_projects=planning_projects,
                          total_tasks=total_tasks,
                          completed_tasks=completed_tasks,
                          in_progress_tasks=in_progress_tasks,
                          todo_tasks=todo_tasks,
                          employee_insights=employee_insights,
                          department_data=department_data)

@project_bp.route('/projects')
@login_required
def projects():
    # Admin can see all projects
    if current_user.is_admin:
        projects = Project.query.order_by(Project.start_date.desc()).all()
    # Accounting can see all projects for financial purposes
    elif current_user.department == 'accounting':
        projects = Project.query.order_by(Project.start_date.desc()).all()
    # All other users should only see projects they're assigned to
    else:
        # Find projects where the user has assigned tasks
        assigned_project_ids = db.session.query(Task.project_id).filter_by(user_id=current_user.id).distinct().all()
        assigned_project_ids = [p[0] for p in assigned_project_ids]  # Convert to simple list
        
        if assigned_project_ids:
            projects = Project.query.filter(Project.id.in_(assigned_project_ids)).order_by(Project.start_date.desc()).all()
        else:
            # If user has no assigned projects, show empty list
            projects = []
        
    return render_template('project_management/projects.html', projects=projects)

@project_bp.route('/clients')
@login_required
def clients():
    clients = ClientUser.query.all()
    return render_template('project_management/clients.html', clients=clients)

@project_bp.route('/clients/new', methods=['GET', 'POST'])
@login_required
def new_client():
    form = ClientUserForm()
    
    # Populate existing user choices
    form.existing_user_id.choices = [(0, '-- Select User --')] + [(u.id, u.username) for u in User.query.all()]
    
    if form.validate_on_submit():
        client = ClientUser(
            name=form.name.data,
            email=form.email.data,
            platform=form.platform.data,
            platform_username=form.platform_username.data,
            is_existing_user=form.is_existing_user.data
        )
        
        if form.is_existing_user.data and form.existing_user_id.data > 0:
            client.existing_user_id = form.existing_user_id.data
            
        db.session.add(client)
        db.session.commit()
        
        flash('Client created successfully!', 'success')
        return redirect(url_for('project_management.clients'))
        
    return render_template('project_management/client_form.html', form=form, title='New Client')

@project_bp.route('/clients/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_client(id):
    client = ClientUser.query.get_or_404(id)
    form = ClientUserForm(obj=client)
    
    # Populate existing user choices
    form.existing_user_id.choices = [(0, '-- Select User --')] + [(u.id, u.username) for u in User.query.all()]
    
    if form.validate_on_submit():
        form.populate_obj(client)
        db.session.commit()
        
        flash('Client updated successfully!', 'success')
        return redirect(url_for('project_management.clients'))
        
    return render_template('project_management/client_form.html', form=form, client=client, title='Edit Client')

@project_bp.route('/clients/<int:id>/delete', methods=['POST'])
@login_required
def delete_client(id):
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('project_management.clients'))
        
    client = ClientUser.query.get_or_404(id)
    
    # Check if client has projects
    if client.projects:
        flash('Cannot delete client with associated projects.', 'danger')
        return redirect(url_for('project_management.clients'))
        
    db.session.delete(client)
    db.session.commit()
    
    flash('Client deleted successfully!', 'success')
    return redirect(url_for('project_management.clients'))

@project_bp.route('/projects/new', methods=['GET', 'POST'])
@login_required
def new_project():
    form = ProjectForm()
    
    # Populate client user choices
    form.client_user_id.choices = [(0, '-- Select Client --')] + [(c.id, c.name) for c in ClientUser.query.all()]
    
    if form.validate_on_submit():
        project = Project(
            name=form.name.data,
            description=form.description.data,
            client=form.client.data,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            status=form.status.data,
            budget=form.budget.data,
            platform=form.platform.data,
            platform_project_id=form.platform_project_id.data,
            payment_status=form.payment_status.data
        )
        
        if form.client_user_id.data and form.client_user_id.data > 0:
            project.client_user_id = form.client_user_id.data
            
        db.session.add(project)
        db.session.commit()
        
        # Create a Sales record for this project
        if project.budget:
            sale = Sales(
                project_id=project.id,
                total_amount=project.budget,
                received_amount=0,
                currency='USD',
                status='open',
                difference=project.budget  # Initially, difference is the full budget
            )
            db.session.add(sale)
            db.session.commit()
            
            # Create accounting journal entry for new project (if accounting module is enabled)
            try:
                from blueprints.accounting.routes import create_journal_entry
                from models_accounting import ChartOfAccount
                
                # Find appropriate accounts
                revenue_account = ChartOfAccount.query.filter_by(name='Sales Revenue').first()
                ar_account = ChartOfAccount.query.filter_by(name='Accounts Receivable').first()
                
                if revenue_account and ar_account:
                    # Prepare line items
                    line_items = [
                        # Debit Accounts Receivable
                        {
                            'account_id': ar_account.id,
                            'debit_amount': float(project.budget),
                            'credit_amount': 0,
                            'description': f'Project {project.name} - Expected Revenue'
                        },
                        # Credit Revenue
                        {
                            'account_id': revenue_account.id,
                            'debit_amount': 0,
                            'credit_amount': float(project.budget),
                            'description': f'Project {project.name} - Expected Revenue'
                        }
                    ]
                    
                    # Create journal entry
                    create_journal_entry(
                        entry_type='PROJECT',
                        transaction_date=project.start_date,
                        reference=f'PRJ-{project.id}',
                        memo=f'New project: {project.name}',
                        line_items=line_items,
                        user_id=current_user.id
                    )
            except Exception as e:
                # Log error but don't prevent project creation if accounting fails
                print(f"Error creating accounting entry for project: {str(e)}")
        
        flash('Project created successfully!', 'success')
        return redirect(url_for('project_management.project_detail', id=project.id))
    
    return render_template('project_management/project_form.html', form=form, title='New Project')

@project_bp.route('/projects/<int:id>')
@login_required
def project_detail(id):
    project = Project.query.get_or_404(id)
    
    # Check if user has access to this project
    is_admin_or_accounting = current_user.is_admin or current_user.department == 'accounting'
    has_task_in_project = Task.query.filter_by(project_id=id, user_id=current_user.id).first() is not None
    
    # Only allow access if user is admin/accounting or has a task in this project
    if not is_admin_or_accounting and not has_task_in_project:
        flash('Access denied. You can only view projects you are assigned to.', 'danger')
        return redirect(url_for('project_management.projects'))
    
    # For regular users, only show tasks assigned to them
    if not is_admin_or_accounting and current_user.department == 'developer':
        tasks = Task.query.filter_by(project_id=id, user_id=current_user.id).order_by(Task.due_date.asc()).all()
    else:
        tasks = Task.query.filter_by(project_id=id).order_by(Task.due_date.asc()).all()
        
    return render_template('project_management/project_detail.html', project=project, tasks=tasks)

@project_bp.route('/projects/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_project(id):
    project = Project.query.get_or_404(id)
    form = ProjectForm(obj=project)
    
    # Populate client user choices
    form.client_user_id.choices = [(0, '-- Select Client --')] + [(c.id, c.name) for c in ClientUser.query.all()]
    
    if form.validate_on_submit():
        form.populate_obj(project)
        
        # Handle 0 value in client_user_id (optional field)
        if form.client_user_id.data == 0:
            project.client_user_id = None
            
        db.session.commit()
        
        flash('Project updated successfully!', 'success')
        return redirect(url_for('project_management.project_detail', id=project.id))
    
    return render_template('project_management/project_form.html', form=form, project=project, title='Edit Project')

@project_bp.route('/projects/<int:id>/delete', methods=['POST'])
@login_required
def delete_project(id):
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('project_management.projects'))
    
    project = Project.query.get_or_404(id)
    db.session.delete(project)
    db.session.commit()
    
    flash('Project deleted successfully!', 'success')
    return redirect(url_for('project_management.projects'))

@project_bp.route('/projects/export')
@login_required
def export_projects():
    projects = Project.query.all()
    headers = ['ID', 'Name', 'Client', 'Start Date', 'End Date', 'Status', 'Progress', 'Budget']
    
    data = []
    for proj in projects:
        data.append({
            'ID': proj.id,
            'Name': proj.name,
            'Client': proj.client,
            'Start Date': proj.start_date.strftime('%Y-%m-%d'),
            'End Date': proj.end_date.strftime('%Y-%m-%d') if proj.end_date else 'N/A',
            'Status': proj.status,
            'Progress': f"{proj.progress}%",
            'Budget': f"${proj.budget}" if proj.budget else 'N/A'
        })
    
    return generate_csv(data, 'projects')

@project_bp.route('/projects/<int:id>/report')
@login_required
def project_report(id):
    project = Project.query.get_or_404(id)
    tasks = Task.query.filter_by(project_id=id).order_by(Task.due_date.asc()).all()
    
    return generate_pdf(
        'project_management/project_report.html', 
        f'project_report_{project.id}',
        project=project,
        tasks=tasks
    )

@project_bp.route('/tasks')
@login_required
def tasks():
    if current_user.is_admin:
        tasks = Task.query.order_by(Task.due_date.asc()).all()
    else:
        tasks = Task.query.filter_by(user_id=current_user.id).order_by(Task.due_date.asc()).all()
    
    return render_template('project_management/tasks.html', tasks=tasks)

@project_bp.route('/projects/<int:project_id>/tasks/new', methods=['GET', 'POST'])
@login_required
def new_task(project_id):
    project = Project.query.get_or_404(project_id)
    form = TaskForm()
    
    # Populate user choices
    form.user_id.choices = [(u.id, u.username) for u in User.query.all()]
    
    # Populate milestone choices
    milestones = ProjectMilestone.query.filter_by(project_id=project_id).all()
    form.milestone_id.choices = [(0, '-- No Milestone --')] + [(m.id, m.name) for m in milestones]
    
    if form.validate_on_submit():
        task = Task(
            project_id=project.id,
            user_id=form.user_id.data,
            milestone_id=form.milestone_id.data if form.milestone_id.data > 0 else None,
            title=form.title.data,
            description=form.description.data,
            due_date=form.due_date.data,
            priority=form.priority.data,
            status=form.status.data
        )
        db.session.add(task)
        db.session.commit()
        
        flash('Task created successfully!', 'success')
        return redirect(url_for('project_management.project_detail', id=project.id))
    
    return render_template('project_management/task_form.html', form=form, project=project, title='New Task')

@project_bp.route('/tasks/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_task(id):
    task = Task.query.get_or_404(id)
    
    if not current_user.is_admin and task.user_id != current_user.id:
        flash('Access denied. You can only edit tasks assigned to you.', 'danger')
        return redirect(url_for('project_management.tasks'))
    
    form = TaskForm(obj=task)
    form.user_id.choices = [(u.id, u.username) for u in User.query.all()]
    
    # Populate milestone choices
    milestones = ProjectMilestone.query.filter_by(project_id=task.project_id).all()
    form.milestone_id.choices = [(0, '-- No Milestone --')] + [(m.id, m.name) for m in milestones]
    
    old_status = task.status
    
    if form.validate_on_submit():
        # Handle milestone_id specifically
        if form.milestone_id.data == 0:
            task.milestone_id = None
        else:
            task.milestone_id = form.milestone_id.data
            
        # Update other fields
        task.user_id = form.user_id.data
        task.title = form.title.data
        task.description = form.description.data
        task.due_date = form.due_date.data
        task.priority = form.priority.data
        task.status = form.status.data
        
        db.session.commit()
        
        # If task status changed to completed, check and update milestone status
        if old_status != 'completed' and task.status == 'completed':
            check_and_update_milestone_status(task.project_id)
            flash('Task updated and marked as completed! Milestone status has been updated if all tasks are completed.', 'success')
        else:
            flash('Task updated successfully!', 'success')
            
        return redirect(url_for('project_management.project_detail', id=task.project_id))
    
    return render_template('project_management/task_form.html', form=form, task=task, project=task.project, title='Edit Task')

@project_bp.route('/tasks/<int:id>/delete', methods=['POST'])
@login_required
def delete_task(id):
    task = Task.query.get_or_404(id)
    
    if not current_user.is_admin and task.user_id != current_user.id:
        flash('Access denied. You can only delete tasks assigned to you.', 'danger')
        return redirect(url_for('project_management.tasks'))
    
    project_id = task.project_id
    db.session.delete(task)
    db.session.commit()
    
    flash('Task deleted successfully!', 'success')
    return redirect(url_for('project_management.project_detail', id=project_id))

@project_bp.route('/tasks/<int:id>/status/<string:status>', methods=['POST'])
@login_required
def update_task_status(id, status):
    task = Task.query.get_or_404(id)
    
    if not current_user.is_admin and task.user_id != current_user.id:
        flash('Access denied. You can only update tasks assigned to you.', 'danger')
        return redirect(url_for('project_management.tasks'))
    
    valid_statuses = ['to-do', 'in-progress', 'in-review', 'completed']
    if status not in valid_statuses:
        flash('Invalid status.', 'danger')
        return redirect(url_for('project_management.tasks'))
    
    task.status = status
    db.session.commit()
    
    # If task is marked as completed, check if all project tasks are completed
    # and update milestone status accordingly
    if status == 'completed':
        check_and_update_milestone_status(task.project_id)
        flash('Task marked as completed! Milestone status has been updated if all tasks are completed.', 'success')
    else:
        flash(f'Task status updated to {status}.', 'success')
    
    referrer = request.referrer
    if referrer:
        return redirect(referrer)
    else:
        return redirect(url_for('project_management.tasks'))

# Project Milestones
@project_bp.route('/projects/<int:project_id>/milestones')
@login_required
def project_milestones(project_id):
    project = Project.query.get_or_404(project_id)
    
    # Check if user has access to this project
    is_admin_or_accounting = current_user.is_admin or current_user.department == 'accounting'
    has_task_in_project = Task.query.filter_by(project_id=project_id, user_id=current_user.id).first() is not None
    
    # Only allow access if user is admin/accounting or has a task in this project
    if not is_admin_or_accounting and not has_task_in_project:
        flash('Access denied. You can only view milestones for projects you are assigned to.', 'danger')
        return redirect(url_for('project_management.projects'))
    
    milestones = ProjectMilestone.query.filter_by(project_id=project_id).order_by(ProjectMilestone.due_date.asc()).all()
    return render_template('project_management/milestones.html', project=project, milestones=milestones)

@project_bp.route('/projects/<int:project_id>/milestones/new', methods=['GET', 'POST'])
@login_required
def new_milestone(project_id):
    project = Project.query.get_or_404(project_id)
    form = ProjectMilestoneForm()
    
    if form.validate_on_submit():
        milestone = ProjectMilestone(
            project_id=project_id,
            name=form.name.data,
            description=form.description.data,
            due_date=form.due_date.data,
            amount=form.amount.data,
            status=form.status.data
        )
        db.session.add(milestone)
        db.session.commit()
        
        flash('Project milestone created successfully!', 'success')
        return redirect(url_for('project_management.project_milestones', project_id=project_id))
    
    return render_template('project_management/milestone_form.html', form=form, project=project, title='New Milestone')

@project_bp.route('/milestones/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_milestone(id):
    milestone = ProjectMilestone.query.get_or_404(id)
    project_id = milestone.project_id
    
    # Check if user has access to this project
    is_admin_or_accounting = current_user.is_admin or current_user.department == 'accounting'
    has_task_in_project = Task.query.filter_by(project_id=project_id, user_id=current_user.id).first() is not None
    
    # Only allow access if user is admin/accounting or has a task in this project
    if not is_admin_or_accounting and not has_task_in_project:
        flash('Access denied. You can only edit milestones for projects you are assigned to.', 'danger')
        return redirect(url_for('project_management.projects'))
    
    form = ProjectMilestoneForm(obj=milestone)
    
    if form.validate_on_submit():
        form.populate_obj(milestone)
        db.session.commit()
        
        flash('Milestone updated successfully!', 'success')
        return redirect(url_for('project_management.project_milestones', project_id=milestone.project_id))
    
    return render_template('project_management/milestone_form.html', form=form, milestone=milestone, project=milestone.project, title='Edit Milestone')

@project_bp.route('/milestones/<int:id>/delete', methods=['POST'])
@login_required
def delete_milestone(id):
    milestone = ProjectMilestone.query.get_or_404(id)
    project_id = milestone.project_id
    
    # Check if the milestone has payments attached
    if milestone.payment:
        flash('Cannot delete milestone with associated payments.', 'danger')
        return redirect(url_for('project_management.project_milestones', project_id=project_id))
    
    db.session.delete(milestone)
    db.session.commit()
    
    flash('Milestone deleted successfully!', 'success')
    return redirect(url_for('project_management.project_milestones', project_id=project_id))

# Account Management
@project_bp.route('/accounts')
@login_required
def accounts():
    accounts = Account.query.all()
    return render_template('project_management/accounts.html', accounts=accounts)

@project_bp.route('/accounts/new', methods=['GET', 'POST'])
@login_required
def new_account():
    form = AccountForm()
    
    if form.validate_on_submit():
        account = Account(
            name=form.name.data,
            account_type=form.account_type.data,
            currency=form.currency.data,
            description=form.description.data
        )
        db.session.add(account)
        db.session.commit()
        
        flash('Account created successfully!', 'success')
        return redirect(url_for('project_management.accounts'))
    
    return render_template('project_management/account_form.html', form=form, title='New Account')

@project_bp.route('/accounts/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_account(id):
    account = Account.query.get_or_404(id)
    form = AccountForm(obj=account)
    
    if form.validate_on_submit():
        form.populate_obj(account)
        db.session.commit()
        
        flash('Account updated successfully!', 'success')
        return redirect(url_for('project_management.accounts'))
    
    return render_template('project_management/account_form.html', form=form, account=account, title='Edit Account')

@project_bp.route('/accounts/<int:id>/delete', methods=['POST'])
@login_required
def delete_account(id):
    account = Account.query.get_or_404(id)
    
    # Check if the account has payments attached
    if account.project_payments:
        flash('Cannot delete account with associated payments.', 'danger')
        return redirect(url_for('project_management.accounts'))
    
    db.session.delete(account)
    db.session.commit()
    
    flash('Account deleted successfully!', 'success')
    return redirect(url_for('project_management.accounts'))

# Payment Management
@project_bp.route('/payments')
@login_required
def payments():
    payments = ProjectPayment.query.order_by(ProjectPayment.payment_date.desc()).all()
    return render_template('project_management/payments.html', payments=payments)

@project_bp.route('/projects/<int:project_id>/payments')
@login_required
def project_payments(project_id):
    project = Project.query.get_or_404(project_id)
    
    # Check if user has access to this project
    is_admin_or_accounting = current_user.is_admin or current_user.department == 'accounting'
    has_task_in_project = Task.query.filter_by(project_id=project_id, user_id=current_user.id).first() is not None
    
    # Only allow access if user is admin/accounting or has a task in this project
    if not is_admin_or_accounting and not has_task_in_project:
        flash('Access denied. You can only view payments for projects you are assigned to.', 'danger')
        return redirect(url_for('project_management.projects'))
    
    payments = ProjectPayment.query.filter_by(project_id=project_id).order_by(ProjectPayment.payment_date.desc()).all()
    return render_template('project_management/project_payments.html', project=project, payments=payments)

@project_bp.route('/payments/new', methods=['GET', 'POST'])
@login_required
def new_payment():
    form = ProjectPaymentForm()
    
    # Populate dropdown choices
    form.project_id.choices = [(p.id, p.name) for p in Project.query.all()]
    form.milestone_id.choices = [(0, '-- Select Milestone --')] 
    form.account_id.choices = [(0, '-- Select Account --')] + [(a.id, a.name) for a in Account.query.all()]
    
    if form.project_id.data:
        milestones = ProjectMilestone.query.filter_by(project_id=form.project_id.data).all()
        form.milestone_id.choices += [(m.id, m.name) for m in milestones]
    
    if form.validate_on_submit():
        payment = ProjectPayment(
            project_id=form.project_id.data,
            amount_original=form.amount_original.data,
            currency_original=form.currency_original.data,
            platform_fee=form.platform_fee.data,
            conversion_fee=form.conversion_fee.data,
            conversion_rate=form.conversion_rate.data,
            status=form.status.data,
            notes=form.notes.data
        )
        
        if form.milestone_id.data > 0:
            payment.milestone_id = form.milestone_id.data
            
        if form.account_id.data > 0:
            payment.account_id = form.account_id.data
            
        if form.payment_date.data:
            payment.payment_date = form.payment_date.data
            
        if form.amount_received.data:
            payment.amount_received = form.amount_received.data
            payment.currency_received = form.currency_received.data
        
        db.session.add(payment)
        db.session.commit()
        
        # Update project payment status if this is transferred
        if payment.status == 'transferred' or payment.status == 'reconciled':
            project = Project.query.get(payment.project_id)
            project.payment_status = 'transferred'
            
            # Update the sales record for this project using the model method
            if payment.amount_received:
                payment.update_project_sales()
                
                # Create accounting journal entry for payment (if accounting module is enabled)
                try:
                    from blueprints.accounting.routes import create_journal_entry
                    from models_accounting import ChartOfAccount
                    
                    # Find appropriate accounts
                    cash_account = ChartOfAccount.query.filter_by(name='Cash').first()
                    ar_account = ChartOfAccount.query.filter_by(name='Accounts Receivable').first()
                    
                    if cash_account and ar_account:
                        # Prepare line items
                        line_items = [
                            # Debit Cash
                            {
                                'account_id': cash_account.id,
                                'debit_amount': float(payment.amount_received),
                                'credit_amount': 0,
                                'description': f'Payment received for project {project.name}'
                            },
                            # Credit Accounts Receivable
                            {
                                'account_id': ar_account.id,
                                'debit_amount': 0,
                                'credit_amount': float(payment.amount_received),
                                'description': f'Payment received for project {project.name}'
                            }
                        ]
                        
                        # Create journal entry
                        create_journal_entry(
                            entry_type='PAYMENT',
                            transaction_date=payment.payment_date or datetime.now().date(),
                            reference=f'PMT-{payment.id}',
                            memo=f'Payment for project: {project.name}',
                            line_items=line_items,
                            user_id=current_user.id
                        )
                except Exception as e:
                    # Log error but don't prevent payment creation if accounting fails
                    print(f"Error creating accounting entry for payment: {str(e)}")
            
            db.session.commit()
        
        flash('Payment record created successfully!', 'success')
        return redirect(url_for('project_management.project_payments', project_id=payment.project_id))
    
    return render_template('project_management/payment_form.html', form=form, title='New Payment')

@project_bp.route('/payments/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_payment(id):
    payment = ProjectPayment.query.get_or_404(id)
    form = ProjectPaymentForm(obj=payment)
    
    # Populate dropdown choices
    form.project_id.choices = [(p.id, p.name) for p in Project.query.all()]
    milestones = ProjectMilestone.query.filter_by(project_id=payment.project_id).all()
    form.milestone_id.choices = [(0, '-- Select Milestone --')] + [(m.id, m.name) for m in milestones]
    form.account_id.choices = [(0, '-- Select Account --')] + [(a.id, a.name) for a in Account.query.all()]
    
    if form.validate_on_submit():
        old_status = payment.status
        form.populate_obj(payment)
        
        # Calculate amount received if missing
        if not payment.amount_received and payment.amount_original and payment.conversion_rate:
            amt_after_platform_fee = payment.amount_original - payment.platform_fee
            payment.amount_received = (amt_after_platform_fee * payment.conversion_rate) - payment.conversion_fee
        
        db.session.commit()
        
        # Update project payment status if status changed to transferred or reconciled
        if old_status != payment.status and (payment.status == 'transferred' or payment.status == 'reconciled'):
            project = Project.query.get(payment.project_id)
            project.payment_status = 'transferred'
            
            # Update the sales record if this is a new transferred payment
            if payment.amount_received and not payment.is_recorded_in_sales:
                # Use the model method to update sales record
                payment.update_project_sales()
                
                # Create accounting journal entry for payment (if accounting module is enabled)
                try:
                    from blueprints.accounting.routes import create_journal_entry
                    from models_accounting import ChartOfAccount
                    
                    # Find appropriate accounts
                    cash_account = ChartOfAccount.query.filter_by(name='Cash').first()
                    ar_account = ChartOfAccount.query.filter_by(name='Accounts Receivable').first()
                    
                    if cash_account and ar_account:
                        # Prepare line items
                        line_items = [
                            # Debit Cash
                            {
                                'account_id': cash_account.id,
                                'debit_amount': float(payment.amount_received),
                                'credit_amount': 0,
                                'description': f'Payment received for project {project.name}'
                            },
                            # Credit Accounts Receivable
                            {
                                'account_id': ar_account.id,
                                'debit_amount': 0,
                                'credit_amount': float(payment.amount_received),
                                'description': f'Payment received for project {project.name}'
                            }
                        ]
                        
                        # Create journal entry
                        create_journal_entry(
                            entry_type='PAYMENT',
                            transaction_date=payment.payment_date or datetime.now().date(),
                            reference=f'PMT-{payment.id}',
                            memo=f'Payment for project: {project.name}',
                            line_items=line_items,
                            user_id=current_user.id
                        )
                except Exception as e:
                    # Log error but don't prevent payment update if accounting fails
                    print(f"Error creating accounting entry for edited payment: {str(e)}")
            
            db.session.commit()
        
        flash('Payment updated successfully!', 'success')
        return redirect(url_for('project_management.project_payments', project_id=payment.project_id))
    
    return render_template('project_management/payment_form.html', form=form, payment=payment, title='Edit Payment')

@project_bp.route('/payments/<int:id>/delete', methods=['POST'])
@login_required
def delete_payment(id):
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('project_management.payments'))
    
    payment = ProjectPayment.query.get_or_404(id)
    project_id = payment.project_id
    
    # Update the sales record if this payment was recorded in sales
    if payment.is_recorded_in_sales and payment.amount_received:
        # Instead of directly modifying the sales record, we'll utilize a special method
        # First, mark the payment as not recorded so we can reverse the effect
        original_amount = payment.amount_received
        payment.is_recorded_in_sales = False
        
        # Get the sales record
        sale = Sales.query.filter_by(project_id=project_id).first()
        if sale:
            # Manually deduct the amount since we're deleting the payment
            sale.received_amount -= original_amount
            sale.calculate_difference()
            
            # Create reversing journal entry for the deleted payment
            try:
                from blueprints.accounting.routes import create_journal_entry
                from models_accounting import ChartOfAccount
                
                # Find appropriate accounts
                cash_account = ChartOfAccount.query.filter_by(name='Cash').first()
                ar_account = ChartOfAccount.query.filter_by(name='Accounts Receivable').first()
                
                if cash_account and ar_account:
                    # Prepare line items - note the reversed debits/credits
                    line_items = [
                        # Credit Cash (reverse the debit)
                        {
                            'account_id': cash_account.id,
                            'debit_amount': 0,
                            'credit_amount': float(payment.amount_received),
                            'description': f'Reversal of payment for project {payment.project.name}'
                        },
                        # Debit Accounts Receivable (reverse the credit)
                        {
                            'account_id': ar_account.id,
                            'debit_amount': float(payment.amount_received),
                            'credit_amount': 0,
                            'description': f'Reversal of payment for project {payment.project.name}'
                        }
                    ]
                    
                    # Create reversal journal entry
                    create_journal_entry(
                        entry_type='REVERSAL',
                        transaction_date=date.today(),
                        reference=f'REV-PMT-{payment.id}',
                        memo=f'Reversal of deleted payment for project: {payment.project.name}',
                        line_items=line_items,
                        user_id=current_user.id
                    )
            except Exception as e:
                # Log error but don't prevent payment deletion if accounting fails
                print(f"Error creating reversal accounting entry for deleted payment: {str(e)}")
                
            db.session.commit()  # Save the sales update first
    
    db.session.delete(payment)
    db.session.commit()
    
    flash('Payment deleted successfully!', 'success')
    return redirect(url_for('project_management.project_payments', project_id=project_id))

# Sales Management Routes
@project_bp.route('/sales')
@login_required
def sales():
    """List all sales records"""
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('project_management.dashboard'))
        
    sales_records = Sales.query.order_by(Sales.created_at.desc()).all()
    return render_template('project_management/sales.html', sales=sales_records, title='Sales Records')

@project_bp.route('/sales/<int:id>')
@login_required
def sales_detail(id):
    """View sales record details"""
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('project_management.dashboard'))
        
    sale = Sales.query.get_or_404(id)
    # Get all payments associated with this project
    payments = ProjectPayment.query.filter_by(project_id=sale.project_id).all()
    return render_template('project_management/sales_detail.html', sale=sale, payments=payments, title='Sales Details')

@project_bp.route('/sales/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_sales(id):
    """Edit a sales record"""
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('project_management.dashboard'))
        
    sale = Sales.query.get_or_404(id)
    form = SalesForm(obj=sale)
    
    # Populate project choices - limit to this project only for editing
    form.project_id.choices = [(sale.project_id, sale.project.name)]
    
    if form.validate_on_submit():
        old_status = sale.status
        form.populate_obj(sale)
        
        # If status changed to closed, set the closed date
        if old_status != 'closed' and sale.status == 'closed':
            from datetime import date
            sale.closed_date = date.today()
            
        # Recalculate difference
        sale.calculate_difference()
        
        db.session.commit()
        flash('Sales record updated successfully!', 'success')
        return redirect(url_for('project_management.sales_detail', id=sale.id))
    
    return render_template('project_management/sales_form.html', form=form, sale=sale, title='Edit Sales Record')

@project_bp.route('/sales/<int:id>/close', methods=['POST'])
@login_required
def close_sales(id):
    """Force close a sales record"""
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('project_management.dashboard'))
        
    sale = Sales.query.get_or_404(id)
    
    if sale.status == 'closed':
        flash('Sales record is already closed.', 'info')
        return redirect(url_for('project_management.sales_detail', id=sale.id))
    
    from datetime import date
    sale.status = 'closed'
    sale.closed_date = date.today()
    sale.calculate_difference()
    
    db.session.commit()
    
    # Create accounting journal entry for closing sales with a difference (write-off)
    if sale.difference > 0:
        try:
            from blueprints.accounting.routes import create_journal_entry
            from models_accounting import ChartOfAccount
            
            # Find appropriate accounts
            ar_account = ChartOfAccount.query.filter_by(name='Accounts Receivable').first()
            revenue_account = ChartOfAccount.query.filter_by(name='Sales Revenue').first()
            
            if ar_account and revenue_account:
                # Prepare line items for writing off the difference
                line_items = [
                    # Credit Accounts Receivable (reduce AR)
                    {
                        'account_id': ar_account.id,
                        'debit_amount': 0,
                        'credit_amount': float(sale.difference),
                        'description': f'Write-off for closed project: {sale.project.name}'
                    },
                    # Debit Revenue (reduce revenue)
                    {
                        'account_id': revenue_account.id,
                        'debit_amount': float(sale.difference),
                        'credit_amount': 0,
                        'description': f'Write-off for closed project: {sale.project.name}'
                    }
                ]
                
                # Create journal entry
                create_journal_entry(
                    entry_type='WRITEOFF',
                    transaction_date=sale.closed_date,
                    reference=f'CLO-{sale.id}',
                    memo=f'Write-off on closing sales for project: {sale.project.name}',
                    line_items=line_items,
                    user_id=current_user.id
                )
        except Exception as e:
            # Log error but don't prevent sales closure if accounting fails
            print(f"Error creating accounting entry for sales closure: {str(e)}")
    
    flash('Sales record has been closed successfully!', 'success')
    return redirect(url_for('project_management.sales_detail', id=sale.id))

@project_bp.route('/project/<int:project_id>/sales')
@login_required
def project_sales(project_id):
    """View sales for a specific project"""
    project = Project.query.get_or_404(project_id)
    sale = Sales.query.filter_by(project_id=project_id).first()
    
    if not sale:
        flash('No sales record found for this project.', 'warning')
        return redirect(url_for('project_management.project_detail', id=project_id))
    
    # Get all payments associated with this project
    payments = ProjectPayment.query.filter_by(project_id=project_id).all()
    
    return render_template('project_management/sales_detail.html', sale=sale, payments=payments, project=project, title='Project Sales')

@project_bp.route('/api/projects/<int:project_id>/milestones', methods=['GET'])
@login_required
def api_project_milestones(project_id):
    """API endpoint to get milestones for a project"""
    milestones = ProjectMilestone.query.filter_by(project_id=project_id).all()
    result = [{'id': m.id, 'name': m.name} for m in milestones]
    return jsonify(result)
