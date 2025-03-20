from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime
from app import db
from models_accounting import ChartOfAccount, FiscalYear, AccountingPeriod, JournalEntry, JournalEntryLine
from models_accounting import Currency, ExchangeRate, Tax, Vendor, VendorInvoice, VendorPayment
from models_accounting import Customer, CustomerInvoice, CustomerPayment, BankAccount, BankReconciliation, BankTransaction
from utils import generate_csv, generate_pdf, format_currency
from . import accounting_bp
from .forms import ChartOfAccountForm, FiscalYearForm, AccountingPeriodForm, JournalEntryForm, JournalEntryLineForm
from .forms import CurrencyForm, ExchangeRateForm, TaxForm, VendorForm, VendorInvoiceForm, VendorPaymentForm
from .forms import CustomerForm, CustomerInvoiceForm, CustomerPaymentForm, BankAccountForm, BankReconciliationForm, BankTransactionForm

# Check if user is admin - decorator
def check_admin():
    if not current_user.is_admin:
        flash('You must be an administrator to access this page.', 'danger')
        return redirect(url_for('project_management.dashboard'))

# Chart of Accounts
@accounting_bp.route('/chart-of-accounts')
@login_required
def chart_of_accounts():
    """List all accounts in the chart of accounts"""
    accounts = ChartOfAccount.query.order_by(ChartOfAccount.code).all()
    
    # Group by account type
    account_groups = {}
    for account in accounts:
        if account.account_type not in account_groups:
            account_groups[account.account_type] = []
        account_groups[account.account_type].append(account)
    
    return render_template('accounting/chart_of_accounts.html', 
                          account_groups=account_groups, 
                          title='Chart of Accounts')

@accounting_bp.route('/chart-of-accounts/new', methods=['GET', 'POST'])
@login_required
def new_account():
    """Create a new account in the chart of accounts"""
    check_admin()
    
    form = ChartOfAccountForm()
    
    # Populate parent account choices
    parent_choices = [(0, '-- No Parent --')]
    accounts = ChartOfAccount.query.order_by(ChartOfAccount.code).all()
    for account in accounts:
        parent_choices.append((account.id, f"{account.code} - {account.name}"))
    form.parent_id.choices = parent_choices
    
    if form.validate_on_submit():
        account = ChartOfAccount(
            code=form.code.data,
            name=form.name.data,
            account_type=form.account_type.data,
            parent_id=form.parent_id.data if form.parent_id.data != 0 else None,
            description=form.description.data,
            is_active=form.is_active.data,
            normal_balance=form.normal_balance.data
        )
        
        db.session.add(account)
        db.session.commit()
        
        flash(f'Account {account.code} - {account.name} has been created.', 'success')
        return redirect(url_for('accounting.chart_of_accounts'))
    
    return render_template('accounting/account_form.html', 
                          form=form,
                          title='New Account')

@accounting_bp.route('/chart-of-accounts/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_account(id):
    """Edit an account in the chart of accounts"""
    check_admin()
    
    account = ChartOfAccount.query.get_or_404(id)
    form = ChartOfAccountForm(obj=account)
    
    # Populate parent account choices
    parent_choices = [(0, '-- No Parent --')]
    accounts = ChartOfAccount.query.filter(ChartOfAccount.id != id).order_by(ChartOfAccount.code).all()
    for acct in accounts:
        parent_choices.append((acct.id, f"{acct.code} - {acct.name}"))
    form.parent_id.choices = parent_choices
    
    if form.validate_on_submit():
        account.code = form.code.data
        account.name = form.name.data
        account.account_type = form.account_type.data
        account.parent_id = form.parent_id.data if form.parent_id.data != 0 else None
        account.description = form.description.data
        account.is_active = form.is_active.data
        account.normal_balance = form.normal_balance.data
        
        db.session.commit()
        
        flash(f'Account {account.code} - {account.name} has been updated.', 'success')
        return redirect(url_for('accounting.chart_of_accounts'))
    
    # Set default value for parent_id
    if account.parent_id:
        form.parent_id.data = account.parent_id
    else:
        form.parent_id.data = 0
    
    return render_template('accounting/account_form.html', 
                          form=form,
                          title='Edit Account')

@accounting_bp.route('/chart-of-accounts/<int:id>/delete', methods=['POST'])
@login_required
def delete_account(id):
    """Delete an account from the chart of accounts"""
    check_admin()
    
    account = ChartOfAccount.query.get_or_404(id)
    
    # Check if account has children
    if account.children:
        flash('Cannot delete an account with child accounts.', 'danger')
        return redirect(url_for('accounting.chart_of_accounts'))
    
    # Check if account has journal entries
    if account.journal_entry_lines:
        flash('Cannot delete an account with journal entries.', 'danger')
        return redirect(url_for('accounting.chart_of_accounts'))
    
    db.session.delete(account)
    db.session.commit()
    
    flash(f'Account {account.code} - {account.name} has been deleted.', 'success')
    return redirect(url_for('accounting.chart_of_accounts'))

# Fiscal Years and Accounting Periods
@accounting_bp.route('/fiscal-years')
@login_required
def fiscal_years():
    """List all fiscal years"""
    check_admin()
    
    years = FiscalYear.query.order_by(FiscalYear.start_date.desc()).all()
    return render_template('accounting/fiscal_years.html', 
                          years=years, 
                          title='Fiscal Years')

@accounting_bp.route('/fiscal-years/new', methods=['GET', 'POST'])
@login_required
def new_fiscal_year():
    """Create a new fiscal year"""
    check_admin()
    
    form = FiscalYearForm()
    
    if form.validate_on_submit():
        year = FiscalYear(
            name=form.name.data,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            is_closed=form.is_closed.data
        )
        
        db.session.add(year)
        db.session.commit()
        
        flash(f'Fiscal Year {year.name} has been created.', 'success')
        return redirect(url_for('accounting.fiscal_years'))
    
    return render_template('accounting/fiscal_year_form.html', 
                          form=form,
                          title='New Fiscal Year')

@accounting_bp.route('/fiscal-years/<int:id>/periods')
@login_required
def accounting_periods(id):
    """List all accounting periods for a fiscal year"""
    check_admin()
    
    year = FiscalYear.query.get_or_404(id)
    periods = AccountingPeriod.query.filter_by(fiscal_year_id=id).order_by(AccountingPeriod.start_date).all()
    
    return render_template('accounting/accounting_periods.html', 
                          year=year, 
                          periods=periods, 
                          title='Accounting Periods')

@accounting_bp.route('/fiscal-years/<int:year_id>/periods/new', methods=['GET', 'POST'])
@login_required
def new_accounting_period(year_id):
    """Create a new accounting period"""
    check_admin()
    
    year = FiscalYear.query.get_or_404(year_id)
    form = AccountingPeriodForm()
    
    # Set fiscal year
    form.fiscal_year_id.choices = [(year.id, year.name)]
    form.fiscal_year_id.data = year.id
    
    if form.validate_on_submit():
        period = AccountingPeriod(
            fiscal_year_id=year.id,
            name=form.name.data,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            is_closed=form.is_closed.data
        )
        
        db.session.add(period)
        db.session.commit()
        
        flash(f'Accounting Period {period.name} has been created.', 'success')
        return redirect(url_for('accounting.accounting_periods', id=year.id))
    
    return render_template('accounting/accounting_period_form.html', 
                          form=form,
                          year=year,
                          title='New Accounting Period')

# Journal Entries
@accounting_bp.route('/journal-entries')
@login_required
def journal_entries():
    """List all journal entries"""
    check_admin()
    
    entries = JournalEntry.query.order_by(JournalEntry.date.desc()).all()
    return render_template('accounting/journal_entries.html', 
                          entries=entries, 
                          title='Journal Entries')

@accounting_bp.route('/journal-entries/new', methods=['GET', 'POST'])
@login_required
def new_journal_entry():
    """Create a new journal entry"""
    check_admin()
    
    form = JournalEntryForm()
    
    # Populate accounting period choices
    periods = AccountingPeriod.query.filter_by(is_closed=False).order_by(AccountingPeriod.start_date.desc()).all()
    period_choices = [(period.id, f"{period.name} ({period.start_date.strftime('%Y-%m-%d')} to {period.end_date.strftime('%Y-%m-%d')})") for period in periods]
    form.period_id.choices = period_choices
    
    if form.validate_on_submit():
        # Generate a unique entry number
        last_entry = JournalEntry.query.order_by(JournalEntry.id.desc()).first()
        entry_number = f"JE-{datetime.now().strftime('%Y%m')}-{(last_entry.id + 1 if last_entry else 1):04d}"
        
        entry = JournalEntry(
            entry_number=entry_number if not form.entry_number.data else form.entry_number.data,
            date=form.date.data,
            period_id=form.period_id.data,
            memo=form.memo.data,
            reference=form.reference.data,
            status=form.status.data,
            entry_type=form.entry_type.data,
            created_by=current_user.id
        )
        
        db.session.add(entry)
        db.session.commit()
        
        flash(f'Journal Entry {entry.entry_number} has been created.', 'success')
        return redirect(url_for('accounting.edit_journal_entry_lines', id=entry.id))
    
    return render_template('accounting/journal_entry_form.html', 
                          form=form,
                          title='New Journal Entry')

@accounting_bp.route('/journal-entries/<int:id>/lines', methods=['GET', 'POST'])
@login_required
def edit_journal_entry_lines(id):
    """Edit lines for a journal entry"""
    check_admin()
    
    entry = JournalEntry.query.get_or_404(id)
    form = JournalEntryLineForm()
    
    # Populate account choices
    accounts = ChartOfAccount.query.filter_by(is_active=True).order_by(ChartOfAccount.code).all()
    form.account_id.choices = [(account.id, f"{account.code} - {account.name}") for account in accounts]
    
    if form.validate_on_submit():
        line = JournalEntryLine(
            journal_entry_id=entry.id,
            account_id=form.account_id.data,
            description=form.description.data,
            debit_amount=form.debit_amount.data,
            credit_amount=form.credit_amount.data
        )
        
        db.session.add(line)
        db.session.commit()
        
        flash('Journal entry line added.', 'success')
        return redirect(url_for('accounting.edit_journal_entry_lines', id=entry.id))
    
    return render_template('accounting/journal_entry_lines.html', 
                          entry=entry,
                          form=form,
                          title='Edit Journal Entry Lines')

@accounting_bp.route('/journal-entries/<int:id>/lines/<int:line_id>/delete', methods=['POST'])
@login_required
def delete_journal_entry_line(id, line_id):
    """Delete a journal entry line"""
    check_admin()
    
    line = JournalEntryLine.query.get_or_404(line_id)
    
    if line.journal_entry_id != id:
        flash('Invalid journal entry line.', 'danger')
        return redirect(url_for('accounting.edit_journal_entry_lines', id=id))
    
    db.session.delete(line)
    db.session.commit()
    
    flash('Journal entry line deleted.', 'success')
    return redirect(url_for('accounting.edit_journal_entry_lines', id=id))

@accounting_bp.route('/journal-entries/<int:id>/post', methods=['POST'])
@login_required
def post_journal_entry(id):
    """Post a journal entry"""
    check_admin()
    
    entry = JournalEntry.query.get_or_404(id)
    
    if entry.status != 'DRAFT':
        flash('Only draft journal entries can be posted.', 'danger')
        return redirect(url_for('accounting.edit_journal_entry_lines', id=id))
    
    if not entry.is_balanced:
        flash('Journal entry must be balanced before posting.', 'danger')
        return redirect(url_for('accounting.edit_journal_entry_lines', id=id))
    
    entry.status = 'POSTED'
    db.session.commit()
    
    flash(f'Journal Entry {entry.entry_number} has been posted.', 'success')
    return redirect(url_for('accounting.journal_entries'))