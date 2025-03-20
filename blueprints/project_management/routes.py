from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from models import Project, Task, User, Employee, ClientUser, ProjectMilestone, ProjectPayment, Account, Sales
from blueprints.project_management.forms import (
    ProjectForm, TaskForm, ClientUserForm, ProjectMilestoneForm, 
    ProjectPaymentForm, AccountForm, SalesForm
)
from utils import generate_csv, generate_pdf
from decimal import Decimal
from sqlalchemy import func

project_bp = Blueprint('project_management', __name__, url_prefix='')

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
    projects = Project.query.order_by(Project.start_date.desc()).limit(5).all()
    
    # Get tasks assigned to current user
    user_tasks = Task.query.filter_by(user_id=current_user.id).order_by(Task.due_date.asc()).limit(5).all()
    
    # Get project statistics
    total_projects = Project.query.count()
    completed_projects = Project.query.filter_by(status='completed').count()
    in_progress_projects = Project.query.filter_by(status='in-progress').count()
    planning_projects = Project.query.filter_by(status='planning').count()
    
    # Get task statistics
    total_tasks = Task.query.count()
    completed_tasks = Task.query.filter_by(status='completed').count()
    in_progress_tasks = Task.query.filter_by(status='in-progress').count()
    todo_tasks = Task.query.filter_by(status='to-do').count()
    
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
                          todo_tasks=todo_tasks)

@project_bp.route('/projects')
@login_required
def projects():
    projects = Project.query.order_by(Project.start_date.desc()).all()
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
        
        flash('Project created successfully!', 'success')
        return redirect(url_for('project_management.project_detail', id=project.id))
    
    return render_template('project_management/project_form.html', form=form, title='New Project')

@project_bp.route('/projects/<int:id>')
@login_required
def project_detail(id):
    project = Project.query.get_or_404(id)
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
            
            # Update the sales record for this project
            if payment.amount_received:
                # Get the sales record for this project
                sale = Sales.query.filter_by(project_id=project.id).first()
                if sale:
                    sale.received_amount += payment.amount_received
                    sale.calculate_difference()
                    payment.is_recorded_in_sales = True
            
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
                # Get the sales record for this project
                sale = Sales.query.filter_by(project_id=project.id).first()
                if sale:
                    sale.received_amount += payment.amount_received
                    sale.calculate_difference()
                    payment.is_recorded_in_sales = True
            
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
        sale = Sales.query.filter_by(project_id=project_id).first()
        if sale:
            sale.received_amount -= payment.amount_received
            sale.calculate_difference()
            db.session.commit()  # Save the sales update first
    
    db.session.delete(payment)
    db.session.commit()
    
    flash('Payment deleted successfully!', 'success')
    return redirect(url_for('project_management.project_payments', project_id=project_id))
