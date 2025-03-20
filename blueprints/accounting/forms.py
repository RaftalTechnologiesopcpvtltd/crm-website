from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, BooleanField, DecimalField, DateField, HiddenField, SubmitField
from wtforms.validators import DataRequired, Optional, Length, NumberRange, ValidationError
from models_accounting import AccountType, DebitCredit
from decimal import Decimal

class ChartOfAccountForm(FlaskForm):
    """Form for Chart of Accounts"""
    code = StringField('Account Code', validators=[DataRequired(), Length(max=20)])
    name = StringField('Account Name', validators=[DataRequired(), Length(max=100)])
    account_type = SelectField('Account Type', choices=[], validators=[DataRequired()])
    parent_id = SelectField('Parent Account', coerce=int, validators=[Optional()])
    description = TextAreaField('Description', validators=[Optional()])
    is_active = BooleanField('Active', default=True)
    normal_balance = SelectField('Normal Balance', choices=[], validators=[DataRequired()])
    submit = SubmitField('Save Account')
    
    def __init__(self, *args, **kwargs):
        super(ChartOfAccountForm, self).__init__(*args, **kwargs)
        self.account_type.choices = AccountType.choices()
        self.normal_balance.choices = DebitCredit.choices()

class FiscalYearForm(FlaskForm):
    """Form for Fiscal Year"""
    name = StringField('Fiscal Year Name', validators=[DataRequired(), Length(max=50)])
    start_date = DateField('Start Date', validators=[DataRequired()])
    end_date = DateField('End Date', validators=[DataRequired()])
    is_closed = BooleanField('Closed')
    submit = SubmitField('Save Fiscal Year')

class AccountingPeriodForm(FlaskForm):
    """Form for Accounting Period"""
    fiscal_year_id = SelectField('Fiscal Year', coerce=int, validators=[DataRequired()])
    name = StringField('Period Name', validators=[DataRequired(), Length(max=50)])
    start_date = DateField('Start Date', validators=[DataRequired()])
    end_date = DateField('End Date', validators=[DataRequired()])
    is_closed = BooleanField('Closed')
    submit = SubmitField('Save Period')

class JournalEntryForm(FlaskForm):
    """Form for Journal Entry"""
    entry_number = StringField('Entry Number', validators=[Optional(), Length(max=20)])
    date = DateField('Date', validators=[DataRequired()])
    period_id = SelectField('Accounting Period', coerce=int, validators=[DataRequired()])
    memo = TextAreaField('Memo', validators=[Optional()])
    reference = StringField('Reference', validators=[Optional(), Length(max=100)])
    status = SelectField('Status', 
                       choices=[('DRAFT', 'Draft'), 
                               ('POSTED', 'Posted'),
                               ('REVERSED', 'Reversed')],
                       default='DRAFT')
    entry_type = SelectField('Entry Type', 
                           choices=[('MANUAL', 'Manual'), 
                                   ('SYSTEM', 'System'),
                                   ('RECURRING', 'Recurring')],
                           default='MANUAL')
    submit = SubmitField('Save Journal Entry')

class JournalEntryLineForm(FlaskForm):
    """Form for Journal Entry Line items"""
    journal_entry_id = HiddenField('Journal Entry ID')
    account_id = SelectField('Account', coerce=int, validators=[DataRequired()])
    description = TextAreaField('Description', validators=[Optional()])
    debit_amount = DecimalField('Debit', places=2, validators=[Optional()], default=Decimal('0.00'))
    credit_amount = DecimalField('Credit', places=2, validators=[Optional()], default=Decimal('0.00'))
    submit = SubmitField('Add Line')
    
    def validate(self):
        if not super(JournalEntryLineForm, self).validate():
            return False
        
        if self.debit_amount.data == 0 and self.credit_amount.data == 0:
            self.debit_amount.errors.append('Either debit or credit amount must be greater than zero')
            return False
        
        if self.debit_amount.data > 0 and self.credit_amount.data > 0:
            self.credit_amount.errors.append('An entry cannot have both debit and credit amounts')
            return False
        
        return True

class CurrencyForm(FlaskForm):
    """Form for Currency"""
    code = StringField('Currency Code', validators=[DataRequired(), Length(max=3)])
    name = StringField('Currency Name', validators=[DataRequired(), Length(max=50)])
    symbol = StringField('Symbol', validators=[DataRequired(), Length(max=5)])
    is_base = BooleanField('Base Currency')
    is_active = BooleanField('Active', default=True)
    submit = SubmitField('Save Currency')

class ExchangeRateForm(FlaskForm):
    """Form for Exchange Rate"""
    from_currency_id = SelectField('From Currency', coerce=int, validators=[DataRequired()])
    to_currency_id = SelectField('To Currency', coerce=int, validators=[DataRequired()])
    rate = DecimalField('Exchange Rate', places=6, validators=[DataRequired()])
    date = DateField('Date', validators=[DataRequired()])
    submit = SubmitField('Save Exchange Rate')
    
    def validate_to_currency_id(self, field):
        if field.data == self.from_currency_id.data:
            raise ValidationError('To currency must be different from From currency')

class TaxForm(FlaskForm):
    """Form for Tax"""
    name = StringField('Tax Name', validators=[DataRequired(), Length(max=50)])
    rate = DecimalField('Rate (%)', places=2, validators=[DataRequired()])
    tax_type = SelectField('Tax Type', 
                         choices=[('VAT', 'VAT'), 
                                 ('GST', 'GST'),
                                 ('SALES', 'Sales Tax'),
                                 ('INCOME', 'Income Tax'),
                                 ('OTHER', 'Other')],
                         default='VAT')
    description = TextAreaField('Description', validators=[Optional()])
    is_active = BooleanField('Active', default=True)
    account_id = SelectField('Tax Account', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Save Tax')

class VendorForm(FlaskForm):
    """Form for Vendor"""
    name = StringField('Vendor Name', validators=[DataRequired(), Length(max=100)])
    vendor_number = StringField('Vendor Number', validators=[DataRequired(), Length(max=20)])
    contact_name = StringField('Contact Name', validators=[Optional(), Length(max=100)])
    email = StringField('Email', validators=[Optional(), Length(max=120)])
    phone = StringField('Phone', validators=[Optional(), Length(max=20)])
    address = TextAreaField('Address', validators=[Optional()])
    payment_terms = SelectField('Payment Terms', 
                              choices=[('NET30', 'Net 30 Days'), 
                                      ('NET60', 'Net 60 Days'),
                                      ('NET90', 'Net 90 Days'),
                                      ('CASH', 'Cash on Delivery'),
                                      ('OTHER', 'Other')],
                              default='NET30')
    account_id = SelectField('AP Account', coerce=int, validators=[DataRequired()])
    is_active = BooleanField('Active', default=True)
    submit = SubmitField('Save Vendor')

class VendorInvoiceForm(FlaskForm):
    """Form for Vendor Invoice"""
    vendor_id = SelectField('Vendor', coerce=int, validators=[DataRequired()])
    invoice_number = StringField('Invoice Number', validators=[DataRequired(), Length(max=50)])
    date = DateField('Invoice Date', validators=[DataRequired()])
    due_date = DateField('Due Date', validators=[DataRequired()])
    total_amount = DecimalField('Total Amount', places=2, validators=[DataRequired()])
    tax_amount = DecimalField('Tax Amount', places=2, default=Decimal('0.00'))
    status = SelectField('Status', 
                       choices=[('PENDING', 'Pending'), 
                               ('APPROVED', 'Approved'),
                               ('PAID', 'Paid'),
                               ('VOIDED', 'Voided')],
                       default='PENDING')
    submit = SubmitField('Save Invoice')

class VendorPaymentForm(FlaskForm):
    """Form for Vendor Payment"""
    invoice_id = SelectField('Invoice', coerce=int, validators=[DataRequired()])
    payment_date = DateField('Payment Date', validators=[DataRequired()])
    amount = DecimalField('Amount', places=2, validators=[DataRequired()])
    payment_method = SelectField('Payment Method', 
                               choices=[('CASH', 'Cash'), 
                                       ('CHECK', 'Check'),
                                       ('WIRE', 'Wire Transfer'),
                                       ('ACH', 'ACH'),
                                       ('CREDIT', 'Credit Card'),
                                       ('OTHER', 'Other')],
                               default='WIRE')
    reference = StringField('Reference', validators=[Optional(), Length(max=100)])
    submit = SubmitField('Save Payment')

class CustomerForm(FlaskForm):
    """Form for Customer"""
    name = StringField('Customer Name', validators=[DataRequired(), Length(max=100)])
    customer_number = StringField('Customer Number', validators=[DataRequired(), Length(max=20)])
    contact_name = StringField('Contact Name', validators=[Optional(), Length(max=100)])
    email = StringField('Email', validators=[Optional(), Length(max=120)])
    phone = StringField('Phone', validators=[Optional(), Length(max=20)])
    address = TextAreaField('Address', validators=[Optional()])
    payment_terms = SelectField('Payment Terms', 
                              choices=[('NET30', 'Net 30 Days'), 
                                      ('NET60', 'Net 60 Days'),
                                      ('NET90', 'Net 90 Days'),
                                      ('CASH', 'Cash on Delivery'),
                                      ('OTHER', 'Other')],
                              default='NET30')
    account_id = SelectField('AR Account', coerce=int, validators=[DataRequired()])
    is_active = BooleanField('Active', default=True)
    client_user_id = SelectField('Existing Client', coerce=int, validators=[Optional()])
    submit = SubmitField('Save Customer')

class CustomerInvoiceForm(FlaskForm):
    """Form for Customer Invoice"""
    customer_id = SelectField('Customer', coerce=int, validators=[DataRequired()])
    invoice_number = StringField('Invoice Number', validators=[DataRequired(), Length(max=50)])
    date = DateField('Invoice Date', validators=[DataRequired()])
    due_date = DateField('Due Date', validators=[DataRequired()])
    total_amount = DecimalField('Total Amount', places=2, validators=[DataRequired()])
    tax_amount = DecimalField('Tax Amount', places=2, default=Decimal('0.00'))
    status = SelectField('Status', 
                       choices=[('PENDING', 'Pending'), 
                               ('SENT', 'Sent'),
                               ('PAID', 'Paid'),
                               ('VOIDED', 'Voided')],
                       default='PENDING')
    project_id = SelectField('Project', coerce=int, validators=[Optional()])
    submit = SubmitField('Save Invoice')

class CustomerPaymentForm(FlaskForm):
    """Form for Customer Payment"""
    invoice_id = SelectField('Invoice', coerce=int, validators=[DataRequired()])
    payment_date = DateField('Payment Date', validators=[DataRequired()])
    amount = DecimalField('Amount', places=2, validators=[DataRequired()])
    payment_method = SelectField('Payment Method', 
                               choices=[('CASH', 'Cash'), 
                                       ('CHECK', 'Check'),
                                       ('WIRE', 'Wire Transfer'),
                                       ('ACH', 'ACH'),
                                       ('CREDIT', 'Credit Card'),
                                       ('OTHER', 'Other')],
                               default='WIRE')
    reference = StringField('Reference', validators=[Optional(), Length(max=100)])
    project_payment_id = SelectField('Project Payment', coerce=int, validators=[Optional()])
    submit = SubmitField('Save Payment')

class BankAccountForm(FlaskForm):
    """Form for Bank Account"""
    name = StringField('Account Name', validators=[DataRequired(), Length(max=100)])
    account_number = StringField('Account Number', validators=[DataRequired(), Length(max=50)])
    bank_name = StringField('Bank Name', validators=[DataRequired(), Length(max=100)])
    account_id = SelectField('GL Account', coerce=int, validators=[DataRequired()])
    is_active = BooleanField('Active', default=True)
    currency_id = SelectField('Currency', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Save Bank Account')

class BankReconciliationForm(FlaskForm):
    """Form for Bank Reconciliation"""
    bank_account_id = SelectField('Bank Account', coerce=int, validators=[DataRequired()])
    statement_date = DateField('Statement Date', validators=[DataRequired()])
    statement_ending_balance = DecimalField('Statement Ending Balance', places=2, validators=[DataRequired()])
    is_reconciled = BooleanField('Reconciled')
    reconciled_date = DateField('Reconciled Date', validators=[Optional()])
    submit = SubmitField('Save Reconciliation')

class BankTransactionForm(FlaskForm):
    """Form for Bank Transaction"""
    reconciliation_id = SelectField('Reconciliation', coerce=int, validators=[DataRequired()])
    transaction_date = DateField('Transaction Date', validators=[DataRequired()])
    description = StringField('Description', validators=[Optional(), Length(max=200)])
    amount = DecimalField('Amount', places=2, validators=[DataRequired()])
    is_cleared = BooleanField('Cleared')
    submit = SubmitField('Save Transaction')