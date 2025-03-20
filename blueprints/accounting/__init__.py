from flask import Blueprint, redirect, url_for, flash
from flask_login import current_user, login_required

accounting_bp = Blueprint('accounting', __name__, url_prefix='/accounting')

@accounting_bp.before_request
@login_required
def restrict_accounting_access():
    """Restrict access to accounting routes to admins and accounting department"""
    if not current_user.is_admin and current_user.department != 'accounting':
        flash('Access denied. Only accounting staff can access this section.', 'danger')
        return redirect(url_for('project_management.dashboard'))

from . import routes, forms