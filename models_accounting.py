from app import db
from datetime import datetime
from decimal import Decimal
from enum import Enum
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy import func, text
from models import User

class AccountType(Enum):
    ASSET = 'Asset'
    LIABILITY = 'Liability'
    EQUITY = 'Equity'
    REVENUE = 'Revenue'
    EXPENSE = 'Expense'
    
    @classmethod
    def choices(cls):
        return [(choice.name, choice.value) for choice in cls]
    
    @classmethod
    def coerce(cls, item):
        return item if isinstance(item, AccountType) else AccountType[item]

class DebitCredit(Enum):
    DEBIT = 'Debit'
    CREDIT = 'Credit'
    
    @classmethod
    def choices(cls):
        return [(choice.name, choice.value) for choice in cls]

class ChartOfAccount(db.Model):
    """Chart of Accounts model"""
    __tablename__ = 'chart_of_account'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    account_type = db.Column(db.String(20), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('chart_of_account.id'), nullable=True)
    description = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    normal_balance = db.Column(db.String(10), nullable=False, default='DEBIT')  # DEBIT or CREDIT
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    parent = db.relationship('ChartOfAccount', remote_side=[id], backref='children')
    journal_entry_lines = db.relationship('JournalEntryLine', backref='chart_account', lazy=True)
    
    def __repr__(self):
        return f"{self.code} - {self.name}"
    
    @property
    def balance(self):
        """Calculate the current balance of the account"""
        debit_sum = db.session.query(func.sum(JournalEntryLine.debit_amount)).filter(
            JournalEntryLine.account_id == self.id
        ).scalar() or Decimal('0.00')
        
        credit_sum = db.session.query(func.sum(JournalEntryLine.credit_amount)).filter(
            JournalEntryLine.account_id == self.id
        ).scalar() or Decimal('0.00')
        
        if self.normal_balance == 'DEBIT':
            return debit_sum - credit_sum
        else:
            return credit_sum - debit_sum
    
    @property
    def has_children(self):
        """Check if the account has child accounts"""
        return len(self.children) > 0
    
    @property
    def display_balance(self):
        """Format balance for display with currency symbol"""
        return f"${abs(self.balance):,.2f}"
    
    @property
    def is_debit_balance(self):
        """Return True if account has a debit balance"""
        if self.normal_balance == 'DEBIT':
            return self.balance >= 0
        else:
            return self.balance < 0


class FiscalYear(db.Model):
    """Fiscal Year model for accounting periods"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    is_closed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    periods = db.relationship('AccountingPeriod', backref='fiscal_year', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f"{self.name} ({self.start_date} to {self.end_date})"


class AccountingPeriod(db.Model):
    """Accounting periods within a fiscal year"""
    id = db.Column(db.Integer, primary_key=True)
    fiscal_year_id = db.Column(db.Integer, db.ForeignKey('fiscal_year.id'), nullable=False)
    name = db.Column(db.String(50), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    is_closed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    journal_entries = db.relationship('JournalEntry', backref='period', lazy=True)
    
    def __repr__(self):
        return f"{self.name} ({self.start_date} to {self.end_date})"


class JournalEntry(db.Model):
    """Journal Entry header"""
    id = db.Column(db.Integer, primary_key=True)
    entry_number = db.Column(db.String(20), unique=True, nullable=False)
    date = db.Column(db.Date, nullable=False)
    period_id = db.Column(db.Integer, db.ForeignKey('accounting_period.id'), nullable=False)
    memo = db.Column(db.Text, nullable=True)
    reference = db.Column(db.String(100), nullable=True)
    status = db.Column(db.String(20), default='DRAFT')  # DRAFT, POSTED, REVERSED
    entry_type = db.Column(db.String(20), default='MANUAL')  # MANUAL, SYSTEM, RECURRING
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    lines = db.relationship('JournalEntryLine', backref='journal_entry', lazy=True, cascade='all, delete-orphan')
    user = db.relationship('User', backref='journal_entries')
    
    def __repr__(self):
        return f"Journal Entry #{self.entry_number}"
    
    @property
    def total_debits(self):
        """Calculate the total debits"""
        return sum(line.debit_amount for line in self.lines)
    
    @property
    def total_credits(self):
        """Calculate the total credits"""
        return sum(line.credit_amount for line in self.lines)
    
    @property
    def is_balanced(self):
        """Check if the journal entry is balanced"""
        return self.total_debits == self.total_credits


class JournalEntryLine(db.Model):
    """Journal Entry line items"""
    id = db.Column(db.Integer, primary_key=True)
    journal_entry_id = db.Column(db.Integer, db.ForeignKey('journal_entry.id'), nullable=False)
    account_id = db.Column(db.Integer, db.ForeignKey('chart_of_account.id'), nullable=False)
    description = db.Column(db.Text, nullable=True)
    debit_amount = db.Column(db.Numeric(10, 2), default=0)
    credit_amount = db.Column(db.Numeric(10, 2), default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"{self.chart_account.code} - {'Debit' if self.debit_amount > 0 else 'Credit'} {abs(self.debit_amount if self.debit_amount > 0 else self.credit_amount)}"


class Currency(db.Model):
    """Currency for multi-currency support"""
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(3), unique=True, nullable=False)
    name = db.Column(db.String(50), nullable=False)
    symbol = db.Column(db.String(5), nullable=False)
    is_base = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"{self.code} ({self.name})"


class ExchangeRate(db.Model):
    """Exchange rates for currency conversion"""
    id = db.Column(db.Integer, primary_key=True)
    from_currency_id = db.Column(db.Integer, db.ForeignKey('currency.id'), nullable=False)
    to_currency_id = db.Column(db.Integer, db.ForeignKey('currency.id'), nullable=False)
    rate = db.Column(db.Numeric(10, 6), nullable=False)
    date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    from_currency = db.relationship('Currency', foreign_keys=[from_currency_id])
    to_currency = db.relationship('Currency', foreign_keys=[to_currency_id])
    
    def __repr__(self):
        return f"{self.from_currency.code} to {self.to_currency.code}: {self.rate} ({self.date})"


class Tax(db.Model):
    """Tax types and rates"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    rate = db.Column(db.Numeric(5, 2), nullable=False)
    tax_type = db.Column(db.String(20), nullable=False)  # VAT, GST, SALES TAX, etc.
    description = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    account_id = db.Column(db.Integer, db.ForeignKey('chart_of_account.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    account = db.relationship('ChartOfAccount')
    
    def __repr__(self):
        return f"{self.name} ({self.rate}%)"


class Vendor(db.Model):
    """Vendors for accounts payable"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    vendor_number = db.Column(db.String(20), unique=True, nullable=False)
    contact_name = db.Column(db.String(100), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    address = db.Column(db.Text, nullable=True)
    payment_terms = db.Column(db.String(50), nullable=True)  # NET30, NET60, etc.
    account_id = db.Column(db.Integer, db.ForeignKey('chart_of_account.id'), nullable=False)  # AP account
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    account = db.relationship('ChartOfAccount')
    invoices = db.relationship('VendorInvoice', backref='vendor', lazy=True)
    
    def __repr__(self):
        return f"{self.name} ({self.vendor_number})"


class VendorInvoice(db.Model):
    """Vendor invoices for accounts payable"""
    id = db.Column(db.Integer, primary_key=True)
    vendor_id = db.Column(db.Integer, db.ForeignKey('vendor.id'), nullable=False)
    invoice_number = db.Column(db.String(50), nullable=False)
    date = db.Column(db.Date, nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    total_amount = db.Column(db.Numeric(10, 2), nullable=False)
    tax_amount = db.Column(db.Numeric(10, 2), default=0)
    status = db.Column(db.String(20), default='PENDING')  # PENDING, APPROVED, PAID, VOIDED
    journal_entry_id = db.Column(db.Integer, db.ForeignKey('journal_entry.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    journal_entry = db.relationship('JournalEntry')
    payments = db.relationship('VendorPayment', backref='invoice', lazy=True)
    
    def __repr__(self):
        return f"Invoice #{self.invoice_number} - {self.vendor.name}"


class VendorPayment(db.Model):
    """Vendor payments for accounts payable"""
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('vendor_invoice.id'), nullable=False)
    payment_date = db.Column(db.Date, nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    payment_method = db.Column(db.String(50), nullable=False)  # CASH, CHECK, WIRE, etc.
    reference = db.Column(db.String(100), nullable=True)
    journal_entry_id = db.Column(db.Integer, db.ForeignKey('journal_entry.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    journal_entry = db.relationship('JournalEntry')
    
    def __repr__(self):
        return f"Payment for Invoice #{self.invoice.invoice_number} - {self.amount}"


class Customer(db.Model):
    """Customers for accounts receivable"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    customer_number = db.Column(db.String(20), unique=True, nullable=False)
    contact_name = db.Column(db.String(100), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    address = db.Column(db.Text, nullable=True)
    payment_terms = db.Column(db.String(50), nullable=True)  # NET30, NET60, etc.
    account_id = db.Column(db.Integer, db.ForeignKey('chart_of_account.id'), nullable=False)  # AR account
    is_active = db.Column(db.Boolean, default=True)
    client_user_id = db.Column(db.Integer, db.ForeignKey('client_user.id'), nullable=True)  # Link to existing client
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    account = db.relationship('ChartOfAccount')
    client_user = db.relationship('ClientUser', backref='customer', uselist=False)
    invoices = db.relationship('CustomerInvoice', backref='customer', lazy=True)
    
    def __repr__(self):
        return f"{self.name} ({self.customer_number})"


class CustomerInvoice(db.Model):
    """Customer invoices for accounts receivable"""
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    invoice_number = db.Column(db.String(50), nullable=False)
    date = db.Column(db.Date, nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    total_amount = db.Column(db.Numeric(10, 2), nullable=False)
    tax_amount = db.Column(db.Numeric(10, 2), default=0)
    status = db.Column(db.String(20), default='PENDING')  # PENDING, SENT, PAID, VOIDED
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=True)  # Link to project
    journal_entry_id = db.Column(db.Integer, db.ForeignKey('journal_entry.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    journal_entry = db.relationship('JournalEntry')
    project = db.relationship('Project', backref='customer_invoices')
    payments = db.relationship('CustomerPayment', backref='invoice', lazy=True)
    
    def __repr__(self):
        return f"Invoice #{self.invoice_number} - {self.customer.name}"


class CustomerPayment(db.Model):
    """Customer payments for accounts receivable"""
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('customer_invoice.id'), nullable=False)
    payment_date = db.Column(db.Date, nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    payment_method = db.Column(db.String(50), nullable=False)  # CASH, CHECK, WIRE, etc.
    reference = db.Column(db.String(100), nullable=True)
    journal_entry_id = db.Column(db.Integer, db.ForeignKey('journal_entry.id'), nullable=True)
    project_payment_id = db.Column(db.Integer, db.ForeignKey('project_payment.id'), nullable=True)  # Link to project payment
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    journal_entry = db.relationship('JournalEntry')
    project_payment = db.relationship('ProjectPayment', backref='customer_payment', uselist=False)
    
    def __repr__(self):
        return f"Payment for Invoice #{self.invoice.invoice_number} - {self.amount}"


class BankAccount(db.Model):
    """Bank accounts for banking operations"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    account_number = db.Column(db.String(50), nullable=False)
    bank_name = db.Column(db.String(100), nullable=False)
    account_id = db.Column(db.Integer, db.ForeignKey('chart_of_account.id'), nullable=False)  # GL account
    is_active = db.Column(db.Boolean, default=True)
    currency_id = db.Column(db.Integer, db.ForeignKey('currency.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    account = db.relationship('ChartOfAccount')
    currency = db.relationship('Currency')
    reconciliations = db.relationship('BankReconciliation', backref='bank_account', lazy=True)
    
    def __repr__(self):
        return f"{self.name} ({self.account_number})"


class BankReconciliation(db.Model):
    """Bank reconciliations"""
    id = db.Column(db.Integer, primary_key=True)
    bank_account_id = db.Column(db.Integer, db.ForeignKey('bank_account.id'), nullable=False)
    statement_date = db.Column(db.Date, nullable=False)
    statement_ending_balance = db.Column(db.Numeric(10, 2), nullable=False)
    is_reconciled = db.Column(db.Boolean, default=False)
    reconciled_date = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    transactions = db.relationship('BankTransaction', backref='reconciliation', lazy=True)
    
    def __repr__(self):
        return f"Reconciliation {self.statement_date} - {self.bank_account.name}"


class BankTransaction(db.Model):
    """Bank transactions for reconciliation"""
    id = db.Column(db.Integer, primary_key=True)
    reconciliation_id = db.Column(db.Integer, db.ForeignKey('bank_reconciliation.id'), nullable=False)
    transaction_date = db.Column(db.Date, nullable=False)
    description = db.Column(db.String(200), nullable=True)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    is_cleared = db.Column(db.Boolean, default=False)
    journal_entry_id = db.Column(db.Integer, db.ForeignKey('journal_entry.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    journal_entry = db.relationship('JournalEntry')
    
    def __repr__(self):
        return f"Transaction {self.transaction_date} - {self.amount}"