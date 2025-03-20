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

def get_time_remaining(due_date):
    """
    Calculate time remaining until due date and return formatted string
    
    Args:
        due_date: The due date to compare against current time
    
    Returns:
        Dictionary with 'time_str', 'days', 'hours', 'minutes', and 'is_overdue' values
    """
    if not due_date:
        return {
            'time_str': 'No deadline',
            'days': 0,
            'hours': 0,
            'minutes': 0,
            'is_overdue': False,
            'css_class': 'text-muted'
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
    
    return {
        'time_str': time_str,
        'days': days,
        'hours': hours,
        'minutes': minutes,
        'is_overdue': is_overdue,
        'css_class': css_class
    }
