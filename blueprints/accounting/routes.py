from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime, date
from app import db
from models_accounting import ChartOfAccount, FiscalYear, AccountingPeriod, JournalEntry, JournalEntryLine
from models_accounting import Currency, ExchangeRate, Tax, Vendor, VendorInvoice, VendorPayment
from models_accounting import Customer, CustomerInvoice, CustomerPayment, BankAccount, BankReconciliation, BankTransaction
from models_accounting import AccountType, DebitCredit
from utils import generate_csv, generate_pdf, format_currency
from . import accounting_bp
from .forms import ChartOfAccountForm, FiscalYearForm, AccountingPeriodForm, JournalEntryForm, JournalEntryLineForm
from .forms import CurrencyForm, ExchangeRateForm, TaxForm, VendorForm, VendorInvoiceForm, VendorPaymentForm
from .forms import CustomerForm, CustomerInvoiceForm, CustomerPaymentForm, BankAccountForm, BankReconciliationForm, BankTransactionForm

# Initialize default accounting data
def initialize_accounting():
    """Initialize default accounting data if not exists"""
    # Check if chart of accounts exists
    if ChartOfAccount.query.count() == 0:
        # Default chart of accounts
        default_accounts = [
            # Asset accounts
            {'code': '1000', 'name': 'Cash', 'account_type': 'Asset', 'normal_balance': 'DEBIT', 'parent_id': None},
            {'code': '1100', 'name': 'Accounts Receivable', 'account_type': 'Asset', 'normal_balance': 'DEBIT', 'parent_id': None},
            {'code': '1200', 'name': 'Bank Accounts', 'account_type': 'Asset', 'normal_balance': 'DEBIT', 'parent_id': None},
            {'code': '1300', 'name': 'Inventory', 'account_type': 'Asset', 'normal_balance': 'DEBIT', 'parent_id': None},
            
            # Liability accounts
            {'code': '2000', 'name': 'Accounts Payable', 'account_type': 'Liability', 'normal_balance': 'CREDIT', 'parent_id': None},
            {'code': '2100', 'name': 'Accrued Liabilities', 'account_type': 'Liability', 'normal_balance': 'CREDIT', 'parent_id': None},
            {'code': '2200', 'name': 'Taxes Payable', 'account_type': 'Liability', 'normal_balance': 'CREDIT', 'parent_id': None},
            
            # Equity accounts
            {'code': '3000', 'name': 'Owner\'s Equity', 'account_type': 'Equity', 'normal_balance': 'CREDIT', 'parent_id': None},
            {'code': '3100', 'name': 'Retained Earnings', 'account_type': 'Equity', 'normal_balance': 'CREDIT', 'parent_id': None},
            
            # Revenue accounts
            {'code': '4000', 'name': 'Sales Revenue', 'account_type': 'Revenue', 'normal_balance': 'CREDIT', 'parent_id': None},
            {'code': '4100', 'name': 'Service Revenue', 'account_type': 'Revenue', 'normal_balance': 'CREDIT', 'parent_id': None},
            {'code': '4200', 'name': 'Interest Income', 'account_type': 'Revenue', 'normal_balance': 'CREDIT', 'parent_id': None},
            
            # Expense accounts
            {'code': '5000', 'name': 'Cost of Goods Sold', 'account_type': 'Expense', 'normal_balance': 'DEBIT', 'parent_id': None},
            {'code': '5100', 'name': 'Salaries and Wages', 'account_type': 'Expense', 'normal_balance': 'DEBIT', 'parent_id': None},
            {'code': '5200', 'name': 'Rent Expense', 'account_type': 'Expense', 'normal_balance': 'DEBIT', 'parent_id': None},
            {'code': '5300', 'name': 'Utilities Expense', 'account_type': 'Expense', 'normal_balance': 'DEBIT', 'parent_id': None},
            {'code': '5400', 'name': 'Office Supplies', 'account_type': 'Expense', 'normal_balance': 'DEBIT', 'parent_id': None},
        ]
        
        for account_data in default_accounts:
            account = ChartOfAccount(
                code=account_data['code'],
                name=account_data['name'],
                account_type=account_data['account_type'],
                normal_balance=account_data['normal_balance'],
                is_active=True,
                description=f"Default {account_data['account_type']} account"
            )
            db.session.add(account)
        
        db.session.commit()
    
    # Check if fiscal year exists
    if FiscalYear.query.count() == 0:
        # Create current fiscal year
        current_year = datetime.now().year
        fiscal_year = FiscalYear(
            name=f"FY {current_year}",
            start_date=date(current_year, 1, 1),
            end_date=date(current_year, 12, 31),
            is_closed=False
        )
        db.session.add(fiscal_year)
        db.session.commit()
        
        # Create quarterly periods
        periods = [
            {'name': f"Q1 {current_year}", 'start_date': date(current_year, 1, 1), 'end_date': date(current_year, 3, 31)},
            {'name': f"Q2 {current_year}", 'start_date': date(current_year, 4, 1), 'end_date': date(current_year, 6, 30)},
            {'name': f"Q3 {current_year}", 'start_date': date(current_year, 7, 1), 'end_date': date(current_year, 9, 30)},
            {'name': f"Q4 {current_year}", 'start_date': date(current_year, 10, 1), 'end_date': date(current_year, 12, 31)},
        ]
        
        for period_data in periods:
            period = AccountingPeriod(
                fiscal_year_id=fiscal_year.id,
                name=period_data['name'],
                start_date=period_data['start_date'],
                end_date=period_data['end_date'],
                is_closed=False
            )
            db.session.add(period)
        
        db.session.commit()
    
    # Check if currencies exist
    if Currency.query.count() == 0:
        # Default currencies
        currencies = [
            {'code': 'USD', 'name': 'US Dollar', 'symbol': '$', 'is_base': True},
            {'code': 'EUR', 'name': 'Euro', 'symbol': '€', 'is_base': False},
            {'code': 'GBP', 'name': 'British Pound', 'symbol': '£', 'is_base': False},
        ]
        
        for currency_data in currencies:
            currency = Currency(
                code=currency_data['code'],
                name=currency_data['name'],
                symbol=currency_data['symbol'],
                is_base=currency_data['is_base'],
                is_active=True
            )
            db.session.add(currency)
        
        db.session.commit()

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
    # Initialize accounting data if not exists
    initialize_accounting()
    
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
    
    # Initialize accounting data if not exists
    initialize_accounting()
    
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
    
    # Initialize accounting data if not exists
    initialize_accounting()
    
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
        # Generate a unique entry number - add timestamp to ensure uniqueness
        now = datetime.now()
        timestamp = now.strftime('%Y%m%d%H%M%S')
        
        if form.entry_number.data:
            # Check if user-provided entry number is unique
            existing = JournalEntry.query.filter_by(entry_number=form.entry_number.data).first()
            if existing:
                form.entry_number.errors = list(form.entry_number.errors) if form.entry_number.errors else []
                form.entry_number.errors.append('This entry number already exists. Please use a unique value.')
                return render_template('accounting/journal_entry_form.html', form=form, title='New Journal Entry')
            entry_number = form.entry_number.data
        else:
            # Generate a unique entry number with random suffix to avoid collisions
            import random
            random_suffix = random.randint(1000, 9999)
            entry_number = f"JE-{now.strftime('%Y%m')}-{timestamp[-4:]}-{random_suffix}"
        
        entry = JournalEntry(
            entry_number=entry_number,
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
        
        flash(f'Journal Entry {entry.entry_number} has been created. Please add line items below.', 'success')
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

@accounting_bp.route('/journal-entries/<int:id>/post', methods=['GET', 'POST'])
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

@accounting_bp.route('/general-ledger', methods=['GET'])
@login_required
def general_ledger():
    """General Ledger - View all financial transactions"""
    # Check if user is admin
    if not current_user.is_admin:
        flash('Access denied. You need admin privileges to view the general ledger.', 'danger')
        return redirect(url_for('accounts.login'))
    
    # Get all accounts for the filter dropdown
    accounts = ChartOfAccount.query.order_by(ChartOfAccount.code).all()
    
    # Get filter parameters
    account_id = request.args.get('account_id', type=int)
    from_date_str = request.args.get('from_date')
    to_date_str = request.args.get('to_date')
    entry_type = request.args.get('entry_type')
    
    # Convert date strings to date objects
    from_date = None
    to_date = None
    if from_date_str:
        try:
            from_date = datetime.strptime(from_date_str, '%Y-%m-%d').date()
        except ValueError:
            pass
    
    if to_date_str:
        try:
            to_date = datetime.strptime(to_date_str, '%Y-%m-%d').date()
        except ValueError:
            pass
    
    # Base query for journal entry lines with joins
    query = db.session.query(
        JournalEntryLine, 
        JournalEntry, 
        ChartOfAccount
    ).join(
        JournalEntry, 
        JournalEntryLine.journal_entry_id == JournalEntry.id
    ).join(
        ChartOfAccount, 
        JournalEntryLine.account_id == ChartOfAccount.id
    )
    
    # Apply filters
    if account_id:
        query = query.filter(JournalEntryLine.account_id == account_id)
    
    if from_date:
        query = query.filter(JournalEntry.date >= from_date)
    
    if to_date:
        query = query.filter(JournalEntry.date <= to_date)
    
    if entry_type:
        query = query.filter(JournalEntry.entry_type == entry_type)
    
    # Order by account, then date
    results = query.order_by(
        ChartOfAccount.code,
        JournalEntry.date,
        JournalEntry.id
    ).all()
    
    # Entry types for filter dropdown
    entry_types = [
        ('MANUAL', 'Manual'),
        ('SYSTEM', 'System'),
        ('RECURRING', 'Recurring')
    ]
    
    return render_template(
        'accounting/general_ledger.html',
        title='General Ledger',
        accounts=accounts,
        results=results,
        entry_types=entry_types,
        selected_account_id=account_id,
        selected_from_date=from_date,
        selected_to_date=to_date,
        selected_entry_type=entry_type
    )

# Financial Statements Routes

@accounting_bp.route('/balance_sheet', methods=['GET'])
@login_required
def balance_sheet():
    """Display the balance sheet"""
    as_of_date_str = request.args.get('as_of_date')
    as_of_date = None
    
    if as_of_date_str:
        try:
            as_of_date = datetime.strptime(as_of_date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid date format. Using current date.', 'warning')
            as_of_date = date.today()
    else:
        as_of_date = date.today()
    
    # Get asset accounts
    asset_accounts = ChartOfAccount.query.filter_by(
        account_type='Asset', 
        is_active=True
    ).order_by(ChartOfAccount.code).all()
    
    # Get liability accounts
    liability_accounts = ChartOfAccount.query.filter_by(
        account_type='Liability', 
        is_active=True
    ).order_by(ChartOfAccount.code).all()
    
    # Get equity accounts
    equity_accounts = ChartOfAccount.query.filter_by(
        account_type='Equity', 
        is_active=True
    ).order_by(ChartOfAccount.code).all()
    
    # Calculate account balances as of the specified date
    for account in asset_accounts + liability_accounts + equity_accounts:
        # Get journal entry lines for this account up to the specified date
        query = JournalEntryLine.query.join(
            JournalEntry, 
            JournalEntryLine.journal_entry_id == JournalEntry.id
        ).filter(
            JournalEntryLine.account_id == account.id,
            JournalEntry.date <= as_of_date,
            JournalEntry.status == 'POSTED'  # Only consider posted entries
        )
        
        # Calculate debits and credits
        debits = sum(line.debit_amount for line in query.all())
        credits = sum(line.credit_amount for line in query.all())
        
        # Calculate balance based on normal balance type
        if account.normal_balance == 'DEBIT':
            account.balance_amount = debits - credits
        else:  # CREDIT
            account.balance_amount = credits - debits
    
    # Calculate totals
    total_assets = sum(account.balance_amount for account in asset_accounts)
    total_liabilities = sum(account.balance_amount for account in liability_accounts)
    total_equity = sum(account.balance_amount for account in equity_accounts)
    total_liabilities_equity = total_liabilities + total_equity
    
    return render_template(
        'accounting/balance_sheet.html',
        title='Balance Sheet',
        as_of_date=as_of_date,
        asset_accounts=asset_accounts,
        liability_accounts=liability_accounts,
        equity_accounts=equity_accounts,
        total_assets=total_assets,
        total_liabilities=total_liabilities,
        total_equity=total_equity,
        total_liabilities_equity=total_liabilities_equity
    )

@accounting_bp.route('/income_statement', methods=['GET'])
@login_required
def income_statement():
    """Display the income statement (profit and loss)"""
    from_date_str = request.args.get('from_date')
    to_date_str = request.args.get('to_date')
    from_date = None
    to_date = None
    
    if from_date_str:
        try:
            from_date = datetime.strptime(from_date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid from date format.', 'warning')
            from_date = date.today().replace(day=1)  # First day of current month
    else:
        from_date = date.today().replace(day=1)  # First day of current month
    
    if to_date_str:
        try:
            to_date = datetime.strptime(to_date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid to date format.', 'warning')
            to_date = date.today()
    else:
        to_date = date.today()
    
    # Get revenue accounts
    revenue_accounts = ChartOfAccount.query.filter_by(
        account_type='Revenue', 
        is_active=True
    ).order_by(ChartOfAccount.code).all()
    
    # Get expense accounts
    expense_accounts = ChartOfAccount.query.filter_by(
        account_type='Expense', 
        is_active=True
    ).order_by(ChartOfAccount.code).all()
    
    # Calculate account balances for the specified period
    for account in revenue_accounts + expense_accounts:
        # Get journal entry lines for this account within the specified period
        query = JournalEntryLine.query.join(
            JournalEntry, 
            JournalEntryLine.journal_entry_id == JournalEntry.id
        ).filter(
            JournalEntryLine.account_id == account.id,
            JournalEntry.date >= from_date,
            JournalEntry.date <= to_date,
            JournalEntry.status == 'POSTED'  # Only consider posted entries
        )
        
        # Calculate debits and credits
        debits = sum(line.debit_amount for line in query.all())
        credits = sum(line.credit_amount for line in query.all())
        
        # Calculate balance based on normal balance type
        if account.normal_balance == 'DEBIT':
            account.balance_amount = debits - credits
        else:  # CREDIT
            account.balance_amount = credits - debits
    
    # Calculate totals
    total_revenue = sum(account.balance_amount for account in revenue_accounts)
    total_expenses = sum(account.balance_amount for account in expense_accounts)
    net_income = total_revenue - total_expenses
    
    return render_template(
        'accounting/income_statement.html',
        title='Income Statement',
        from_date=from_date,
        to_date=to_date,
        revenue_accounts=revenue_accounts,
        expense_accounts=expense_accounts,
        total_revenue=total_revenue,
        total_expenses=total_expenses,
        net_income=net_income
    )

@accounting_bp.route('/trial_balance', methods=['GET'])
@login_required
def trial_balance():
    """Display the trial balance"""
    as_of_date_str = request.args.get('as_of_date')
    as_of_date = None
    
    if as_of_date_str:
        try:
            as_of_date = datetime.strptime(as_of_date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid date format. Using current date.', 'warning')
            as_of_date = date.today()
    else:
        as_of_date = date.today()
    
    # Get all active accounts
    accounts = ChartOfAccount.query.filter_by(
        is_active=True
    ).order_by(ChartOfAccount.code).all()
    
    accounts_with_balances = []
    total_debits = Decimal('0.00')
    total_credits = Decimal('0.00')
    
    # Calculate account balances as of the specified date
    for account in accounts:
        # Get journal entry lines for this account up to the specified date
        query = JournalEntryLine.query.join(
            JournalEntry, 
            JournalEntryLine.journal_entry_id == JournalEntry.id
        ).filter(
            JournalEntryLine.account_id == account.id,
            JournalEntry.date <= as_of_date,
            JournalEntry.status == 'POSTED'  # Only consider posted entries
        )
        
        # Calculate debits and credits
        debits = sum(line.debit_amount for line in query.all())
        credits = sum(line.credit_amount for line in query.all())
        
        # Only include accounts with non-zero balances
        if debits > 0 or credits > 0:
            # Determine debit or credit balance
            if debits > credits:
                debit_balance = debits - credits
                credit_balance = Decimal('0.00')
                total_debits += debit_balance
            else:
                debit_balance = Decimal('0.00')
                credit_balance = credits - debits
                total_credits += credit_balance
            
            accounts_with_balances.append({
                'account': account,
                'debit_balance': debit_balance,
                'credit_balance': credit_balance
            })
    
    return render_template(
        'accounting/trial_balance.html',
        title='Trial Balance',
        as_of_date=as_of_date,
        accounts=accounts_with_balances,
        total_debits=total_debits,
        total_credits=total_credits
    )