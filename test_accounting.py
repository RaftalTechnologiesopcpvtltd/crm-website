from app import create_app, db
from models_accounting import ChartOfAccount, JournalEntry, JournalEntryLine, AccountingPeriod, FiscalYear
from models import User
from decimal import Decimal
from datetime import datetime, date, timedelta
import random

app = create_app()

def initialize_accounting_data():
    """Initialize basic accounting data for testing"""
    with app.app_context():
        # Check if we already have accounting data
        if ChartOfAccount.query.count() > 0:
            print("Accounting data already exists. Skipping initialization.")
            return
        
        # Create a fiscal year
        current_year = date.today().year
        fiscal_year = FiscalYear(
            name=f"Fiscal Year {current_year}",
            start_date=date(current_year, 1, 1),
            end_date=date(current_year, 12, 31),
            is_closed=False
        )
        db.session.add(fiscal_year)
        db.session.flush()  # Get the ID without committing
        
        # Create accounting periods (quarters)
        for quarter in range(1, 5):
            start_month = (quarter - 1) * 3 + 1
            end_month = quarter * 3
            
            # Calculate last day of end month
            if end_month in [4, 6, 9, 11]:
                last_day = 30
            elif end_month == 2:
                # Rough check for leap year
                last_day = 29 if current_year % 4 == 0 and (current_year % 100 != 0 or current_year % 400 == 0) else 28
            else:
                last_day = 31
                
            period = AccountingPeriod(
                fiscal_year_id=fiscal_year.id,
                name=f"Q{quarter} {current_year}",
                start_date=date(current_year, start_month, 1),
                end_date=date(current_year, end_month, last_day),
                is_closed=False
            )
            db.session.add(period)
        
        # Create basic chart of accounts
        accounts = [
            # Asset accounts
            {"code": "1000", "name": "Cash", "account_type": "ASSET", "normal_balance": "DEBIT"},
            {"code": "1100", "name": "Accounts Receivable", "account_type": "ASSET", "normal_balance": "DEBIT"},
            {"code": "1200", "name": "Equipment", "account_type": "ASSET", "normal_balance": "DEBIT"},
            # Liability accounts
            {"code": "2000", "name": "Accounts Payable", "account_type": "LIABILITY", "normal_balance": "CREDIT"},
            {"code": "2100", "name": "Salaries Payable", "account_type": "LIABILITY", "normal_balance": "CREDIT"},
            # Equity accounts
            {"code": "3000", "name": "Retained Earnings", "account_type": "EQUITY", "normal_balance": "CREDIT"},
            # Revenue accounts
            {"code": "4000", "name": "Sales Revenue", "account_type": "REVENUE", "normal_balance": "CREDIT"},
            {"code": "4100", "name": "Service Revenue", "account_type": "REVENUE", "normal_balance": "CREDIT"},
            # Expense accounts
            {"code": "5000", "name": "Salary Expense", "account_type": "EXPENSE", "normal_balance": "DEBIT"},
            {"code": "5100", "name": "Rent Expense", "account_type": "EXPENSE", "normal_balance": "DEBIT"},
            {"code": "5200", "name": "Utilities Expense", "account_type": "EXPENSE", "normal_balance": "DEBIT"},
        ]
        
        for account_data in accounts:
            account = ChartOfAccount(**account_data)
            db.session.add(account)
        
        db.session.commit()
        print(f"Created {len(accounts)} accounts, 1 fiscal year, and 4 accounting periods.")

def create_test_journal_entry():
    """Create a test journal entry"""
    with app.app_context():
        # Get the current admin user
        admin = User.query.filter_by(is_admin=True).first()
        if not admin:
            print("No admin user found. Cannot create test journal entry.")
            return
        
        # Get the current period
        current_month = date.today().month
        quarter = (current_month - 1) // 3 + 1
        period = AccountingPeriod.query.filter(
            AccountingPeriod.name.like(f"Q{quarter}%")
        ).first()
        
        if not period:
            print("No accounting period found for the current quarter.")
            return
        
        # Get accounts
        cash_account = ChartOfAccount.query.filter_by(name="Cash").first()
        ar_account = ChartOfAccount.query.filter_by(name="Accounts Receivable").first()
        revenue_account = ChartOfAccount.query.filter_by(name="Sales Revenue").first()
        
        if not all([cash_account, ar_account, revenue_account]):
            print("Required accounts not found. Please initialize accounting data first.")
            return
        
        # Create a journal entry
        entry = JournalEntry(
            entry_number=f"TEST-{random.randint(1000, 9999)}",
            date=date.today(),
            period_id=period.id,
            memo="Test journal entry for project revenue and payment",
            reference="TEST",
            status="POSTED",
            entry_type="MANUAL",
            created_by=admin.id
        )
        db.session.add(entry)
        db.session.flush()  # Get the ID without committing
        
        # Create journal entry lines
        amount = Decimal("1000.00")
        
        # Line 1: Debit AR for the project/sale
        line1 = JournalEntryLine(
            journal_entry_id=entry.id,
            account_id=ar_account.id,
            description="Test project receivable",
            debit_amount=amount,
            credit_amount=Decimal("0.00")
        )
        db.session.add(line1)
        
        # Line 2: Credit Revenue for the project/sale
        line2 = JournalEntryLine(
            journal_entry_id=entry.id,
            account_id=revenue_account.id,
            description="Test project revenue",
            debit_amount=Decimal("0.00"),
            credit_amount=amount
        )
        db.session.add(line2)
        
        # Create a second entry for payment
        payment_entry = JournalEntry(
            entry_number=f"TEST-PMT-{random.randint(1000, 9999)}",
            date=date.today() + timedelta(days=1),
            period_id=period.id,
            memo="Test journal entry for project payment",
            reference="TEST-PMT",
            status="POSTED",
            entry_type="MANUAL",
            created_by=admin.id
        )
        db.session.add(payment_entry)
        db.session.flush()  # Get the ID without committing
        
        # Line 1: Debit Cash for the payment
        payment_line1 = JournalEntryLine(
            journal_entry_id=payment_entry.id,
            account_id=cash_account.id,
            description="Test payment received",
            debit_amount=amount,
            credit_amount=Decimal("0.00")
        )
        db.session.add(payment_line1)
        
        # Line 2: Credit AR for the payment
        payment_line2 = JournalEntryLine(
            journal_entry_id=payment_entry.id,
            account_id=ar_account.id,
            description="Test payment applied to AR",
            debit_amount=Decimal("0.00"),
            credit_amount=amount
        )
        db.session.add(payment_line2)
        
        db.session.commit()
        print(f"Created 2 test journal entries with 4 lines totaling ${amount * 2}.")

if __name__ == "__main__":
    initialize_accounting_data()
    create_test_journal_entry()