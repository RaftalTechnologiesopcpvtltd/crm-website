import csv
import io
from datetime import datetime, timedelta
import base64
from flask import Response, render_template, url_for
import pdfkit
from xhtml2pdf import pisa

def generate_csv(data, filename, headers=None):
    """
    Generate a CSV file from data
    
    Args:
        data: List of dictionaries or objects
        filename: Name of the CSV file
        headers: List of header names (optional)
    
    Returns:
        Flask Response object with the CSV file
    """
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write headers
    if headers:
        writer.writerow(headers)
    elif data and isinstance(data[0], dict):
        writer.writerow(data[0].keys())
    
    # Write data
    for row in data:
        if isinstance(row, dict):
            writer.writerow(row.values())
        else:
            writer.writerow(row)
    
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": f"attachment; filename={filename}.csv"}
    )

def generate_pdf(template_name, filename, **context):
    """
    Generate a PDF file from a template
    
    Args:
        template_name: Name of the template file
        filename: Name of the PDF file
        context: Template context variables
    
    Returns:
        Flask Response object with the PDF file
    """
    html = render_template(template_name, **context)
    pdf_file = io.BytesIO()
    pisa.CreatePDF(html, dest=pdf_file)
    pdf_file.seek(0)
    
    return Response(
        pdf_file.getvalue(),
        mimetype="application/pdf",
        headers={"Content-disposition": f"attachment; filename={filename}.pdf"}
    )

def format_currency(amount):
    """Format a number as currency"""
    if amount is None:
        return "$0.00"
    return "${:,.2f}".format(float(amount))

def calculate_date_diff(start_date, end_date):
    """Calculate the difference between two dates in days"""
    if not start_date or not end_date:
        return 0
    delta = end_date - start_date
    return delta.days + 1

def get_status_badge_class(status):
    """Get the Bootstrap badge class for a status"""
    status = status.lower()
    if status in ['completed', 'approved', 'paid']:
        return 'bg-success'
    elif status in ['in-progress', 'pending']:
        return 'bg-warning text-dark'
    elif status in ['to-do', 'planning']:
        return 'bg-info text-dark'
    elif status in ['rejected', 'on-hold']:
        return 'bg-danger'
    else:
        return 'bg-secondary'

def get_time_remaining(due_date, start_date=None):
    """
    Calculate time remaining until due date and return formatted string
    
    Args:
        due_date: The due date to compare against current time
        start_date: Optional start date (order creation date). If provided, 
                   the percentage completion will be calculated from this date
    
    Returns:
        Dictionary with 'time_str', 'days', 'hours', 'minutes', 'is_overdue', 
        'css_class', and optionally 'percent_complete' values
    """
    if not due_date:
        return {
            'time_str': 'No deadline',
            'days': 0,
            'hours': 0,
            'minutes': 0,
            'is_overdue': False,
            'css_class': 'text-muted',
            'percent_complete': 0
        }
    
    now = datetime.now().replace(microsecond=0)
    
    # Convert date to datetime at end of day if it's just a date
    if isinstance(due_date, datetime):
        target_date = due_date
    else:
        target_date = datetime.combine(due_date, datetime.max.time())
    
    # Calculate time difference
    time_diff = target_date - now
    
    # Check if overdue
    is_overdue = time_diff.total_seconds() < 0
    
    # Get absolute values for display
    if is_overdue:
        time_diff = abs(time_diff)
        prefix = "Overdue by: "
        css_class = "text-danger"
    else:
        prefix = "Time left: "
        
        # Determine color based on urgency
        if time_diff.days > 5:
            css_class = "text-success"
        elif time_diff.days >= 2:
            css_class = "text-info"
        elif time_diff.days >= 1:
            css_class = "text-warning"
        else:
            css_class = "text-danger"
    
    # Calculate days, hours, minutes
    days = time_diff.days
    hours = time_diff.seconds // 3600
    minutes = (time_diff.seconds % 3600) // 60
    
    # Format the time string
    if days > 0:
        time_str = f"{prefix}{days}d {hours}h {minutes}m"
    elif hours > 0:
        time_str = f"{prefix}{hours}h {minutes}m"
    else:
        time_str = f"{prefix}{minutes}m"
    
    result = {
        'time_str': time_str,
        'days': days,
        'hours': hours,
        'minutes': minutes,
        'is_overdue': is_overdue,
        'css_class': css_class
    }
    
    # Calculate percentage completion if start_date is provided
    if start_date:
        # Convert to datetime objects for calculation
        if not isinstance(start_date, datetime):
            start_datetime = datetime.combine(start_date, datetime.min.time())
        else:
            start_datetime = start_date
        
        # Calculate total duration and elapsed time
        total_duration = (target_date - start_datetime).total_seconds()
        elapsed_time = (now - start_datetime).total_seconds()
        
        # Avoid division by zero and negative percentages
        if total_duration > 0:
            percent_complete = min(max(0, (elapsed_time / total_duration) * 100), 100)
            result['percent_complete'] = round(percent_complete, 1)
        else:
            result['percent_complete'] = 100 if is_overdue else 0
    
    return result

def generate_financial_report_csv(data, headers, title, filename):
    """
    Generate a CSV file for financial reports
    
    Args:
        data: The financial data to include in the report
        headers: List of header names
        title: Title of the report
        filename: Name of the CSV file
    
    Returns:
        Flask Response object with the CSV file
    """
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Add title and date
    writer.writerow([title])
    writer.writerow([f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"])
    writer.writerow([])  # Empty row for spacing
    
    # Add headers
    writer.writerow(headers)
    
    # Add data rows
    for row in data:
        writer.writerow(row)
    
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": f"attachment; filename={filename}"}
    )

def export_trial_balance(accounts, total_debits, total_credits, as_of_date, export_format='csv'):
    """
    Export trial balance report to CSV or PDF
    
    Args:
        accounts: List of accounts with balances
        total_debits: Total debits
        total_credits: Total credits
        as_of_date: As of date
        export_format: 'csv' or 'pdf'
    
    Returns:
        Response object with the exported file
    """
    if export_format == 'csv':
        headers = ['Account Code', 'Account Name', 'Debit', 'Credit']
        data = []
        
        for account in accounts:
            account_obj = account['account']
            data.append([
                account_obj.code,
                account_obj.name,
                float(account['debit_balance']),
                float(account['credit_balance'])
            ])
        
        # Add totals row
        data.append(['', 'TOTALS', float(total_debits), float(total_credits)])
        
        filename = f"trial_balance_{as_of_date.strftime('%Y%m%d')}.csv"
        return generate_financial_report_csv(data, headers, 
                                           f"Trial Balance as of {as_of_date.strftime('%Y-%m-%d')}", 
                                           filename)
    
    elif export_format == 'pdf':
        # Prepare context for PDF template
        context = {
            'title': 'Trial Balance',
            'as_of_date': as_of_date,
            'accounts': accounts,
            'total_debits': total_debits,
            'total_credits': total_credits,
            'export': True  # Flag to modify template for export
        }
        
        filename = f"trial_balance_{as_of_date.strftime('%Y%m%d')}"
        return generate_pdf('accounting/trial_balance.html', filename, **context)

def export_balance_sheet(asset_accounts, liability_accounts, equity_accounts, 
                        total_assets, total_liabilities, total_equity, 
                        as_of_date, export_format='csv'):
    """
    Export balance sheet to CSV or PDF
    
    Args:
        asset_accounts: List of asset accounts
        liability_accounts: List of liability accounts
        equity_accounts: List of equity accounts
        total_assets: Total assets
        total_liabilities: Total liabilities
        total_equity: Total equity
        as_of_date: As of date
        export_format: 'csv' or 'pdf'
    
    Returns:
        Response object with the exported file
    """
    if export_format == 'csv':
        headers = ['Account Type', 'Account Code', 'Account Name', 'Amount']
        data = []
        
        # Add assets
        data.append(['ASSETS', '', '', ''])
        for account in asset_accounts:
            data.append(['Asset', account.code, account.name, float(account.balance_amount)])
        data.append(['', '', 'Total Assets', float(total_assets)])
        
        # Add liabilities
        data.append(['', '', '', ''])  # Empty row for spacing
        data.append(['LIABILITIES', '', '', ''])
        for account in liability_accounts:
            data.append(['Liability', account.code, account.name, float(account.balance_amount)])
        data.append(['', '', 'Total Liabilities', float(total_liabilities)])
        
        # Add equity
        data.append(['', '', '', ''])  # Empty row for spacing
        data.append(['EQUITY', '', '', ''])
        for account in equity_accounts:
            data.append(['Equity', account.code, account.name, float(account.balance_amount)])
        data.append(['', '', 'Total Equity', float(total_equity)])
        
        # Add liabilities + equity total
        data.append(['', '', 'Total Liabilities & Equity', float(total_liabilities + total_equity)])
        
        filename = f"balance_sheet_{as_of_date.strftime('%Y%m%d')}.csv"
        return generate_financial_report_csv(data, headers, 
                                           f"Balance Sheet as of {as_of_date.strftime('%Y-%m-%d')}", 
                                           filename)
    
    elif export_format == 'pdf':
        # Prepare context for PDF template
        context = {
            'title': 'Balance Sheet',
            'as_of_date': as_of_date,
            'asset_accounts': asset_accounts,
            'liability_accounts': liability_accounts,
            'equity_accounts': equity_accounts,
            'total_assets': total_assets,
            'total_liabilities': total_liabilities,
            'total_equity': total_equity,
            'total_liabilities_equity': total_liabilities + total_equity,
            'export': True  # Flag to modify template for export
        }
        
        filename = f"balance_sheet_{as_of_date.strftime('%Y%m%d')}"
        return generate_pdf('accounting/balance_sheet.html', filename, **context)

def export_income_statement(revenue_accounts, expense_accounts, total_revenue, 
                          total_expenses, net_income, from_date, to_date, export_format='csv'):
    """
    Export income statement to CSV or PDF
    
    Args:
        revenue_accounts: List of revenue accounts
        expense_accounts: List of expense accounts
        total_revenue: Total revenue
        total_expenses: Total expenses
        net_income: Net income
        from_date: From date
        to_date: To date
        export_format: 'csv' or 'pdf'
    
    Returns:
        Response object with the exported file
    """
    if export_format == 'csv':
        headers = ['Account Type', 'Account Code', 'Account Name', 'Amount']
        data = []
        
        # Add revenues
        data.append(['REVENUE', '', '', ''])
        for account in revenue_accounts:
            data.append(['Revenue', account.code, account.name, float(account.balance_amount)])
        data.append(['', '', 'Total Revenue', float(total_revenue)])
        
        # Add expenses
        data.append(['', '', '', ''])  # Empty row for spacing
        data.append(['EXPENSES', '', '', ''])
        for account in expense_accounts:
            data.append(['Expense', account.code, account.name, float(account.balance_amount)])
        data.append(['', '', 'Total Expenses', float(total_expenses)])
        
        # Add net income
        data.append(['', '', '', ''])  # Empty row for spacing
        data.append(['', '', 'NET INCOME', float(net_income)])
        
        period_str = f"{from_date.strftime('%Y%m%d')}_to_{to_date.strftime('%Y%m%d')}"
        filename = f"income_statement_{period_str}.csv"
        return generate_financial_report_csv(data, headers, 
                                           f"Income Statement: {from_date.strftime('%Y-%m-%d')} to {to_date.strftime('%Y-%m-%d')}", 
                                           filename)
    
    elif export_format == 'pdf':
        # Prepare context for PDF template
        context = {
            'title': 'Income Statement',
            'from_date': from_date,
            'to_date': to_date,
            'revenue_accounts': revenue_accounts,
            'expense_accounts': expense_accounts,
            'total_revenue': total_revenue,
            'total_expenses': total_expenses,
            'net_income': net_income,
            'export': True  # Flag to modify template for export
        }
        
        period_str = f"{from_date.strftime('%Y%m%d')}_to_{to_date.strftime('%Y%m%d')}"
        filename = f"income_statement_{period_str}"
        return generate_pdf('accounting/income_statement.html', filename, **context)

def export_cash_flow_statement(operating_activities, investing_activities, financing_activities,
                             total_operating, total_investing, total_financing,
                             beginning_cash, ending_cash, net_change,
                             from_date, to_date, export_format='csv'):
    """
    Export cash flow statement to CSV or PDF
    
    Args:
        operating_activities: List of operating activities
        investing_activities: List of investing activities
        financing_activities: List of financing activities
        total_operating: Total operating cash flow
        total_investing: Total investing cash flow
        total_financing: Total financing cash flow
        beginning_cash: Beginning cash balance
        ending_cash: Ending cash balance
        net_change: Net change in cash
        from_date: From date
        to_date: To date
        export_format: 'csv' or 'pdf'
    
    Returns:
        Response object with the exported file
    """
    if export_format == 'csv':
        headers = ['Section', 'Date', 'Reference', 'Description', 'Inflow', 'Outflow', 'Net Amount']
        data = []
        
        # Add summary section
        data.append(['SUMMARY', '', '', '', '', '', ''])
        data.append(['Cash Balance', from_date.strftime('%Y-%m-%d'), '', 'Beginning Balance', '', '', float(beginning_cash)])
        data.append(['Operating Activities', '', '', 'Net Cash Flow', '', '', float(total_operating)])
        data.append(['Investing Activities', '', '', 'Net Cash Flow', '', '', float(total_investing)])
        data.append(['Financing Activities', '', '', 'Net Cash Flow', '', '', float(total_financing)])
        data.append(['Net Change', '', '', '', '', '', float(net_change)])
        data.append(['Cash Balance', to_date.strftime('%Y-%m-%d'), '', 'Ending Balance', '', '', float(ending_cash)])
        
        # Add operating activities
        data.append(['', '', '', '', '', '', ''])  # Empty row for spacing
        data.append(['OPERATING ACTIVITIES', '', '', '', '', '', ''])
        for activity in operating_activities:
            inflow = float(activity['amount']) if activity['type'] == 'inflow' else 0
            outflow = float(activity['amount']) if activity['type'] == 'outflow' else 0
            data.append([
                'Operating',
                activity['date'].strftime('%Y-%m-%d'),
                activity['reference'],
                activity['description'],
                inflow,
                outflow,
                ''
            ])
        
        # Add investing activities
        data.append(['', '', '', '', '', '', ''])  # Empty row for spacing
        data.append(['INVESTING ACTIVITIES', '', '', '', '', '', ''])
        for activity in investing_activities:
            inflow = float(activity['amount']) if activity['type'] == 'inflow' else 0
            outflow = float(activity['amount']) if activity['type'] == 'outflow' else 0
            data.append([
                'Investing',
                activity['date'].strftime('%Y-%m-%d'),
                activity['reference'],
                activity['description'],
                inflow,
                outflow,
                ''
            ])
        
        # Add financing activities
        data.append(['', '', '', '', '', '', ''])  # Empty row for spacing
        data.append(['FINANCING ACTIVITIES', '', '', '', '', '', ''])
        for activity in financing_activities:
            inflow = float(activity['amount']) if activity['type'] == 'inflow' else 0
            outflow = float(activity['amount']) if activity['type'] == 'outflow' else 0
            data.append([
                'Financing',
                activity['date'].strftime('%Y-%m-%d'),
                activity['reference'],
                activity['description'],
                inflow,
                outflow,
                ''
            ])
        
        period_str = f"{from_date.strftime('%Y%m%d')}_to_{to_date.strftime('%Y%m%d')}"
        filename = f"cash_flow_{period_str}.csv"
        return generate_financial_report_csv(data, headers, 
                                           f"Cash Flow Statement: {from_date.strftime('%Y-%m-%d')} to {to_date.strftime('%Y-%m-%d')}", 
                                           filename)
    
    elif export_format == 'pdf':
        # Prepare context for PDF template
        context = {
            'title': 'Cash Flow Statement',
            'from_date': from_date,
            'to_date': to_date,
            'operating_activities': operating_activities,
            'investing_activities': investing_activities,
            'financing_activities': financing_activities,
            'total_operating': total_operating,
            'total_investing': total_investing,
            'total_financing': total_financing,
            'beginning_cash': beginning_cash,
            'ending_cash': ending_cash,
            'net_change': net_change,
            'export': True  # Flag to modify template for export
        }
        
        period_str = f"{from_date.strftime('%Y%m%d')}_to_{to_date.strftime('%Y%m%d')}"
        filename = f"cash_flow_{period_str}"
        return generate_pdf('accounting/cash_flow.html', filename, **context)
