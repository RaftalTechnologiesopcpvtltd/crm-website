from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash
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

@accounts_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('project_management.dashboard'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for('accounts.login'))
    
    return render_template('accounts/register.html', form=form)

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
