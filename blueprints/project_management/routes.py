from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from models import Project, Task, User, Employee
from blueprints.project_management.forms import ProjectForm, TaskForm
from utils import generate_csv, generate_pdf

project_bp = Blueprint('project_management', __name__, url_prefix='')

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

@project_bp.route('/projects/new', methods=['GET', 'POST'])
@login_required
def new_project():
    form = ProjectForm()
    
    if form.validate_on_submit():
        project = Project(
            name=form.name.data,
            description=form.description.data,
            client=form.client.data,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            status=form.status.data,
            budget=form.budget.data
        )
        db.session.add(project)
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
    
    if form.validate_on_submit():
        form.populate_obj(project)
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
    
    if form.validate_on_submit():
        task = Task(
            project_id=project.id,
            user_id=form.user_id.data,
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
    
    if form.validate_on_submit():
        form.populate_obj(task)
        db.session.commit()
        
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
    
    flash(f'Task status updated to {status}.', 'success')
    
    referrer = request.referrer
    if referrer:
        return redirect(referrer)
    else:
        return redirect(url_for('project_management.tasks'))
