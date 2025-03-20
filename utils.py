import csv
import io
from datetime import datetime
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
