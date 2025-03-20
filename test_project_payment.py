from app import create_app, db
from models import Project, ProjectPayment, Sales, User, ClientUser
from decimal import Decimal
from datetime import datetime, date, timedelta
import random

app = create_app()

def create_test_project():
    """Create a test project with sales record"""
    with app.app_context():
        # Get the current admin user
        admin = User.query.filter_by(is_admin=True).first()
        if not admin:
            print("No admin user found. Cannot create test project.")
            return
            
        # Create a test client
        client = ClientUser.query.filter_by(name="Test Client").first()
        if not client:
            client = ClientUser(
                name="Test Client",
                email="testclient@example.com",
                platform="other",
                platform_username="testclient",
                is_existing_user=False
            )
            db.session.add(client)
            db.session.flush()
            print(f"Created test client: {client.name}")
        
        # Create a test project
        project_name = f"Test Project {date.today().strftime('%Y-%m-%d')}"
        project = Project(
            name=project_name,
            description="This is a test project created for accounting integration testing",
            client="Test Client Corp",
            client_user_id=client.id,
            platform="other",
            platform_project_id=f"TEST-{random.randint(1000, 9999)}",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            status="in-progress",
            budget=Decimal("2000.00"),
            payment_status="pending"
        )
        db.session.add(project)
        db.session.commit()
        print(f"Created test project: {project.name} with budget ${project.budget}")
        
        # Check if sales record was automatically created
        sale = Sales.query.filter_by(project_id=project.id).first()
        if sale:
            print(f"Sales record automatically created with total amount: ${sale.total_amount}")
        else:
            print("No sales record was created.")
        
        return project

def create_test_payment(project_id):
    """Create a test payment for a project"""
    with app.app_context():
        project = Project.query.get(project_id)
        if not project:
            print(f"No project found with ID {project_id}")
            return
            
        # Create a test payment
        payment = ProjectPayment(
            project_id=project.id,
            amount_original=Decimal("1500.00"),
            currency_original="USD",
            platform_fee=Decimal("150.00"),
            conversion_fee=Decimal("0.00"),
            conversion_rate=Decimal("1.0"),
            amount_received=Decimal("1350.00"),
            currency_received="USD",
            payment_date=date.today(),
            status="transferred",  # This triggers the journal entry creation
            notes="Test payment with automatic journal entry creation"
        )
        db.session.add(payment)
        db.session.commit()
        print(f"Created test payment for project {project.name}: ${payment.amount_original} (received: ${payment.amount_received})")
        
        # Check sales record update
        sale = Sales.query.filter_by(project_id=project.id).first()
        if sale:
            print(f"Sales record updated - received amount: ${sale.received_amount}, difference: ${sale.difference}")
        
        return payment

def close_test_sales(project_id):
    """Force close a project's sales record"""
    with app.app_context():
        sale = Sales.query.filter_by(project_id=project_id).first()
        if not sale:
            print(f"No sales record found for project ID {project_id}")
            return
            
        sale.status = "closed"
        sale.closed_date = date.today()
        sale.calculate_difference()
        db.session.commit()
        
        print(f"Closed sales record for project ID {project_id}")
        print(f"Final status: {sale.status}, closed date: {sale.closed_date}")
        print(f"Total amount: ${sale.total_amount}, received: ${sale.received_amount}, difference: ${sale.difference}")
        
        return sale

if __name__ == "__main__":
    # Create a test project
    project = create_test_project()
    
    if project:
        # Create a test payment
        payment = create_test_payment(project.id)
        
        # Close the sales record
        close_test_sales(project.id)