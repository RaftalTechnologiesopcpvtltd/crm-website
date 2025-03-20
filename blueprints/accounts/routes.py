from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash
from wtforms import BooleanField
from app import db
from models import User
from blueprints.accounts.forms import LoginForm, RegistrationForm, ProfileForm

accounts_bp = Blueprint('accounts', __name__, url_prefix='/accounts')

@accounts_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('project_management.dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            next_page = request.args.get('next')
            flash('Login successful!', 'success')
            return redirect(next_page or url_for('project_management.dashboard'))
        else:
            flash('Invalid username or password', 'danger')
    
    return render_template('accounts/login.html', form=form)

@accounts_bp.route('/add_user', methods=['GET', 'POST'])
@login_required
def add_user():
    # Only admin users can add new users
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('project_management.dashboard'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data,
            is_admin=form.is_admin.data if hasattr(form, 'is_admin') else False
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        
        flash('User added successfully!', 'success')
        return redirect(url_for('accounts.user_list'))
    
    return render_template('accounts/register.html', form=form, admin_view=True)

@accounts_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('accounts.login'))

@accounts_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = ProfileForm(obj=current_user)
    
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.email = form.email.data
        
        if form.new_password.data:
            current_user.password_hash = generate_password_hash(form.new_password.data)
        
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('accounts.profile'))
    
    return render_template('accounts/profile.html', form=form)

@accounts_bp.route('/users')
@login_required
def user_list():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('project_management.dashboard'))
    
    users = User.query.all()
    return render_template('accounts/user_list.html', users=users)

@accounts_bp.route('/edit_user/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_user(id):
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('project_management.dashboard'))
    
    user = User.query.get_or_404(id)
    form = ProfileForm(obj=user)
    
    # Add admin field to the form
    form.is_admin = BooleanField('Admin Privileges', default=user.is_admin)
    
    if form.validate_on_submit():
        user.username = form.username.data
        user.email = form.email.data
        user.is_admin = form.is_admin.data if hasattr(form, 'is_admin') else user.is_admin
        
        if form.new_password.data:
            user.password_hash = generate_password_hash(form.new_password.data)
        
        db.session.commit()
        flash('User updated successfully!', 'success')
        return redirect(url_for('accounts.user_list'))
    
    return render_template('accounts/profile.html', form=form, user=user, admin_view=True)

@accounts_bp.route('/delete_user/<int:id>')
@login_required
def delete_user(id):
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('project_management.dashboard'))
    
    user = User.query.get_or_404(id)
    
    # Prevent deleting yourself
    if user.id == current_user.id:
        flash('You cannot delete your own account.', 'danger')
        return redirect(url_for('accounts.user_list'))
    
    # Check if user has any related records before deletion
    if hasattr(user, 'employee') and user.employee:
        flash('Cannot delete user with employee records. Remove employee record first.', 'danger')
        return redirect(url_for('accounts.user_list'))
    
    if hasattr(user, 'tasks') and user.tasks:
        flash('Cannot delete user with assigned tasks. Reassign tasks first.', 'danger')
        return redirect(url_for('accounts.user_list'))
    
    db.session.delete(user)
    db.session.commit()
    flash('User deleted successfully!', 'success')
    return redirect(url_for('accounts.user_list'))
