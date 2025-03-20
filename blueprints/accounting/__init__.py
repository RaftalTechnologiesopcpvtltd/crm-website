from flask import Blueprint

accounting_bp = Blueprint('accounting', __name__, url_prefix='/accounting',
                         template_folder='templates')

from . import routes